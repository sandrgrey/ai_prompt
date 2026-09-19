import json
import pytest
from core.prompt_engine import PromptEngine, PromptOptions, PromptError
from core.schemas import StructuredAnalysis

class FakeClient:
    def __init__(self, replies): self.replies=iter(replies); self.messages=[]
    def chat(self,messages,schema=None):
        self.messages.append(messages)
        return next(self.replies)

def structured():
    return {key: ([] if key == 'subjects' else '') for key in StructuredAnalysis.model_fields}

def test_repair_and_strict_rejection():
    client=FakeClient(['{}', json.dumps(structured())])
    assert PromptEngine(client).structured('cat') == structured()
    with pytest.raises(PromptError): PromptEngine(FakeClient(['{}','{}'])).structured('cat')

def test_filter_and_negative():
    data=structured(); data.update(primary_subject='cat', lighting='SECRET LIGHT')
    client=FakeClient([json.dumps(data),json.dumps({'prompt':'A cat','negative_prompt':'unwanted'})])
    result=PromptEngine(client).generate('MASTER SECRET LIGHT',PromptOptions(include=('subject',)))
    assert result == {'prompt':'A cat','negative_prompt':''}
    assert 'SECRET LIGHT' not in json.dumps(client.messages[-1])

def test_mj_parameters_and_no_inferred():
    data=json.dumps(structured())
    client=FakeClient([data,json.dumps({'prompt':'cat --ar 9:16 --v 6','negative_prompt':''})])
    result=PromptEngine(client).generate('cat',PromptOptions(generator='Midjourney',mj_parameters='--ar 1:1'))
    assert result['prompt']=='cat --ar 1:1'

def test_options_validation():
    for kwargs in [dict(generator='bad'),dict(detail='bad'),dict(reconstruction='bad'),dict(include=('bad',))]:
        with pytest.raises(ValueError): PromptOptions(**kwargs)


def test_cache_is_bounded_and_returns_copies():
    client=FakeClient([json.dumps(structured())]*3)
    engine=PromptEngine(client,cache_size=1)
    first=engine.structured('cat'); first['subjects'].append('changed')
    assert engine.structured('cat')['subjects']==[]
    engine.structured('dog'); engine.structured('cat')
    assert len(client.messages)==3


def test_wrong_field_type_rejected_after_repair():
    data=structured(); data['primary_subject']=123
    with pytest.raises(PromptError): PromptEngine(FakeClient([json.dumps(data)]*2)).structured('cat')


def test_character_uses_only_subject_facts():
    from core.schemas import CharacterDNA
    data=structured(); data['background']='PRIVATE SCENE'
    expected={key:'' for key in CharacterDNA.model_fields}
    client=FakeClient([json.dumps(data),json.dumps(expected)])
    assert PromptEngine(client).character('cat')==expected
    assert 'PRIVATE SCENE' not in json.dumps(client.messages[-1])


def test_enabled_negative_preserved():
    client=FakeClient([json.dumps(structured()),json.dumps({'prompt':'cat','negative_prompt':'duplicate subject'})])
    assert PromptEngine(client).generate('cat',PromptOptions(negative=True))['negative_prompt']=='duplicate subject'

@pytest.mark.parametrize('mode',['Exact','Close','Balanced','Creative'])
def test_required_reconstruction_modes(mode):
    assert PromptOptions(reconstruction=mode).reconstruction==mode


def test_character_excludes_transient_pose():
    from core.schemas import CharacterDNA
    data=structured(); data.update(pose='TRANSIENT POSE',body_orientation='TRANSIENT ORIENTATION',expression='TRANSIENT EXPRESSION')
    client=FakeClient([json.dumps(data),json.dumps({key:'' for key in CharacterDNA.model_fields})])
    PromptEngine(client).character('cat')
    assert 'TRANSIENT' not in json.dumps(client.messages[-1])

def test_character_retains_identity_colors_materials():
    from core.schemas import CharacterDNA
    data=structured(); data.update(colors='Subject has green eyes and red hair; background blue',materials='Subject wears leather armor',textures='Subject has striped fur',pose='TRANSIENT POSE')
    expected={key:'' for key in CharacterDNA.model_fields}
    client=FakeClient([json.dumps(data),json.dumps(expected)])
    PromptEngine(client).character('character')
    facts=json.loads(client.messages[-1][-1]['content'])['untrusted_subject_facts']
    assert facts['colors']==data['colors']
    assert facts['materials']==data['materials']
    assert facts['textures']==data['textures']
    assert 'pose' not in facts

def test_empty_include_rejected():
    with pytest.raises(ValueError,match='Select at least one detail category'):
        PromptOptions(include=())

def test_parameter_only_positive_prompt_rejected():
    client=FakeClient([json.dumps(structured()),json.dumps({'prompt':'--ar 2:3','negative_prompt':''})])
    with pytest.raises(PromptError,match='empty prompt'):
        PromptEngine(client).generate('cat',PromptOptions())


@pytest.mark.parametrize('negative',['','   '])
def test_requested_empty_negative_rejected(negative):
    client=FakeClient([json.dumps(structured()),json.dumps({'prompt':'cat','negative_prompt':negative})])
    with pytest.raises(PromptError,match='negative prompt'):
        PromptEngine(client).generate('cat',PromptOptions(negative=True))
