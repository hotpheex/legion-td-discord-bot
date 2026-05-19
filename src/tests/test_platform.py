"""
Tests for the `libs.platform` parallel-run notifier (issue #118).

`post_to_platform` is a fire-and-forget, fail-open helper: it POSTs an event
to the new tournament platform's `/legacy/*` bridge endpoints. It must NEVER
raise -- every failure mode (timeout, connection error, HTTP non-2xx) is
swallowed so the calling Lambda handler is unaffected.

The HTTP boundary (`requests.post`) is mocked; no test makes a real network
call.
"""
import logging
from unittest.mock import MagicMock, patch

import pytest
import requests

from libs import platform


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _response(status_code=200):
    res = MagicMock()
    res.status_code = status_code

    def raise_for_status():
        if status_code >= 400:
            raise requests.exceptions.HTTPError(f"{status_code} error")

    res.raise_for_status.side_effect = raise_for_status
    return res


@pytest.fixture(autouse=True)
def _platform_config(monkeypatch):
    """Point the notifier at a fake, non-routable platform by default."""
    monkeypatch.setenv("PLATFORM_BASE_URL", "https://platform.invalid")
    monkeypatch.setenv("LEGACY_BRIDGE_SECRET", "test-bridge-secret")
    yield


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------
@patch("libs.platform.requests.post")
def test_post_to_platform_success(mock_post):
    mock_post.return_value = _response(200)

    result = platform.post_to_platform("/legacy/checkin", {"team_name": "Rocket"})

    assert result is True
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    # Endpoint is the configured base URL joined with the given path.
    assert args[0] == "https://platform.invalid/legacy/checkin"
    # Payload is sent as JSON.
    assert kwargs["json"] == {"team_name": "Rocket"}
    # Shared secret travels in the agreed header.
    assert kwargs["headers"]["x-legacy-bridge-secret"] == "test-bridge-secret"
    # A short timeout is set so a slow platform cannot stall the handler.
    assert "timeout" in kwargs
    assert kwargs["timeout"] > 0


@patch("libs.platform.requests.post")
def test_post_to_platform_trims_slashes(mock_post):
    """Base URL trailing slash + path leading slash never double up."""
    mock_post.return_value = _response(200)

    with patch.dict("os.environ", {"PLATFORM_BASE_URL": "https://platform.invalid/"}):
        platform.post_to_platform("legacy/sort", {"divisions": []})

    args, _ = mock_post.call_args
    assert args[0] == "https://platform.invalid/legacy/sort"


# ---------------------------------------------------------------------------
# Swallowed failure modes -- the helper must never raise
# ---------------------------------------------------------------------------
@patch("libs.platform.requests.post")
def test_post_to_platform_swallows_timeout(mock_post):
    mock_post.side_effect = requests.exceptions.Timeout("timed out")

    # Must not raise.
    result = platform.post_to_platform("/legacy/checkin", {"team_name": "Rocket"})

    assert result is False


@patch("libs.platform.requests.post")
def test_post_to_platform_swallows_connection_error(mock_post):
    mock_post.side_effect = requests.exceptions.ConnectionError("refused")

    result = platform.post_to_platform("/legacy/checkin", {"team_name": "Rocket"})

    assert result is False


@patch("libs.platform.requests.post")
def test_post_to_platform_swallows_http_500(mock_post):
    mock_post.return_value = _response(500)

    result = platform.post_to_platform("/legacy/results", {"winning_score": 2})

    assert result is False


@patch("libs.platform.requests.post")
def test_post_to_platform_swallows_http_401(mock_post):
    """A wrong/missing secret (401 on the platform) is also swallowed."""
    mock_post.return_value = _response(401)

    result = platform.post_to_platform("/legacy/sort", {"divisions": []})

    assert result is False


@patch("libs.platform.requests.post")
def test_post_to_platform_swallows_unexpected_error(mock_post):
    """Any non-requests exception is swallowed too -- truly fail-open."""
    mock_post.side_effect = ValueError("something weird")

    result = platform.post_to_platform("/legacy/checkin", {"team_name": "Rocket"})

    assert result is False


def test_post_to_platform_skips_when_unconfigured(monkeypatch):
    """With no base URL configured the helper no-ops without touching HTTP."""
    monkeypatch.delenv("PLATFORM_BASE_URL", raising=False)
    monkeypatch.delenv("LEGACY_BRIDGE_SECRET", raising=False)

    with patch("libs.platform.requests.post") as mock_post:
        result = platform.post_to_platform("/legacy/checkin", {"team_name": "Rocket"})

    assert result is False
    mock_post.assert_not_called()


@patch("libs.platform.requests.post")
def test_post_to_platform_logs_but_does_not_raise_on_failure(mock_post, caplog):
    mock_post.side_effect = requests.exceptions.Timeout("timed out")

    with caplog.at_level(logging.WARNING):
        platform.post_to_platform("/legacy/checkin", {"team_name": "Rocket"})

    # The failure is observable in logs (for the parallel-run audit) ...
    assert any("platform" in rec.message.lower() for rec in caplog.records)
