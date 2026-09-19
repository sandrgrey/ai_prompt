"""Quiet Windows launcher: reuse server, start Ollama, open browser when ready."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.error import URLError, HTTPError
from urllib.request import build_opener, ProxyHandler
import webbrowser

ROOT = Path(__file__).resolve().parent


def ensure_services(app_url, ollama_url, probe, spawn, wait):
    app_state = probe(app_url, 'app')
    if app_state == 'other':
        raise RuntimeError('Порт приложения занят другой программой. Проверьте GRADIO_PORT в .env.')
    ollama_state = probe(ollama_url, 'ollama')
    if ollama_state == 'other':
        raise RuntimeError('Адрес Ollama занят другой программой. Проверьте OLLAMA_URL в .env.')
    if ollama_state == 'missing':
        process = spawn('ollama')
        wait(ollama_url, 'ollama', process)
    if app_state == 'missing':
        process = spawn('app')
        wait(app_url, 'app', process)


def probe(url, kind):
    endpoint = '/config' if kind == 'app' else '/api/tags'
    try:
        with build_opener(ProxyHandler({})).open(url.rstrip('/') + endpoint, timeout=2) as response:
            data = json.load(response)
        if kind == 'app':
            return 'ready' if data.get('title') == 'Image → Prompt' else 'other'
        return 'ready' if isinstance(data.get('models'), list) else 'other'
    except HTTPError:
        return 'other'
    except (URLError, TimeoutError, OSError):
        return 'missing'
    except (ValueError, AttributeError):
        return 'other'


def wait_ready(url, kind, process):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        state = probe(url, kind)
        if state == 'ready':
            return
        if state == 'other':
            raise RuntimeError(f'Адрес {url} занят другой программой.')
        if process.poll() is not None:
            raise RuntimeError(f'Не удалось запустить {kind}. Подробности: logs/launcher-{kind}.log')
        time.sleep(.5)
    raise RuntimeError(f'{kind} не ответил за 120 секунд. Проверьте logs/launcher-{kind}.log и повторите запуск.')


@contextmanager
def launch_lock():
    # OS lock is released even when the launcher exits unexpectedly.
    import msvcrt
    folder = ROOT / '.runtime'
    folder.mkdir(exist_ok=True)
    with (folder / 'launcher.lock').open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        deadline = time.monotonic() + 250
        while True:
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise RuntimeError('Другой запуск ещё выполняется. Повторите попытку позже.')
                time.sleep(.5)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def main(open_browser=True):
    from config import Settings
    settings = Settings.from_env()
    host = '[::1]' if settings.gradio_host == '::1' else settings.gradio_host
    app_url = f'http://{host}:{settings.gradio_port}'
    (ROOT / 'logs').mkdir(exist_ok=True)

    def spawn(kind):
        env = os.environ.copy()
        if kind == 'app':
            args = [str(ROOT / '.venv' / 'Scripts' / 'python.exe'), str(ROOT / 'app.py')]
        else:
            executable = shutil.which('ollama')
            if not executable:
                candidate = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Ollama' / 'ollama.exe'
                executable = str(candidate) if candidate.is_file() else None
            if not executable:
                raise RuntimeError('Ollama не найдена. Установите её с ollama.com, затем повторите запуск.')
            args = [executable, 'serve']
            env['OLLAMA_HOST'] = settings.ollama_url
        with (ROOT / 'logs' / f'launcher-{kind}.log').open('a', encoding='utf-8') as log:
            return subprocess.Popen(args, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)

    with launch_lock():
        ensure_services(app_url, settings.ollama_url, probe, spawn, wait_ready)
    if open_browser and not webbrowser.open(app_url):
        raise RuntimeError(f'Приложение готово. Откройте в браузере: {app_url}')
    return app_url


if __name__ == '__main__':
    try:
        main(open_browser='--no-browser' not in sys.argv)
    except Exception as exc:
        if '--no-browser' in sys.argv:
            raise
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, str(exc), 'Image → Prompt — ошибка запуска', 0x10)
        sys.exit(1)
