"""
Characterization tests for the `results` handler.

These pin the *current* behaviour of the unmodified `results` function:
match lookup against a Challonge tournament and the resulting score update.

Challonge is mocked at the boundary via the `Challonge` class the handler
imports -- no test touches a real Challonge API or the network. The handler
caches participants under `/tmp/{tournament_id}.json`; each test uses a
unique tournament id and cleans the file up so runs are independent.
"""
import glob
import os
import uuid
from unittest.mock import MagicMock, patch

import pytest

from results import main


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------
@pytest.fixture
def tournament_id():
    """A unique id per test so the /tmp participant cache never collides."""
    tid = f"test-{uuid.uuid4().hex}"
    yield tid
    # Final cache file plus any intermediate `{tid}-{aws_request_id}.json`
    # leaked by a mid-write failure.
    for path in [f"/tmp/{tid}.json", *glob.glob(f"/tmp/{tid}-*.json")]:
        if os.path.exists(path):
            os.remove(path)


def _context():
    ctx = MagicMock()
    ctx.aws_request_id = uuid.uuid4().hex
    return ctx


def results_event(winning_team="Winners", winning_score=2, losing_score=1):
    return {
        "data": {
            "options": [
                {"value": winning_team},
                {"value": winning_score},
                {"value": losing_score},
            ]
        }
    }


def participant(pid, name, group_player_ids=None):
    return {
        "participant": {
            "id": pid,
            "name": name,
            "group_player_ids": group_player_ids or [],
        }
    }


def match(match_id, player1_id, player2_id, state="open", round_=1):
    return {
        "match": {
            "id": match_id,
            "player1_id": player1_id,
            "player2_id": player2_id,
            "state": state,
            "round": round_,
        }
    }


def make_challonge(
    state="underway",
    name="Test Cup",
    participants=None,
    matches=None,
    losing_participant_name="Losers",
):
    """Build a mock Challonge instance for `results.main.Challonge`."""
    challonge = MagicMock()
    challonge._get_tournament.return_value = {
        "tournament": {"state": state, "name": name}
    }
    challonge._get_participants.return_value = participants or []
    challonge._get_matches.return_value = matches or []
    challonge._get_participant.return_value = {
        "participant": {"name": losing_participant_name}
    }
    challonge._update_match.return_value = {}
    return challonge


# ---------------------------------------------------------------------------
# Tournament-state short-circuits
# ---------------------------------------------------------------------------
@patch("results.main.Challonge")
def test_results_tournament_pending(mock_challonge_cls, tournament_id):
    mock_challonge_cls.return_value = make_challonge(state="pending")

    message = main.results(results_event(), _context(), tournament_id)

    assert message.startswith(":no_entry: Test Cup has not started yet")


@patch("results.main.Challonge")
def test_results_tournament_complete(mock_challonge_cls, tournament_id):
    mock_challonge_cls.return_value = make_challonge(state="complete")

    message = main.results(results_event(), _context(), tournament_id)

    assert message == ":no_entry: Test Cup has finished"


# ---------------------------------------------------------------------------
# Score validation
# ---------------------------------------------------------------------------
@patch("results.main.Challonge")
def test_results_winning_score_not_higher(mock_challonge_cls, tournament_id):
    mock_challonge_cls.return_value = make_challonge(state="underway")

    message = main.results(
        results_event(winning_score=1, losing_score=1), _context(), tournament_id
    )

    assert message == (
        ":no_entry: Winning score `1` must be higher than losing score `1`"
    )


# ---------------------------------------------------------------------------
# Match lookup
# ---------------------------------------------------------------------------
@patch("results.main.Challonge")
def test_results_team_not_found(mock_challonge_cls, tournament_id):
    challonge = make_challonge(
        state="underway",
        participants=[participant(101, "SomeOtherTeam")],
    )
    mock_challonge_cls.return_value = challonge

    message = main.results(
        results_event(winning_team="Winners"), _context(), tournament_id
    )

    assert message.startswith(":no_entry: Team `Winners` not found")
    challonge._update_match.assert_not_called()


@patch("results.main.Challonge")
def test_results_no_open_match(mock_challonge_cls, tournament_id):
    challonge = make_challonge(
        state="underway",
        participants=[participant(101, "Winners"), participant(102, "Losers")],
        matches=[match(900, 101, 102, state="complete")],
    )
    mock_challonge_cls.return_value = challonge

    message = main.results(
        results_event(winning_team="Winners"), _context(), tournament_id
    )

    assert message.startswith(":no_entry: No match in progress for Winners")
    challonge._update_match.assert_not_called()


# ---------------------------------------------------------------------------
# Successful score update
# ---------------------------------------------------------------------------
@patch("results.main.Challonge")
def test_results_score_update_winner_is_player1(mock_challonge_cls, tournament_id):
    challonge = make_challonge(
        state="underway",
        participants=[participant(101, "Winners"), participant(102, "Losers")],
        matches=[match(900, 101, 102, state="open", round_=3)],
        losing_participant_name="Losers",
    )
    mock_challonge_cls.return_value = challonge

    message = main.results(
        results_event(winning_team="Winners", winning_score=2, losing_score=1),
        _context(),
        tournament_id,
    )

    # winner is player1 -> scores_csv is "winning-losing".
    challonge._update_match.assert_called_once_with(tournament_id, 900, 101, "2-1")
    assert message == (
        ":white_check_mark: [Round 3] `Winners` 2-1 `Losers`"
    )


@patch("results.main.Challonge")
def test_results_score_update_winner_is_player2(mock_challonge_cls, tournament_id):
    challonge = make_challonge(
        state="underway",
        participants=[participant(101, "Losers"), participant(102, "Winners")],
        matches=[match(900, 101, 102, state="open", round_=1)],
        losing_participant_name="Losers",
    )
    mock_challonge_cls.return_value = challonge

    message = main.results(
        results_event(winning_team="Winners", winning_score=3, losing_score=0),
        _context(),
        tournament_id,
    )

    # winner is player2 -> scores_csv is flipped to "losing-winning".
    challonge._update_match.assert_called_once_with(tournament_id, 900, 102, "0-3")
    assert message == ":white_check_mark: [Round 1] `Winners` 3-0 `Losers`"


@patch("results.main.Challonge")
def test_results_participants_cache_reused(mock_challonge_cls, tournament_id):
    """Second invocation reads participants from the /tmp cache file rather
    than re-fetching them from Challonge."""
    challonge = make_challonge(
        state="underway",
        participants=[participant(101, "Winners"), participant(102, "Losers")],
        matches=[match(900, 101, 102, state="open")],
    )
    mock_challonge_cls.return_value = challonge

    main.results(results_event(winning_team="Winners"), _context(), tournament_id)
    main.results(results_event(winning_team="Winners"), _context(), tournament_id)

    # Participants fetched once; the cache file served the second call.
    challonge._get_participants.assert_called_once()
    assert os.path.exists(f"/tmp/{tournament_id}.json")
