"""Local Ollama HTTP transport. Never logs image analysis or prompts."""
import ipaddress
import logging
logger = logging.getLogger(__name__)
from urllib.parse import urlparse
import httpx

class OllamaError(RuntimeError):
    pass

class OllamaClient:
    def __init__(self, settings, *, transport=None):
        self.settings = settings
        self.model = settings.ollama_model.strip()
        if ':cloud' in self.model.lower():
            raise ValueError('Cloud models are disabled. Select a downloaded local Ollama model.')
        parsed = urlparse(settings.ollama_url)
        host = parsed.hostname or ''
        try:
            local = ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = host.lower() == 'localhost'
        if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password or not host:
            raise ValueError('Invalid Ollama URL.')
        if not local:
            raise ValueError('Ollama must use a loopback address for local privacy.')
        self._client = httpx.Client(base_url=settings.ollama_url.rstrip('/')+'/', timeout=settings.ollama_timeout, transport=transport, trust_env=False, follow_redirects=False)

    def close(self):
        self._client.close()

    def _request(self, method, endpoint, **kwargs):
        try:
            response = self._client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            value = response.json()
            if not isinstance(value, dict):
                raise ValueError('not an object')
            if value.get('error'):
                raise OllamaError('Ollama could not process this request. Verify the installed model and available memory.')
            return value
        except httpx.TimeoutException as exc:
            logger.warning('Ollama request timed out')
            raise OllamaError('Ollama timed out. Increase OLLAMA_TIMEOUT or choose a smaller model.') from exc
        except httpx.HTTPStatusError as exc:
            logger.warning('Ollama HTTP error: %s', exc.response.status_code)
            if exc.response.status_code == 404:
                raise OllamaError('Ollama model or API was not found. Download the configured model with ollama pull.') from exc
            raise OllamaError(f'Ollama returned HTTP {exc.response.status_code}. Check the local Ollama server.') from exc
        except httpx.RequestError as exc:
            logger.warning('Ollama connection error: %s', type(exc).__name__)
            raise OllamaError('Cannot connect to Ollama. Start Ollama and check OLLAMA_URL.') from exc
        except ValueError as exc:
            raise OllamaError('Ollama returned an invalid JSON response.') from exc

    def status(self):
        result = dict(available=False, model_present=False, error='', model=self.model)
        try:
            data=self._request('GET','api/tags',timeout=min(5,self.settings.ollama_timeout))
            models=data.get('models')
            if not isinstance(models,list):
                raise OllamaError('Ollama returned an invalid model list.')
            names=[item.get('name',item.get('model','')) for item in models if isinstance(item,dict)]
            names={name for name in names if isinstance(name,str)}
            canonical=lambda name: name if ':' in name else name+':latest'
            result.update(available=True, model_present=canonical(self.model) in {canonical(name) for name in names})
            if not result['model_present']:
                result['error']='The configured model is not installed. Run ollama pull '+self.model
        except OllamaError as exc:
            result['error']=str(exc)
        return result

    def chat(self,messages,schema=None):
        payload=dict(model=self.model,messages=messages,stream=False,think=False,keep_alive=0,options=dict(num_gpu=self.settings.ollama_num_gpu,num_ctx=8192,num_predict=2048,temperature=0))
        if schema is not None:
            payload['format']=schema
        logger.info('Ollama generation start')
        data=self._request('POST','api/chat',json=payload)
        if data.get('done_reason') == 'length':
            logger.warning('Ollama output token limit reached')
            raise OllamaError('Ollama reached its output token limit. Choose a shorter detail level or a more compact analysis.')
        message=data.get('message')
        content=message.get('content') if isinstance(message,dict) else None
        if not isinstance(content,str) or not content.strip():
            raise OllamaError('Ollama returned no valid text. Check model compatibility.')
        logger.info('Ollama generation end')
        return content
