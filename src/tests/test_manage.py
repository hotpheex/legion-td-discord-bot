"""
Characterization tests for the `manage` handler.

These tests pin the *current* behaviour of the unmodified handler so that a
later, additive change can be proven behaviour-preserving. They are not a
specification of desired behaviour -- if the handler changes, the expected
values here are what must be re-derived from the real code.

Every external service (boto3 / SSM, Google Sheets, Challonge) is mocked at
the boundary; no test makes a real network or API call.
"""
import random
from unittest.mock import MagicMock

import pytest
from requests.exceptions import HTTPError

from manage import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def generate_checkins(num_teams, num_solos):
    """Build deterministic-shaped team/solo check-in dicts.

    `generate_divisions` only branches on *counts* and relative rating order,
    so the random ratings here do not affect the division *sizes* that the
    characterization assertions below pin. A fixed seed keeps the generated
    ratings reproducible so any future failure can be replayed.
    """
    random.seed(0)
    teams = []
    for i in range(num_teams):
        teams.append(
            {
                "team": f"Team {i + 1}",
                "player_1": f"Player {2 * i + 1}",
                "player_2": f"Player {2 * i + 2}",
                "rating": random.randint(1400, 2400),
            }
        )

    solos = []
    for i in range(num_solos):
        solos.append(
            {
                "player": f"Player {2 * num_teams + i + 1}",
                "rating": random.randint(800, 2800),
            }
        )

    return teams, solos


def run_generate_divisions(
    i_teams,
    i_solos,
    o_div_sizes,
    o_playing_teams,
    o_playing_solos,
    o_excluded_teams,
    o_excluded_solos,
):
    teams, solos = generate_checkins(i_teams, i_solos)
    (
        divisions,
        playing_teams,
        playing_solos,
        excluded_teams,
        excluded_solos,
    ) = main.generate_divisions(teams, solos)

    assert [len(d) for d in divisions] == o_div_sizes
    assert len(playing_teams) == o_playing_teams
    assert len(playing_solos) == o_playing_solos
    assert len(excluded_teams) == o_excluded_teams
    assert len(excluded_solos) == o_excluded_solos


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
def test_calculate_team_seed():
    rating, message = main.calculate_team_seed([2330, 1895])
    assert rating == 2185
    assert message == "Team rating for `[2330, 1895]`: `2185`"


def test_get_checkin_status():
    client = MagicMock()
    client.get_parameter.return_value = {"Parameter": {"Value": "disabled"}}
    status = main.get_checkin_status(client, "checkin-status-param")
    assert status == "disabled"
    client.get_parameter.assert_called_once_with(Name="checkin-status-param")


def test_set_checkin_status_enabled():
    client = MagicMock()
    client.get_parameter.return_value = {"Parameter": {"Value": "disabled"}}
    client.put_parameter.return_value = {}
    event = {
        "data": {
            "options": [
                {
                    "name": "checkin_enabled",
                    "options": [{"name": "checkin_enabled", "value": "day_1"}],
                }
            ]
        }
    }
    message = main.set_checkin_status(client, event, "checkin-status-param")
    assert message == "Checkins are now set to `day_1`"
    client.put_parameter.assert_called_once_with(
        Name="checkin-status-param", Value="day_1", Overwrite=True
    )


def test_set_checkin_status_already_set():
    client = MagicMock()
    client.get_parameter.return_value = {"Parameter": {"Value": "day_1"}}
    event = {
        "data": {
            "options": [
                {
                    "name": "checkin_enabled",
                    "options": [{"name": "checkin_enabled", "value": "day_1"}],
                }
            ]
        }
    }
    message = main.set_checkin_status(client, event, "checkin-status-param")
    assert message == "Checkins already set to `day_1`"
    client.put_parameter.assert_not_called()


# ---------------------------------------------------------------------------
# generate_divisions -- division generation
#
# Expected division sizes / counts are derived from running the *current*
# unmodified `generate_divisions` against the inputs below. With MAX_TEAMS=176
# none of these inputs hit the team cap, so no teams are ever excluded.
# ---------------------------------------------------------------------------
def test_divs_leftover_teams():
    run_generate_divisions(
        i_teams=106,
        i_solos=11,
        o_div_sizes=[8, 8, 31, 64, 0],
        o_playing_teams=111,
        o_playing_solos=10,
        o_excluded_teams=0,
        o_excluded_solos=1,
    )


def test_divs_leftover_solos():
    run_generate_divisions(
        i_teams=90,
        i_solos=35,
        o_div_sizes=[8, 8, 27, 64, 0],
        o_playing_teams=107,
        o_playing_solos=34,
        o_excluded_teams=0,
        o_excluded_solos=1,
    )


def test_divs_sizes_lt_72_teams():
    run_generate_divisions(
        i_teams=69,
        i_solos=3,
        o_div_sizes=[8, 8, 16, 22, 16],
        o_playing_teams=70,
        o_playing_solos=2,
        o_excluded_teams=0,
        o_excluded_solos=1,
    )


def test_divs_sizes_gt_72_teams():
    run_generate_divisions(
        i_teams=70,
        i_solos=9,
        o_div_sizes=[8, 8, 16, 26, 16],
        o_playing_teams=74,
        o_playing_solos=8,
        o_excluded_teams=0,
        o_excluded_solos=1,
    )


def test_divs_sizes_gt_88_teams():
    run_generate_divisions(
        i_teams=80,
        i_solos=22,
        o_div_sizes=[8, 8, 32, 27, 16],
        o_playing_teams=91,
        o_playing_solos=22,
        o_excluded_teams=0,
        o_excluded_solos=0,
    )


def test_divs_teams_only_no_solos():
    """All-team field: solos list is returned untouched as excluded_solos."""
    run_generate_divisions(
        i_teams=64,
        i_solos=0,
        o_div_sizes=[8, 8, 16, 16, 16],
        o_playing_teams=64,
        o_playing_solos=0,
        o_excluded_teams=0,
        o_excluded_solos=0,
    )


# ---------------------------------------------------------------------------
# sort_signups -- division generation + Sheet and Challonge writes
# ---------------------------------------------------------------------------
def _sort_event(confirmed=True):
    return {
        "data": {
            "options": [
                {
                    "name": "sort_signups",
                    "options": [{"name": "confirm", "value": confirmed}],
                }
            ]
        }
    }


def _stub_challonge():
    """A Challonge stub whose tournaments all exist."""
    challonge = MagicMock()
    challonge._get_tournament.return_value = {"tournament": {"id": 1}}
    return challonge


def test_sort_signups_cancelled_when_unconfirmed():
    gsheet = MagicMock()
    challonge = MagicMock()

    message = main.sort_signups(_sort_event(confirmed=False), gsheet, challonge)

    assert message == "Cancelled"
    gsheet.get_all_checkins.assert_not_called()
    challonge.add_participants_to_tournament.assert_not_called()


def test_sort_signups_missing_challonge_tournament_lookup_returns_falsy():
    """CHARACTERIZATION OF A KNOWN BUG.

    When `_get_tournament` returns falsy (tournament absent) *without*
    raising, `sort_signups` appends to `missing_challonges` but never binds
    `f_missing` -- so the missing-tournament return statement raises
    `UnboundLocalError`. `lambda_handler` wraps the call in a try/except, so
    in production this surfaces as the generic ":warning: Command failed
    unexpectedly" message. Pinned here so a later refactor is shown to
    preserve (or deliberately change) this behaviour.
    """
    gsheet = MagicMock()
    challonge = MagicMock()
    challonge._get_tournament.return_value = None

    with pytest.raises(UnboundLocalError):
        main.sort_signups(_sort_event(), gsheet, challonge)

    gsheet.get_all_checkins.assert_not_called()


def test_sort_signups_missing_challonge_tournament_lookup_raises():
    """When `_get_tournament` raises, the except branch binds `f_missing`
    and the handler returns the missing-tournaments message."""
    gsheet = MagicMock()
    challonge = MagicMock()
    challonge._get_tournament.side_effect = Exception("challonge unavailable")

    message = main.sort_signups(_sort_event(), gsheet, challonge)

    assert message.startswith(":no_entry: Tournaments are missing in Challonge:")
    gsheet.get_all_checkins.assert_not_called()


def test_sort_signups_writes_to_sheets_and_challonge():
    teams, solos = generate_checkins(64, 0)
    gsheet = MagicMock()
    gsheet.get_all_checkins.return_value = (teams, solos)
    gsheet.write_teams_to_div_sheets.return_value = True
    challonge = _stub_challonge()

    message = main.sort_signups(_sort_event(), gsheet, challonge)

    # Sheet write happens exactly once with the generated divisions.
    gsheet.write_teams_to_div_sheets.assert_called_once()
    written_divisions = gsheet.write_teams_to_div_sheets.call_args[0][0]
    assert [len(d) for d in written_divisions] == [8, 8, 16, 16, 16]

    # The handler calls add_participants_to_tournament twice (an unguarded
    # call followed by a try/except'd call) -- pin that current behaviour.
    assert challonge.add_participants_to_tournament.call_count == 2

    assert message.startswith(
        ":white_check_mark: Teams sorted in GSheets and added to Challonge:"
    )
    assert "Team Signups: 64" in message
    assert "Solo Signups: 0" in message
    assert "Total Teams Playing: 64" in message


def test_sort_signups_failed_sheet_write():
    teams, solos = generate_checkins(64, 0)
    gsheet = MagicMock()
    gsheet.get_all_checkins.return_value = (teams, solos)
    gsheet.write_teams_to_div_sheets.return_value = False
    challonge = _stub_challonge()

    message = main.sort_signups(_sort_event(), gsheet, challonge)

    assert message == (
        ":warning: Failed to write teams to division sheets or Challonge"
    )
    challonge.add_participants_to_tournament.assert_not_called()


def test_sort_signups_challonge_write_failure():
    teams, solos = generate_checkins(64, 0)
    gsheet = MagicMock()
    gsheet.get_all_checkins.return_value = (teams, solos)
    gsheet.write_teams_to_div_sheets.return_value = True
    challonge = _stub_challonge()
    # First add succeeds, second add raises HTTPError -> caught and reported.
    challonge.add_participants_to_tournament.side_effect = [None, HTTPError()]

    message = main.sort_signups(_sort_event(), gsheet, challonge)

    assert message == (
        ":warning: Successfully sorted teams but failed to add all teams "
        "to Challonge tournaments"
    )
