import sys
from io import StringIO

import pytest

from functions.manage.handler import main


def test_manage_handler_output():
    """Test that the manage handler prints 'Checked In'."""
    # Mock event and context
    event = {"type": 1, "token": "test_token", "application_id": "test_app_id"}  # PING
    context = None

    # Capture stdout
    captured_output = StringIO()
    sys.stdout = captured_output

    # Call the handler
    main(event, context)

    # Restore stdout
    sys.stdout = sys.__stdout__

    # Verify output
    assert "Checked In" in captured_output.getvalue()
