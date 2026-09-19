"""Session-isolated Gradio UI; importing this module never loads a model."""
from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from core.prompt_engine import PromptOptions
from core.ollama_client import OllamaError
from core.vision_engine import AnalysisOptions

logger = logging.getLogger(__name__)
CSS = (Path(__file__).parent / "assets" / "style.css").read_text(encoding="utf-8")
INCLUDE = ("subject", "environment", "camera", "lighting", "composition", "colors", "materials", "style")


@dataclass(frozen=True)
class Session:
    record: Any = None
    result: Any = None
    structured: Any = None
    character: Any = None
    status: str = "Upload an image to begin."
    source_path: str | None = None


class UIHandlers:
    """Pure session transitions, independently testable without Gradio or GPU."""

    def __init__(self, service, settings):
        self.service, self.settings = service, settings

    @staticmethod
    def invalidate(*_):
        return Session(status="Image changed. Ready to analyze.")

    @staticmethod
    def reset_prompt(session):
        return replace(session, result=None, status="Prompt settings changed. Generate a new prompt.")

    def run(self, action, session, path, analysis_options, prompt_options=None):
        # Keep already completed vision output if a subsequent language call fails.
        current = session or Session()
        try:
            if not path:
                raise ValueError("Upload an image first.")
            same_analysis = (
                current.record is not None
                and current.source_path == str(path)
                and current.record.options == analysis_options
            )
            if same_analysis and action != "reanalyze":
                record = current.record
            else:
                if not same_analysis:
                    current = Session()
                record = self.service.analyze(path, analysis_options, force=action == "reanalyze")
                current = Session(record=record, source_path=str(path))
            if action == "generate":
                current = replace(current, result=None)
                current = replace(current, result=self.service.generate(record, prompt_options))
            elif action == "structured":
                current = replace(current, structured=self.service.structured(record))
            elif action == "character":
                current = replace(current, character=self.service.character(record))
            return replace(current, status={"analyze": "Analysis ready. Generate a prompt or extract structured data.", "reanalyze": "Fresh analysis ready.", "generate": "Prompt ready.", "structured": "Structured analysis ready.", "character": "Character DNA ready."}[action])
        except Exception as exc:
            logger.exception("UI action %s failed", action)
            if isinstance(exc, OllamaError) and current.record is not None:
                return replace(current, status="Ollama unavailable — raw JoyCaption analysis is still available.")
            message = str(exc) if isinstance(exc, (ValueError, RuntimeError)) else "Unexpected error. Check the console log for details."
            return replace(current, status=f"Could not complete: {message}")

    def export(self, session, format):
        from core.export import export_results
        try:
            if not session or session.record is None:
                raise ValueError("Analyze an image before saving.")
            paths = export_results(self.settings, session.record, session.result, session.structured, session.character, format)
            return paths, f"Saved {len(paths)} file(s)."
        except Exception as exc:
            logger.exception("Export failed")
            return [], f"Could not save: {exc}" if isinstance(exc, (ValueError, RuntimeError)) else "Could not save. Check the console log."


def character_prompt(character):
    """Readable reusable identity description from validated Character DNA."""
    return "\n".join(f"{key.replace('_', ' ').capitalize()}: {value}" for key, value in (character or {}).items() if value)


def render(session):
    result = session.result or {}
    return (session, result.get("prompt", ""), result.get("negative_prompt", ""),
            session.record.master if session.record else "", session.structured or {},
            session.character or {}, character_prompt(session.character), session.status, [])


def build_action_options(action, tokens, temperature, top_p, sampling, generator, detail, reconstruction, include, negative, mj_parameters):
    analysis = AnalysisOptions(max_new_tokens=int(tokens), temperature=float(temperature), top_p=float(top_p), do_sample=sampling)
    prompt = None
    if action == "generate":
        prompt = PromptOptions(generator=generator, detail=detail, reconstruction=reconstruction, include=tuple(include or ()), negative=negative,
                               mj_parameters=(mj_parameters or "") if generator == "Midjourney" else "")
    return analysis, prompt


def build_ui(service, settings):
    import gradio as gr

    handlers = UIHandlers(service, settings)
    with gr.Blocks(title="Image → Prompt", analytics_enabled=False, delete_cache=(600, 3600)) as demo:
        state = gr.State(Session())
        gr.HTML('<div class="masthead"><div><span class="eyebrow">LOCAL VISION WORKSPACE</span><h1>Image <span>→</span> Prompt</h1><p>See the details. Rebuild the image.</p></div><div class="local-badge">● LOCAL PIPELINE</div></div>')
        with gr.Row(equal_height=False):
            with gr.Column(scale=5, min_width=340):
                gr.Markdown("### 01 / Source image")
                upload = gr.Image(type="filepath", sources=["upload"], label="Reference image", height=340)
                with gr.Row():
                    analyze = gr.Button("ANALYZE IMAGE", variant="secondary")
                    reanalyze = gr.Button("RE-ANALYZE", variant="secondary")
                gr.Markdown("### 02 / Prompt direction")
                with gr.Row():
                    generator = gr.Dropdown(["Universal", "FLUX", "SDXL", "Stable Diffusion", "Leonardo", "Midjourney"], value="FLUX", label="Target generator")
                    detail = gr.Dropdown(["Short", "Medium", "Detailed", "Extreme"], value="Detailed", label="Detail level")
                reconstruction = gr.Radio(["Exact", "Close", "Balanced", "Creative"], value="Exact", label="Reconstruction")
                include = gr.CheckboxGroup([("Materials / textures" if x == "materials" else x.title(), x) for x in INCLUDE], value=list(INCLUDE), label="Include in prompt")
                negative_enabled = gr.Checkbox(False, label="Generate negative prompt")
                mj = gr.Textbox(label="Midjourney parameters", placeholder="--ar 3:2 --stylize 50", visible=False)
                with gr.Accordion("Advanced analysis", open=False):
                    gr.Markdown(f"JoyCaption startup mode: **{settings.joycaption_mode}** · Change configuration and restart to switch mode.")
                    max_tokens = gr.Slider(32, 4096, value=settings.max_new_tokens, step=32, label="Maximum new tokens")
                    temperature = gr.Slider(.05, 2, value=settings.temperature, step=.05, label="Temperature")
                    top_p = gr.Slider(.05, 1, value=settings.top_p, step=.05, label="Top P")
                    sample = gr.Checkbox(settings.do_sample, label="Sample analysis tokens")
                generate = gr.Button("GENERATE PROMPT", variant="primary", size="lg")
            with gr.Column(scale=7, min_width=420):
                gr.Markdown("### 03 / Results")
                status = gr.Textbox(value="Upload an image to begin.", label="Pipeline status", interactive=False)
                with gr.Tabs():
                    with gr.Tab("Final Prompt"):
                        final = gr.Textbox(label="Final prompt", lines=17, interactive=False, placeholder="Your reconstructed prompt appears here.")
                    with gr.Tab("Negative Prompt"):
                        negative = gr.Textbox(label="Negative prompt", lines=17, interactive=False)
                    with gr.Tab("Master Analysis"):
                        master = gr.Textbox(label="Raw JoyCaption analysis", lines=17, interactive=False)
                    with gr.Tab("Structured Analysis"):
                        structured = gr.JSON(label="Structured image description", value={})
                        structure_button = gr.Button("JSON STRUCTURE")
                    with gr.Tab("Character DNA"):
                        character_text = gr.Textbox(label="CHARACTER PROMPT", lines=8, interactive=False, placeholder="Reusable character identity appears here.")
                        character = gr.JSON(label="Character DNA", value={})
                        extract = gr.Button("EXTRACT CHARACTER")
                    with gr.Tab("System / Diagnostics"):
                        diagnostics = gr.JSON(label="Local runtime diagnostics", value={})
                        refresh = gr.Button("REFRESH DIAGNOSTICS")
                with gr.Row():
                    copy = gr.Button("COPY PROMPT")
                    save_txt = gr.Button("SAVE TXT")
                    save_json = gr.Button("SAVE JSON")
                files = gr.File(label="Exported files", file_count="multiple", interactive=False)
                gr.Markdown("Vision analysis is reused when you change the target generator. Exports are saved only when requested.", elem_classes=["footnote"])
        outputs = [state, final, negative, master, structured, character, character_text, status, files]
        inputs = [state, upload, max_tokens, temperature, top_p, sample, generator, detail, reconstruction, include, negative_enabled, mj]
        event_options = dict(concurrency_id="pipeline", concurrency_limit=1)

        def action_callback(action):
            def callback(session, path, tokens, temp, p, sampling, gen, level, fidelity, parts, neg, params, progress=gr.Progress()):
                progress(0, desc="Preparing image and loading local vision model if needed…")
                try:
                    analysis_options, prompt_options = build_action_options(action, tokens, temp, p, sampling, gen, level, fidelity, parts, neg, params)
                except (ValueError, TypeError) as exc:
                    logger.exception("Invalid UI options")
                    return render(replace(session or Session(), result=None, status=f"Invalid options: {exc}"))
                progress(.15, desc="Running local analysis / prompt pipeline…")
                result = handlers.run(action, session, path, analysis_options, prompt_options)
                progress(1, desc="Finished")
                return render(result)
            return callback

        for button, action in [(analyze, "analyze"), (reanalyze, "reanalyze"), (generate, "generate"), (structure_button, "structured"), (extract, "character")]:
            button.click(action_callback(action), inputs, outputs, **event_options)
        # Upload changes serialize behind in-flight work, then clear every old result.
        upload.change(lambda: render(handlers.invalidate()), outputs=outputs, **event_options)
        for component in [max_tokens, temperature, top_p, sample]:
            component.change(lambda: render(Session(status="Analysis settings changed. Analyze or generate again.")), outputs=outputs, **event_options)
        for component in [detail, reconstruction, include, negative_enabled, mj]:
            component.change(lambda s: render(handlers.reset_prompt(s)), state, outputs, **event_options)
        def change_generator(s, gen):
            return (*render(handlers.reset_prompt(s)), gen in ("SDXL", "Stable Diffusion"), gr.update(visible=gen == "Midjourney"))
        generator.change(change_generator, [state, generator], outputs + [negative_enabled, mj], **event_options)
        save_txt.click(lambda s: handlers.export(s, "txt"), state, [files, status], **event_options)
        save_json.click(lambda s: handlers.export(s, "json"), state, [files, status], **event_options)
        def get_diagnostics():
            try:
                return service.diagnostics()
            except Exception:
                logger.exception("Diagnostics failed")
                return {"error": "Diagnostics failed. Check the console log."}
        refresh.click(get_diagnostics, outputs=diagnostics, **event_options)
        copy.click(None, final, status, js="async (text) => { if (!text) return 'Generate a prompt first.'; try { await navigator.clipboard.writeText(text); return 'Prompt copied.'; } catch (_) { return 'Clipboard unavailable. Select the prompt and copy it manually.'; } }")
    return demo
