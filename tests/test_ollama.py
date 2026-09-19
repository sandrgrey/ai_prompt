import json
from types import SimpleNamespace
import httpx
import pytest
from core.ollama_client import OllamaClient, OllamaError


def settings(**kw):
    return SimpleNamespace(**(dict(ollama_url='http://localhost:11434', ollama_model='qwen3:8b', ollama_timeout=30, ollama_num_gpu=0) | kw))


def test_chat_payload():
    def handler(request):
        payload = json.loads(request.content)
        assert payload['stream'] is False and payload['think'] is False
        assert payload['options']['num_gpu'] == 0
        assert payload['format'] == {'type': 'object'}
        return httpx.Response(200, json={'message': {'content': 'ok'}})
    client = OllamaClient(settings(), transport=httpx.MockTransport(handler))
    assert client.chat([{'role':'user','content':'hi'}], {'type':'object'}) == 'ok'


@pytest.mark.parametrize('response', [httpx.Response(404), httpx.Response(200,json={}), httpx.Response(200,json={'message':{'content':3}})])
def test_bad_response(response):
    client=OllamaClient(settings(),transport=httpx.MockTransport(lambda _:response))
    with pytest.raises(OllamaError): client.chat([])


def test_cloud_forbidden():
    with pytest.raises(ValueError): OllamaClient(settings(ollama_model='qwen3:cloud'))


def test_status_missing():
    client=OllamaClient(settings(),transport=httpx.MockTransport(lambda _:httpx.Response(200,json={'models':[]})))
    assert client.status()['model_present'] is False

def test_timeout_and_connection_errors():
    for error in [httpx.ReadTimeout('timeout'), httpx.ConnectError('offline')]:
        def handler(request): raise error
        client=OllamaClient(settings(), transport=httpx.MockTransport(handler))
        with pytest.raises(OllamaError): client.chat([])
        assert client.status()['available'] is False


def test_remote_and_redirect_are_rejected():
    with pytest.raises(ValueError): OllamaClient(settings(ollama_url='https://example.com'))
    client=OllamaClient(settings(), transport=httpx.MockTransport(lambda _:httpx.Response(302,headers={'Location':'https://example.com'})))
    with pytest.raises(OllamaError): client.chat([])


def test_status_latest_name():
    client=OllamaClient(settings(ollama_model='qwen3'),transport=httpx.MockTransport(lambda _:httpx.Response(200,json={'models':[{'name':'qwen3:latest'}]})))
    assert client.status()['model_present'] is True

def test_status_malformed_model_name():
    client=OllamaClient(settings(),transport=httpx.MockTransport(lambda _:httpx.Response(200,json={'models':[{'name':[]}]})))
    assert client.status()['model_present'] is False

def test_truncated_response_rejected():
    client=OllamaClient(settings(),transport=httpx.MockTransport(lambda _:httpx.Response(200,json={'message':{'content':'partial'},'done_reason':'length'})))
    with pytest.raises(OllamaError,match='limit'): client.chat([])


def test_status_short_timeout():
    def handler(request):
        assert request.extensions['timeout']['read']==5
        return httpx.Response(200,json={'models':[]})
    OllamaClient(settings(ollama_timeout=600),transport=httpx.MockTransport(handler)).status()


def test_chat_releases_model_and_is_deterministic():
    def handler(request):
        payload=json.loads(request.content)
        assert payload['keep_alive']==0
        assert payload['options']['temperature']==0
        return httpx.Response(200,json={'message':{'content':'ok'}})
    OllamaClient(settings(),transport=httpx.MockTransport(handler)).chat([])
