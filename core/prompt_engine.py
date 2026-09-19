"""Schema-validated local prompt generation and bounded extraction cache."""
from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from threading import RLock
from pydantic import ValidationError
from .schemas import StructuredAnalysis, CharacterDNA, GeneratedPrompt

PROMPTS = Path(__file__).resolve().parent.parent / 'prompts'
GENERATORS = ('Universal','FLUX','SDXL','Stable Diffusion','Leonardo','Midjourney')
DETAILS = {'Short':'50–100', 'Medium':'100–200', 'Detailed':'200–400', 'Extreme':'400–800'}
CATEGORIES = ('subject','environment','camera','lighting','composition','colors','materials','style')
FIELD_GROUPS = {
    'subject': ('subjects','primary_subject','appearance','face','expression','clothing','accessories','pose','hair','body_orientation'),
    'environment': ('environment','foreground','background'),
    'camera': ('camera_angle','shot_type','lens_estimate','depth_of_field'),
    'lighting': ('lighting',),
    'composition': ('composition','object_positions'),
    'colors': ('colors',), 'materials': ('materials','textures'), 'style': ('style','atmosphere'),
}

class PromptError(RuntimeError):
    pass

@dataclass(frozen=True)
class PromptOptions:
    generator: str = 'FLUX'
    detail: str = 'Detailed'
    reconstruction: str = 'Exact'
    include: tuple[str,...] = CATEGORIES
    negative: bool = False
    mj_parameters: str = ''

    def __post_init__(self):
        if self.generator not in GENERATORS: raise ValueError('Unknown generator.')
        if self.detail not in DETAILS: raise ValueError('Unknown detail level.')
        if self.reconstruction not in ('Exact','Close','Balanced','Creative'): raise ValueError('Unknown reconstruction mode.')
        if isinstance(self.include,str) or any(x not in CATEGORIES for x in self.include): raise ValueError('Unknown include category.')
        object.__setattr__(self,'include',tuple(dict.fromkeys(self.include)))
        if not self.include: raise ValueError('Select at least one detail category.')
        if type(self.negative) is not bool: raise ValueError('Negative must be a boolean.')
        if not isinstance(self.mj_parameters,str) or len(self.mj_parameters)>1000 or '\n' in self.mj_parameters or '\r' in self.mj_parameters:
            raise ValueError('Midjourney parameters must be a single line under 1000 characters.')
        if self.mj_parameters.strip() and not re.fullmatch(r'(?:--[A-Za-z][A-Za-z0-9-]*(?: +[^\r\n]+)?)',self.mj_parameters.strip()):
            raise ValueError('Midjourney parameters must begin with --parameter.')

def template(name):
    return (PROMPTS / (name+'.txt')).read_text(encoding='utf-8')

class PromptEngine:
    def __init__(self, client, cache_size=32):
        self.client=client
        self.cache_size=max(1,cache_size)
        self._cache=OrderedDict()
        self._lock=RLock()

    def _validated(self, messages, model):
        schema=model.model_json_schema()
        raw=self.client.chat(messages,schema=schema)
        for attempt in range(2):
            try:
                result=model.model_validate_json(raw)
                if isinstance(result,GeneratedPrompt) and not result.prompt.strip():
                    raise ValueError('empty prompt')
                return result.model_dump()
            except (ValidationError,ValueError,TypeError):
                if attempt:
                    raise PromptError('The local language model returned invalid structured output after one repair attempt. Please retry or choose a stronger local model.') from None
                raw=self.client.chat(messages+[{'role':'assistant','content':raw if isinstance(raw,str) else ''},{'role':'user','content':template('repair')}],schema=schema)

    def structured(self,master):
        if not isinstance(master,str) or not master.strip(): raise PromptError('Analyze an image before generating a prompt.')
        key=hashlib.sha256(master.encode('utf-8')).hexdigest()
        with self._lock:
            if key not in self._cache:
                self._cache[key]=self._validated([{'role':'system','content':template('structured')},{'role':'user','content':json.dumps({'untrusted_visual_analysis':master},ensure_ascii=False)}],StructuredAnalysis)
                while len(self._cache)>self.cache_size: self._cache.popitem(last=False)
            self._cache.move_to_end(key)
            return json.loads(json.dumps(self._cache[key]))

    def character(self,master):
        data=self.structured(master)
        subject={key:data[key] for key in (*FIELD_GROUPS['subject'], 'colors', 'materials', 'textures') if key not in ('pose','body_orientation','expression')}
        return self._validated([{'role':'system','content':template('character')},{'role':'user','content':json.dumps({'untrusted_subject_facts':subject},ensure_ascii=False)}],CharacterDNA)

    def generate(self,master,options):
        data=self.structured(master)
        filtered={key:data[key] for category in options.include for key in FIELD_GROUPS[category]}
        rules=template('generate')+'\n'+template(options.generator.lower().replace(' ','_'))
        controls={'detail':options.detail,'target_word_range':DETAILS[options.detail],'reconstruction':options.reconstruction,'allowed_categories':options.include,'negative_enabled':options.negative}
        result=self._validated([{'role':'system','content':rules},{'role':'user','content':json.dumps({'controls':controls,'untrusted_visual_facts':filtered},ensure_ascii=False)}],GeneratedPrompt)
        # No inferred CLI parameters survive, including ones inside generated prose.
        result['prompt']=re.sub(r'\s*--[A-Za-z][\s\S]*$','',result['prompt']).strip()
        if not result['prompt']:
            raise PromptError('The local model returned an empty prompt after parameter cleanup. Please retry.')
        if options.negative and not result['negative_prompt'].strip():
            raise PromptError('The local model did not return the requested negative prompt. Please retry.')
        if options.generator=='Midjourney' and options.mj_parameters.strip():
            result['prompt']+=' '+options.mj_parameters.strip()
        if not options.negative: result['negative_prompt']=''
        return result
