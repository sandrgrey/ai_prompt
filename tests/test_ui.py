from dataclasses import dataclass
from types import SimpleNamespace

from core.prompt_engine import PromptOptions
from core.vision_engine import AnalysisOptions
from ui import Session, UIHandlers, render


@dataclass(frozen=True)
class Record:
    key: str
    master: str
    options: AnalysisOptions = AnalysisOptions()


class FakeService:
    def __init__(self):
        self.cache = {}
        self.vision_calls = 0
        self.fail_generate = False

    def analyze(self, path, options, force=False):
        key = (path, options)
        if force or key not in self.cache:
            self.vision_calls += 1
            self.cache[key] = Record(str(key), "A red coat beside a window", options)
        return self.cache[key]

    def generate(self, record, options):
        if self.fail_generate:
            raise RuntimeError("Ollama unavailable")
        return {"prompt": options.generator + ": " + record.master, "negative_prompt": "blur" if options.negative else "", "generator": options.generator}

    def structured(self, record):
        return {"subject": record.master}

    def character(self, record):
        return {"clothing": "red coat"}


def test_generator_changes_reuse_master_and_return_new_session():
    service = FakeService()
    handlers = UIHandlers(service, SimpleNamespace())
    start = Session()
    flux = handlers.run("generate", start, "image.png", AnalysisOptions(), PromptOptions())
    sdxl = handlers.run("generate", flux, "image.png", AnalysisOptions(), PromptOptions(generator="SDXL", negative=True))
    assert service.vision_calls == 1
    assert start.record is None
    assert flux.result["generator"] == "FLUX"
    assert sdxl.result["generator"] == "SDXL"
    assert sdxl.result["negative_prompt"] == "blur"


def test_failed_language_stage_keeps_master_and_clears_old_prompt():
    service = FakeService()
    handlers = UIHandlers(service, None)
    state = handlers.run("generate", Session(), "image.png", AnalysisOptions(), PromptOptions())
    service.fail_generate = True
    state = handlers.run("generate", state, "image.png", AnalysisOptions(), PromptOptions())
    assert state.record.master == "A red coat beside a window"
    assert state.result is None
    assert "Ollama unavailable" in state.status
    assert "Traceback" not in state.status


def test_upload_and_clear_reset_all_outputs():
    populated = Session(Record("key", "master"), {"prompt": "old"}, {"scene": 1}, {"person": 1})
    reset = UIHandlers.invalidate(populated)
    assert reset.record is reset.result is reset.structured is reset.character is None
    assert render(reset)[1:6] == ("", "", "", {}, {})
    assert render(reset)[-1] == []


def test_sessions_do_not_share_results_and_force_reanalyzes():
    service = FakeService()
    handlers = UIHandlers(service, None)
    first = handlers.run("character", Session(), "first.png", AnalysisOptions())
    other = handlers.run("structured", Session(), "second.png", AnalysisOptions())
    assert first.structured is None and other.character is None
    fresh = handlers.run("reanalyze", first, "first.png", AnalysisOptions())
    assert service.vision_calls == 3
    assert fresh.character is None


def test_missing_image_has_actionable_error():
    state = UIHandlers(FakeService(), None).run("analyze", Session(), None, AnalysisOptions())
    assert "Upload an image" in state.status
    assert state.record is None


def test_prompt_settings_reset_preserves_analysis_and_extractions():
    state = Session(Record("key", "master"), {"prompt": "old"}, {"scene": 1}, {"person": 1})
    reset = UIHandlers.reset_prompt(state)
    assert reset.result is None
    assert reset.record == state.record
    assert reset.structured == state.structured
    assert reset.character == state.character


def test_character_prompt_is_separate_readable_output():
    from ui import character_prompt
    character = {"species": "human", "hair_fur": "short dark hair", "unique_features": "freckles", "accessories": ""}
    assert character_prompt(character) == "Species: human\nHair fur: short dark hair\nUnique features: freckles"
    state = Session(character=character)
    assert render(state)[5] == character
    assert render(state)[6] == character_prompt(character)
    assert character_prompt(None) == ""


def test_first_generate_ollama_failure_displays_completed_master():
    from core.ollama_client import OllamaError

    class OfflineService(FakeService):
        def generate(self, record, options):
            raise OllamaError("Connection refused")

    state = UIHandlers(OfflineService(), None).run("generate", Session(), "image.png", AnalysisOptions(), PromptOptions())
    assert state.result is None
    assert render(state)[3] == "A red coat beside a window"
    assert state.status == "Ollama unavailable — raw JoyCaption analysis is still available."


def test_session_master_survives_shared_cache_eviction_and_deleted_upload(tmp_path):
    class FileService(FakeService):
        def analyze(self, path, options, force=False):
            from pathlib import Path
            if not Path(path).exists():
                raise ValueError("Upload file expired")
            return super().analyze(path, options, force)

    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    a.write_bytes(b"fake a")
    b.write_bytes(b"fake b")
    service = FileService()
    handlers = UIHandlers(service, None)
    state = handlers.run("analyze", Session(), str(a), AnalysisOptions())
    handlers.run("analyze", Session(), str(b), AnalysisOptions())
    service.cache.clear()
    a.unlink()
    for action in ("analyze", "generate", "structured", "character"):
        state = handlers.run(action, state, str(a), AnalysisOptions(), PromptOptions())
        assert "Could not" not in state.status
    assert state.result["prompt"]
    assert state.structured and state.character
    assert service.vision_calls == 2
    forced = handlers.run("reanalyze", state, str(a), AnalysisOptions())
    assert "Upload file expired" in forced.status


def test_path_and_analysis_option_changes_do_not_reuse_wrong_record():
    service = FakeService()
    handlers = UIHandlers(service, None)
    state = handlers.run("generate", Session(), "a.png", AnalysisOptions(), PromptOptions())
    next_image = handlers.run("analyze", state, "b.png", AnalysisOptions())
    assert next_image.result is None
    assert next_image.record != state.record
    next_options = handlers.run("analyze", next_image, "b.png", AnalysisOptions(max_new_tokens=1024))
    assert next_options.record.options.max_new_tokens == 1024
    assert service.vision_calls == 3


def test_non_prompt_actions_ignore_empty_categories_and_invalid_mj_parameters():
    from ui import build_action_options
    handlers = UIHandlers(FakeService(), None)
    for action in ("analyze", "reanalyze", "structured", "character"):
        analysis, prompt = build_action_options(action, 768, .6, .9, False, "Midjourney", "Detailed", "Exact", [], False, "invalid\nparameters")
        assert prompt is None
        result = handlers.run(action, Session(), "image.png", analysis, prompt)
        assert "Could not" not in result.status
        assert result.record is not None


def test_hidden_midjourney_parameters_do_not_block_other_generators():
    import pytest
    from ui import build_action_options
    args = ("Detailed", "Exact", ["subject"], False, "invalid\nparameters")
    _, prompt = build_action_options("generate", 768, .6, .9, False, "FLUX", *args)
    assert prompt.mj_parameters == ""
    with pytest.raises(ValueError, match="single line"):
        build_action_options("generate", 768, .6, .9, False, "Midjourney", *args)
    with pytest.raises(ValueError, match="at least one"):
        build_action_options("generate", 768, .6, .9, False, "FLUX", "Detailed", "Exact", [], False, "")
