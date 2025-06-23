import os
import sys
from pathlib import Path

import pytest

# Add functions directory to Python path
functions_path = Path(__file__).parent.parent / "functions"
sys.path.insert(0, str(functions_path))

# Simulate Lambda deployment environment structure
# In Lambda, the handler.py file is at the root level, so we need to add
# the manage directory to the path so imports like "from commands import ..." work
manage_path = functions_path / "manage"
sys.path.insert(0, str(manage_path))


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables"""
    os.environ["CHECKIN_STATUS_PARAM"] = "/test/checkin_status"
    os.environ["APPLICATION_ID"] = "test_app_id"
    os.environ["ALERT_WEBHOOK_PARAM"] = "/test/alert_webhook"
    os.environ["CHALLONGE_API_KEY_PARAM"] = "/test/challonge_api_key"
    os.environ["GOOGLE_API_KEY_PARAM"] = "/test/google_api_key"
    os.environ["GOOGLE_SHEET_ID_PARAM"] = "/test/google_sheet_id"
    yield
    # Clean up environment variables after tests
    for key in [
        "CHECKIN_STATUS_PARAM",
        "APPLICATION_ID",
        "ALERT_WEBHOOK_PARAM",
        "CHALLONGE_API_KEY_PARAM",
        "GOOGLE_API_KEY_PARAM",
        "GOOGLE_SHEET_ID_PARAM",
    ]:
        os.environ.pop(key, None)
