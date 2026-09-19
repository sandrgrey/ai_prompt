"""Official JoyCaption Beta One LLaVA inference, lazily loaded once."""
from __future__ import annotations

import gc
import logging
from pathlib import Path
from threading import RLock

from config import ROOT, Settings
from .model_manager import detect_hardware, select_mode
from .vision_engine import AnalysisOptions, VisionEngine

log = logging.getLogger(__name__)
# Transformers 5 nests these modules under LlavaForConditionalGeneration.model.
QUANTIZATION_EXCLUSIONS = ['model.vision_tower', 'model.multi_modal_projector', 'lm_head']


class JoyCaptionEngine(VisionEngine):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = None
        self.processor = None
        self.status = 'Not loaded — loads on first analysis'
        self.mode = settings.joycaption_mode
        self.device = 'not selected'
        self.dtype = None
        self._lock = RLock()
        self.analysis_count = 0

    def _load(self):
        if self.model is not None:
            return
        import torch
        from transformers import AutoProcessor, BitsAndBytesConfig, LlavaForConditionalGeneration

        hw = detect_hardware()
        self.mode = select_mode(self.settings.joycaption_mode, hw)
        self.device = 'cpu' if self.mode == 'CPU' else 'cuda:0'
        self.dtype = torch.float32 if self.mode == 'CPU' else (torch.bfloat16 if hw.bf16 else torch.float16)
        self.status = 'Loading model…'
        log.info('Model loading: %s device=%s GPU=%s mode=%s', self.settings.joycaption_model, self.device, hw.gpu, self.mode)
        path = self._model_path()
        kwargs = dict(dtype=self.dtype, device_map=self.device, local_files_only=True,
                      attn_implementation='sdpa')
        if self.mode == '4BIT':
            kwargs['quantization_config'] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=self.dtype,
                llm_int8_skip_modules=QUANTIZATION_EXCLUSIONS,
            )
        self.processor = AutoProcessor.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        self.model = LlavaForConditionalGeneration.from_pretrained(path, **kwargs)
        self.model.eval()
        self.status = f'Ready · {self.mode} · {self.device}'
        log.info('JoyCaption ready')

    def _model_path(self) -> str:
        """Resolve a local snapshot once; subsequent inference never contacts HF."""
        from huggingface_hub import snapshot_download

        if Path(self.settings.joycaption_model).is_dir():
            return self.settings.joycaption_model
        return snapshot_download(
            repo_id=self.settings.joycaption_model,
            cache_dir=str(self.settings.hf_home / 'hub'),
            local_files_only=self.settings.local_files_only,
            allow_patterns=['*.json', '*.safetensors', '*.model', '*.jinja', '*.txt'],
            max_workers=2,
        )

    def analyze(self, image, options: AnalysisOptions) -> str:
        import torch

        with self._lock:
            inputs = generated = None
            failure = None
            try:
                self._load()
                instruction = (ROOT / 'prompts' / 'analysis.txt').read_text(encoding='utf-8')
                convo = [{'role': 'system', 'content': 'You are a helpful image captioner.'},
                         {'role': 'user', 'content': instruction}]
                # This two-step combination follows the official model author example.
                text = self.processor.apply_chat_template(convo, tokenize=False, add_generation_prompt=True)
                inputs = self.processor(text=[text], images=[image], return_tensors='pt').to(self.device)
                inputs['pixel_values'] = inputs['pixel_values'].to(self.dtype)
                params = dict(max_new_tokens=options.max_new_tokens, do_sample=options.do_sample,
                              use_cache=True, suppress_tokens=None)
                if options.do_sample:
                    params.update(temperature=options.temperature, top_p=options.top_p, top_k=None)
                log.info('Analysis start mode=%s max_tokens=%d', self.mode, options.max_new_tokens)
                self.status = 'Analyzing…'
                with torch.inference_mode():
                    generated = self.model.generate(**inputs, **params)
                caption = self.processor.tokenizer.decode(
                    generated[0, inputs['input_ids'].shape[1]:], skip_special_tokens=True,
                    clean_up_tokenization_spaces=False,
                ).strip()
                if not caption:
                    raise RuntimeError('JoyCaption returned an empty description.')
                self.analysis_count += 1
                self.status = f'Ready · {self.mode} · {self.device}'
                log.info('Analysis complete')
                return caption
            except torch.cuda.OutOfMemoryError:
                log.exception('CUDA out of memory')
                failure = 'Недостаточно VRAM. Закройте GPU-приложения, выберите 4BIT и уменьшите max_new_tokens. Перезапустите приложение после изменения .env.'
            except Exception:
                log.exception('JoyCaption failed')
                failure = 'Не удалось выполнить JoyCaption. Проверьте модель, свободную память и System / Diagnostics; подробности в logs/app.log.'
            finally:
                # References are dropped before clearing allocator after a failed request.
                del inputs, generated
            if failure:
                self.status = 'Error — retry available; see logs/app.log'
                if self.model is None:
                    self.processor = None
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                raise RuntimeError(failure) from None

    def unload(self):
        """Explicit shutdown/recovery operation, never used between normal requests."""
        import torch
        with self._lock:
            self.model = self.processor = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            self.status = 'Unloaded'
