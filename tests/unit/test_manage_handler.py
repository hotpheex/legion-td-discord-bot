import os
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3

os.environ["CHECKIN_STATUS_PARAM"] = "dummy_param"
os.environ["APPLICATION_ID"] = "dummy_app"
os.environ["ALERT_WEBHOOK_PARAM"] = "dummy_webhook"
os.environ["CHALLONGE_API_KEY_PARAM"] = "dummy_challonge"
os.environ["GOOGLE_API_KEY_PARAM"] = "dummy_google"
os.environ["GOOGLE_SHEET_ID_PARAM"] = "dummy_sheet"

from functions.manage import handler as manage_handler

# Helper to build a mock Discord event for a given subcommand

def build_event(subcommand, options=None):
    if options is None:
        options = []
    return {
        "detail": {
            "discord_event": {
                "token": "testtoken",
                "data": {
                    "name": subcommand,
                    "options": [
                        {"name": subcommand, "options": options}
                    ]
                }
            }
        }
    }

@pytest.fixture(autouse=True)
def setup_ssm():
    with mock_aws():
        ssm = boto3.client("ssm", region_name="us-east-1")
        ssm.put_parameter(Name="dummy_webhook", Value="mocked-webhook", Type="String")
        ssm.put_parameter(Name="dummy_challonge", Value="mocked-challonge", Type="String")
        ssm.put_parameter(Name="dummy_google", Value="mocked-google", Type="String")
        ssm.put_parameter(Name="dummy_sheet", Value="mocked-sheet", Type="String")
        yield

@pytest.fixture
def all_patches():
    with patch("functions.manage.handler.boto3.client") as mock_boto, \
         patch("functions.manage.handler.Challonge") as mock_challonge, \
         patch("functions.manage.handler.GoogleSheet") as mock_gsheet, \
         patch("functions.manage.handler.Discord") as mock_discord:
        yield mock_discord, mock_gsheet, mock_challonge, mock_boto

def test_checkin_status(all_patches):
    mock_discord, mock_gsheet, mock_challonge, mock_boto = all_patches
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {"Parameter": {"Value": "day_1"}}
    mock_boto.return_value = mock_client
    event = build_event("checkin_status")
    response = manage_handler.handler(event, None)
    assert "Checkins are currently set" in str(response)

def test_checkin_enabled(all_patches):
    mock_discord, mock_gsheet, mock_challonge, mock_boto = all_patches
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {"Parameter": {"Value": "day_1"}}
    mock_client.put_parameter.return_value = {}
    mock_boto.return_value = mock_client
    event = build_event("checkin_enabled", options=[{"name": "enabled", "value": "day_2"}])
    response = manage_handler.handler(event, None)
    assert "Checkins are now set" in str(response) or "already set" in str(response)

def test_calculate_seed(all_patches):
    mock_discord, mock_gsheet, mock_challonge, mock_boto = all_patches
    event = build_event("calculate_seed", options=[{"name": "player_1", "value": 1500}, {"name": "player_2", "value": 1200}])
    response = manage_handler.handler(event, None)
    assert "Team rating for" in str(response)

def test_clear_spreadsheets(all_patches):
    mock_discord, mock_gsheet, mock_challonge, mock_boto = all_patches
    mock_gsheet.return_value.clear_spreadsheets.return_value = None
    event = build_event("clear_spreadsheets", options=[{"name": "clear_signups", "value": True}, {"name": "confirm", "value": True}])
    response = manage_handler.handler(event, None)
    assert "Sheets Wiped" in str(response) or "Cancelled" in str(response)

def test_sort_signups(all_patches):
    mock_discord, mock_gsheet, mock_challonge, mock_boto = all_patches
    mock_gsheet.return_value.get_all_checkins.return_value = ([{"team": "A", "player_1": "p1", "player_2": "p2", "rating": 1500}], [])
    mock_gsheet.return_value.write_teams_to_div_sheets.return_value = True
    mock_challonge.return_value._get_tournament.return_value = True
    mock_challonge.return_value.add_participants_to_tournament.return_value = None
    event = build_event("sort_signups", options=[{"name": "confirm", "value": True}])
    response = manage_handler.handler(event, None)
    assert "Teams sorted in GSheets" in str(response) or "Cancelled" in str(response) 