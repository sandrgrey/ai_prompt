from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from launcher import ensure_services


def test_existing_app_is_reused_and_ollama_checked():
    probe = Mock(side_effect=['ready', 'ready'])
    spawn, wait = Mock(), Mock()
    ensure_services('http://app', 'http://ollama', probe, spawn, wait)
    spawn.assert_not_called()
    wait.assert_not_called()


def test_starts_missing_services_and_waits_for_readiness():
    probe = Mock(side_effect=['missing', 'missing'])
    spawn, wait = Mock(), Mock()
    ensure_services('http://app', 'http://ollama', probe, spawn, wait)
    assert [x.args[0] for x in spawn.call_args_list] == ['ollama', 'app']
    assert [x.args[1] for x in wait.call_args_list] == ['ollama', 'app']


def test_occupied_app_port_does_not_start_anything():
    spawn = Mock()
    with pytest.raises(RuntimeError, match='GRADIO_PORT'):
        ensure_services('http://app', 'http://ollama', Mock(return_value='other'), spawn, Mock())
    spawn.assert_not_called()


def test_running_app_still_recovers_missing_ollama():
    spawn, wait = Mock(), Mock()
    ensure_services('http://app', 'http://ollama', Mock(side_effect=['ready', 'missing']), spawn, wait)
    assert [x.args[0] for x in spawn.call_args_list] == ['ollama']
