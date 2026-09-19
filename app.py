"""Local entry point. No model weights are loaded until the first request."""
import logging
from logging.handlers import RotatingFileHandler

from config import ROOT, Settings


def main():
    settings = Settings.from_env()
    settings.configure_environment()
    (ROOT / 'logs').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s',
                        handlers=[logging.StreamHandler(), RotatingFileHandler(
                            ROOT / 'logs' / 'app.log', maxBytes=2_000_000, backupCount=3, encoding='utf-8')])
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    import gradio as gr
    from core.service import ApplicationService
    from ui import CSS, build_ui

    service = ApplicationService(settings)
    demo = build_ui(service, settings)
    demo.queue(max_size=16, default_concurrency_limit=1).launch(
        server_name=settings.gradio_host, server_port=settings.gradio_port,
        share=False, inbrowser=False, show_error=False,
        css=CSS, js="() => document.documentElement.classList.add('dark')",
        theme=gr.themes.Base(primary_hue='violet', neutral_hue='slate',
                             font=['Segoe UI', 'Arial', 'sans-serif'],
                             font_mono=['Consolas', 'monospace']),
        allowed_paths=[str(settings.output_directory)],
        blocked_paths=[str(ROOT / '.env'), str(ROOT / 'logs'), str(settings.hf_home)],
        max_file_size='50mb',
    )


if __name__ == '__main__':
    main()
