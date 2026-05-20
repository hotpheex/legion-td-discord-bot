"""
Characterization tests for the `checkin` handler.

These pin the *current* behaviour of the unmodified `checkin` function:
the team and solo check-in paths, the already-checked-in short-circuit, and
the name-not-found short-circuit.

Google Sheets (gspread) is mocked at the boundary via the `GoogleSheet`
class the handler imports -- no test touches a real spreadsheet or network.
"""
from unittest.mock import MagicMock, patch

from checkin import main


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------
# A channel id that constants.py maps to the "Sign-up" sheet.
SIGNUP_CHANNEL_ID = "1023401872750547014"


def _cell(row=2, address="K2", value=""):
    """A stand-in for a gspread Cell."""
    cell = MagicMock()
    cell.row = row
    cell.address = address
    cell.value = value
    return cell


def solo_event(player_nick="Alice", channel_id=SIGNUP_CHANNEL_ID):
    return {
        "data": {"options": [{"name": "solo"}]},
        "member": {
            "nick": player_nick,
            "user": {"global_name": "AliceGlobal", "username": "alice_user"},
        },
        "channel_id": channel_id,
    }


def team_event(
    player_nick="Bob", team_name="Team Rocket", channel_id=SIGNUP_CHANNEL_ID
):
    return {
        "data": {
            "options": [
                {"name": "team", "options": [{"name": "team", "value": team_name}]}
            ]
        },
        "member": {
            "nick": player_nick,
            "user": {"global_name": "BobGlobal", "username": "bob_user"},
        },
        "channel_id": channel_id,
    }


def make_worksheet(name_cell=None, status_value="", player_in_row=True):
    """Build a mock gspread worksheet.

    `worksheet.find` is called with keyword args `in_column` (name lookup) or
    `in_row` (team-membership lookup); dispatch on which is present.
    """
    worksheet = MagicMock()
    status_cell = _cell(row=2, address="K2", value=status_value)

    def find(query=None, case_sensitive=None, in_column=None, in_row=None):
        if in_row is not None:
            return _cell() if player_in_row else None
        return name_cell

    worksheet.find.side_effect = find
    worksheet.cell.return_value = status_cell
    return worksheet


# ---------------------------------------------------------------------------
# Solo path
# ---------------------------------------------------------------------------
@patch("checkin.main.GoogleSheet")
def test_checkin_solo_success(mock_gsheet_cls):
    worksheet = make_worksheet(name_cell=_cell(row=5), status_value="")
    mock_gsheet_cls.return_value.worksheet = worksheet

    message = main.checkin(solo_event(player_nick="Alice"), "day_1")

    assert message == ":white_check_mark: `Alice` checked in!"
    # The status cell is written for the solo day_1 column (COLUMNS["solo"]["day_1"]).
    worksheet.update_cell.assert_called_once_with(5, 11, "Checked In")
    worksheet.format.assert_called_once()


@patch("checkin.main.GoogleSheet")
def test_checkin_solo_already_checked_in(mock_gsheet_cls):
    worksheet = make_worksheet(name_cell=_cell(row=5), status_value="Checked In")
    mock_gsheet_cls.return_value.worksheet = worksheet

    message = main.checkin(solo_event(player_nick="Alice"), "day_1")

    assert message == ":no_entry: `Alice` is already checked in"
    worksheet.update_cell.assert_not_called()


@patch("checkin.main.GoogleSheet")
def test_checkin_solo_name_not_found(mock_gsheet_cls):
    worksheet = make_worksheet(name_cell=None)
    mock_gsheet_cls.return_value.worksheet = worksheet

    message = main.checkin(solo_event(player_nick="Ghost"), "day_1")

    assert message.startswith(":no_entry: `Ghost` not found in the `Sign-up` sheet")
    worksheet.update_cell.assert_not_called()


@patch("checkin.main.GoogleSheet")
def test_checkin_solo_falls_back_to_global_name(mock_gsheet_cls):
    """When `nick` is empty the handler falls back to the user global_name."""
    worksheet = make_worksheet(name_cell=_cell(row=3), status_value="")
    mock_gsheet_cls.return_value.worksheet = worksheet

    event = solo_event(player_nick="")  # nick falsy -> use global_name
    message = main.checkin(event, "day_1")

    assert message == ":white_check_mark: `AliceGlobal` checked in!"


@patch("checkin.main.GoogleSheet")
def test_checkin_solo_blocked_on_day_2(mock_gsheet_cls):
    """Solo check-ins are rejected outright on day_2 (no sheet access)."""
    message = main.checkin(solo_event(), "day_2")

    assert message == ":no_entry: Solo players should check in as their team on Day 2"
    mock_gsheet_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Team path
# ---------------------------------------------------------------------------
@patch("checkin.main.GoogleSheet")
def test_checkin_team_success(mock_gsheet_cls):
    worksheet = make_worksheet(
        name_cell=_cell(row=7), status_value="", player_in_row=True
    )
    mock_gsheet_cls.return_value.worksheet = worksheet

    message = main.checkin(team_event(team_name="Team Rocket"), "day_1")

    assert message == ":white_check_mark: `Team Rocket` checked in!"
    # Team day_1 status column is COLUMNS["team"]["day_1"].
    worksheet.update_cell.assert_called_once_with(7, 6, "Checked In")


@patch("checkin.main.GoogleSheet")
def test_checkin_team_already_checked_in(mock_gsheet_cls):
    worksheet = make_worksheet(
        name_cell=_cell(row=7), status_value="Checked In", player_in_row=True
    )
    mock_gsheet_cls.return_value.worksheet = worksheet

    message = main.checkin(team_event(team_name="Team Rocket"), "day_1")

    assert message == ":no_entry: `Team Rocket` is already checked in"
    worksheet.update_cell.assert_not_called()


@patch("checkin.main.GoogleSheet")
def test_checkin_team_name_not_found(mock_gsheet_cls):
    worksheet = make_worksheet(name_cell=None)
    mock_gsheet_cls.return_value.worksheet = worksheet

    message = main.checkin(team_event(team_name="Nonexistent"), "day_1")

    assert message.startswith(
        ":no_entry: `Nonexistent` not found in the `Sign-up` sheet"
    )
    worksheet.update_cell.assert_not_called()


@patch("checkin.main.GoogleSheet")
def test_checkin_team_player_not_on_team(mock_gsheet_cls):
    """Team found, but the requesting player is not in its row."""
    worksheet = make_worksheet(
        name_cell=_cell(row=7), status_value="", player_in_row=False
    )
    mock_gsheet_cls.return_value.worksheet = worksheet

    message = main.checkin(
        team_event(player_nick="Bob", team_name="Team Rocket"), "day_1"
    )

    assert message == (
        ":no_entry: Player `Bob` is not on team `Team Rocket`\n"
        "Please make sure your Discord nickname matches your in game name"
    )
    worksheet.update_cell.assert_not_called()
