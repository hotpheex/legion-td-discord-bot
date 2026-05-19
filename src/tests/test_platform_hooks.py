"""
Tests for the parallel-run platform-bridge hooks wired into the
`checkin`, `manage`/`sort_signups` and `results` handlers (issue #118).

Two layers are covered:

* the pure payload builders (`build_checkin_payload`, `build_sort_payload`),
  which translate handler data into the `/legacy/*` request shapes; and
* the `lambda_handler` integration -- that `post_to_platform` is invoked,
  with the right endpoint and payload, AFTER the Discord reply, and that a
  failing bridge call never breaks the handler.

`post_to_platform` and every external service are mocked; no test makes a
real network call.
"""
from unittest.mock import MagicMock, call, patch

import pytest

from checkin import main as checkin_main
from manage import main as manage_main
from results import main as results_main


# ===========================================================================
# checkin -- build_checkin_payload
# ===========================================================================
def _team_checkin_event(team_name="Team Rocket", channel_id="1023401872750547014"):
    return {
        "token": "tok",
        "channel_id": channel_id,
        "data": {
            "options": [
                {"name": "team", "options": [{"name": "team", "value": team_name}]}
            ]
        },
        "member": {
            "nick": "Bob",
            "user": {"id": "discord-123", "global_name": "BobG", "username": "bob"},
        },
    }


def _solo_checkin_event(nick="Alice", channel_id="1023401872750547014", user=None):
    return {
        "token": "tok",
        "channel_id": channel_id,
        "data": {"options": [{"name": "solo"}]},
        "member": {
            "nick": nick,
            "user": user
            if user is not None
            else {"id": "discord-999", "global_name": "AliceG", "username": "alice"},
        },
    }


def test_build_checkin_payload_team():
    payload = checkin_main.build_checkin_payload(
        _team_checkin_event(team_name="Winners"), "day_2"
    )
    assert payload == {"team_name": "Winners", "day": "day_2"}


def test_build_checkin_payload_solo_with_discord_id():
    payload = checkin_main.build_checkin_payload(_solo_checkin_event(nick="Alice"), "day_1")
    assert payload == {
        "player_name": "Alice",
        "day": "day_1",
        "discord_user_id": "discord-999",
    }


def test_build_checkin_payload_solo_name_fallback():
    """nick -> global_name -> username fallback, mirroring `checkin()`."""
    event = _solo_checkin_event(
        nick="", user={"global_name": "", "username": "fallback_user"}
    )
    payload = checkin_main.build_checkin_payload(event, "day_1")
    assert payload["player_name"] == "fallback_user"
    # No Discord id available -> field omitted.
    assert "discord_user_id" not in payload


# ===========================================================================
# checkin -- lambda_handler hook
# ===========================================================================
@patch("checkin.main.post_to_platform")
@patch("checkin.main.boto3")
@patch("checkin.main.Discord")
@patch("checkin.main.checkin")
def test_checkin_handler_notifies_platform_after_reply(
    mock_checkin, mock_discord_cls, mock_boto3, mock_post
):
    discord = mock_discord_cls.return_value
    mock_checkin.return_value = ":white_check_mark: ok"
    mock_boto3.client.return_value.get_parameter.return_value = {
        "Parameter": {"Value": "day_1"}
    }

    checkin_main.lambda_handler(_team_checkin_event(team_name="Rocket"), MagicMock())

    mock_post.assert_called_once_with(
        "/legacy/checkin", {"team_name": "Rocket", "day": "day_1"}
    )
    # The platform call happens AFTER the Discord reply.
    assert discord.message_response.called


@patch("checkin.main.post_to_platform")
@patch("checkin.main.boto3")
@patch("checkin.main.Discord")
@patch("checkin.main.checkin")
def test_checkin_handler_skips_platform_when_checkins_disabled(
    mock_checkin, mock_discord_cls, mock_boto3, mock_post
):
    mock_boto3.client.return_value.get_parameter.return_value = {
        "Parameter": {"Value": "disabled"}
    }

    checkin_main.lambda_handler(_team_checkin_event(), MagicMock())

    mock_post.assert_not_called()


@patch("checkin.main.post_to_platform")
@patch("checkin.main.boto3")
@patch("checkin.main.Discord")
@patch("checkin.main.checkin")
def test_checkin_handler_unaffected_by_bridge_failure(
    mock_checkin, mock_discord_cls, mock_boto3, mock_post
):
    """A raising bridge hook must not surface as a handler failure."""
    discord = mock_discord_cls.return_value
    mock_checkin.return_value = ":white_check_mark: ok"
    mock_boto3.client.return_value.get_parameter.return_value = {
        "Parameter": {"Value": "day_1"}
    }
    mock_post.side_effect = RuntimeError("bridge exploded")

    # Must not raise.
    checkin_main.lambda_handler(_team_checkin_event(), MagicMock())

    # The user still got the real reply, not the generic failure message.
    discord.message_response.assert_called_once_with(":white_check_mark: ok")


# ===========================================================================
# manage -- build_sort_payload
# ===========================================================================
def test_build_sort_payload_shape_and_order():
    divisions = [
        [
            {"team": "A", "player_1": "a1", "player_2": "a2", "rating": 2000},
            {"team": "B", "player_1": "b1", "player_2": "b2", "rating": 1900},
        ],
        [
            {"team": "C", "player_1": "c1", "player_2": "c2", "rating": 1500},
        ],
    ]

    payload = manage_main.build_sort_payload(divisions)

    assert payload == {
        "divisions": [
            {
                "division_number": 1,
                "teams": [
                    {
                        "team_name": "A",
                        "player_1": "a1",
                        "player_2": "a2",
                        "rating": 2000,
                    },
                    {
                        "team_name": "B",
                        "player_1": "b1",
                        "player_2": "b2",
                        "rating": 1900,
                    },
                ],
            },
            {
                "division_number": 2,
                "teams": [
                    {
                        "team_name": "C",
                        "player_1": "c1",
                        "player_2": "c2",
                        "rating": 1500,
                    }
                ],
            },
        ]
    }


def test_sort_signups_populates_divisions_out():
    """The optional `divisions_out` accumulator collects the layout without
    altering the return value."""
    teams = [
        {"team": f"T{i}", "player_1": f"p{i}a", "player_2": f"p{i}b", "rating": 1500 + i}
        for i in range(64)
    ]
    gsheet = MagicMock()
    gsheet.get_all_checkins.return_value = (teams, [])
    gsheet.write_teams_to_div_sheets.return_value = True
    challonge = MagicMock()
    challonge._get_tournament.return_value = {"tournament": {"id": 1}}

    collected = []
    message = manage_main.sort_signups(
        {
            "data": {
                "options": [
                    {
                        "name": "sort_signups",
                        "options": [{"name": "confirm", "value": True}],
                    }
                ]
            }
        },
        gsheet,
        challonge,
        collected,
    )

    assert message.startswith(":white_check_mark:")
    assert [len(d) for d in collected] == [8, 8, 16, 16, 16]


# ===========================================================================
# manage -- lambda_handler hook
# ===========================================================================
@patch("manage.main.post_to_platform")
@patch("manage.main.GoogleSheet")
@patch("manage.main.Discord")
@patch("manage.main.Challonge")
@patch("manage.main.boto3")
def test_sort_handler_notifies_platform_after_reply(
    mock_boto3, mock_challonge_cls, mock_discord_cls, mock_gsheet_cls, mock_post
):
    discord = mock_discord_cls.return_value
    teams = [
        {"team": f"T{i}", "player_1": f"p{i}a", "player_2": f"p{i}b", "rating": 1500 + i}
        for i in range(64)
    ]
    gsheet = mock_gsheet_cls.return_value
    gsheet.get_all_checkins.return_value = (teams, [])
    gsheet.write_teams_to_div_sheets.return_value = True
    challonge = mock_challonge_cls.return_value
    challonge._get_tournament.return_value = {"tournament": {"id": 1}}

    event = {
        "token": "tok",
        "data": {
            "options": [
                {
                    "name": "sort_signups",
                    "options": [{"name": "confirm", "value": True}],
                }
            ]
        },
    }
    manage_main.lambda_handler(event, MagicMock())

    assert mock_post.call_count == 1
    endpoint, payload = mock_post.call_args[0]
    assert endpoint == "/legacy/sort"
    assert [d["division_number"] for d in payload["divisions"]] == [1, 2, 3, 4, 5]
    assert [len(d["teams"]) for d in payload["divisions"]] == [8, 8, 16, 16, 16]
    assert discord.message_response.called


@patch("manage.main.post_to_platform")
@patch("manage.main.GoogleSheet")
@patch("manage.main.Discord")
@patch("manage.main.Challonge")
@patch("manage.main.boto3")
def test_non_sort_subcommand_does_not_notify_platform(
    mock_boto3, mock_challonge_cls, mock_discord_cls, mock_gsheet_cls, mock_post
):
    """`calculate_seed` and friends never touch the bridge."""
    event = {
        "token": "tok",
        "data": {
            "options": [
                {"name": "calculate_seed", "options": [{"value": 2000}, {"value": 1800}]}
            ]
        },
    }
    manage_main.lambda_handler(event, MagicMock())

    mock_post.assert_not_called()


@patch("manage.main.post_to_platform")
@patch("manage.main.GoogleSheet")
@patch("manage.main.Discord")
@patch("manage.main.Challonge")
@patch("manage.main.boto3")
def test_sort_handler_unaffected_by_bridge_failure(
    mock_boto3, mock_challonge_cls, mock_discord_cls, mock_gsheet_cls, mock_post
):
    discord = mock_discord_cls.return_value
    teams = [
        {"team": f"T{i}", "player_1": f"p{i}a", "player_2": f"p{i}b", "rating": 1500 + i}
        for i in range(64)
    ]
    gsheet = mock_gsheet_cls.return_value
    gsheet.get_all_checkins.return_value = (teams, [])
    gsheet.write_teams_to_div_sheets.return_value = True
    challonge = mock_challonge_cls.return_value
    challonge._get_tournament.return_value = {"tournament": {"id": 1}}
    mock_post.side_effect = RuntimeError("bridge exploded")

    event = {
        "token": "tok",
        "data": {
            "options": [
                {
                    "name": "sort_signups",
                    "options": [{"name": "confirm", "value": True}],
                }
            ]
        },
    }
    # Must not raise.
    manage_main.lambda_handler(event, MagicMock())

    # The success reply was delivered, not the generic failure message.
    assert discord.message_response.call_count == 1
    assert discord.message_response.call_args[0][0].startswith(":white_check_mark:")


# ===========================================================================
# results -- lambda_handler hook
# ===========================================================================
def _results_event(winning_team="Winners", winning_score=2, losing_score=1):
    return {
        "token": "tok",
        "channel_id": "1023401872750547014",  # maps to a real RESULTS tournament id
        "data": {
            "options": [
                {"value": winning_team},
                {"value": winning_score},
                {"value": losing_score},
            ]
        },
    }


@patch("results.main.post_to_platform")
@patch("results.main.Discord")
@patch("results.main.results")
def test_results_handler_notifies_platform_after_reply(
    mock_results, mock_discord_cls, mock_post
):
    discord = mock_discord_cls.return_value

    def fake_results(event, context, tournament_id, result_out=None):
        # Simulate the success path populating the accumulator.
        if result_out is not None:
            result_out.update(
                {
                    "winning_team_name": "Winners",
                    "winning_score": 2,
                    "losing_score": 1,
                }
            )
        return ":white_check_mark: recorded"

    mock_results.side_effect = fake_results

    results_main.lambda_handler(_results_event(), MagicMock())

    mock_post.assert_called_once_with(
        "/legacy/results",
        {"winning_team_name": "Winners", "winning_score": 2, "losing_score": 1},
    )
    assert discord.message_response.called


@patch("results.main.post_to_platform")
@patch("results.main.Discord")
@patch("results.main.results")
def test_results_handler_skips_platform_on_non_success(
    mock_results, mock_discord_cls, mock_post
):
    """A short-circuit return (e.g. team not found) leaves the accumulator
    empty -- nothing is mirrored to the platform."""
    mock_results.return_value = ":no_entry: Team `Ghost` not found"

    results_main.lambda_handler(_results_event(winning_team="Ghost"), MagicMock())

    mock_post.assert_not_called()


@patch("results.main.post_to_platform")
@patch("results.main.Discord")
@patch("results.main.results")
def test_results_handler_unaffected_by_bridge_failure(
    mock_results, mock_discord_cls, mock_post
):
    discord = mock_discord_cls.return_value

    def fake_results(event, context, tournament_id, result_out=None):
        if result_out is not None:
            result_out.update(
                {
                    "winning_team_name": "Winners",
                    "winning_score": 2,
                    "losing_score": 1,
                }
            )
        return ":white_check_mark: recorded"

    mock_results.side_effect = fake_results
    mock_post.side_effect = RuntimeError("bridge exploded")

    # Must not raise.
    results_main.lambda_handler(_results_event(), MagicMock())

    discord.message_response.assert_called_once_with(":white_check_mark: recorded")
