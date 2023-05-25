"""
Commands for players to self report results
"""
import json
import logging
import os
from pathlib import Path

from libs.challonge import Challonge
from libs.constants import *
from libs.discord import Discord

if os.getenv("DEBUG") == "true":
    logging.getLogger().setLevel(logging.DEBUG)
else:
    logging.getLogger().setLevel(logging.INFO)

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
APPLICATION_ID = os.environ["APPLICATION_ID"]
ALERT_WEBHOOK = os.environ["ALERT_WEBHOOK"]
CHALLONGE_API_KEY = os.environ["CHALLONGE_API_KEY"]


def find_losing_team_id(participants, id):
    matching_participants = [
        p
        for p in participants
        if p["participant"]["id"] == id
        or (
            p["participant"]["group_player_ids"]
            and p["participant"]["group_player_ids"][0] == id
        )
    ]
    if matching_participants:
        return matching_participants[0]["participant"]["id"]
    else:
        return None


def results(event, context, tournament_id):
    winning_team = event["data"]["options"][0]["value"]
    winning_score = event["data"]["options"][1]["value"]
    losing_score = event["data"]["options"][2]["value"]

    challonge = Challonge(CHALLONGE_API_KEY)

    # Check is tournament is running
    t = challonge._get_tournament(tournament_id)
    tournament_state = t["tournament"]["state"]
    if tournament_state == "pending":
        return f':no_entry: {t["tournament"]["name"]} has not started yet <https://challonge.com/{tournament_id}>'
    elif tournament_state == "awaiting_review" or tournament_state == "complete":
        return f':no_entry: {t["tournament"]["name"]} has finished'

    # Random validations
    # TODO check if person is on team

    if winning_score <= losing_score:
        return f":no_entry: Winning score `{str(winning_score)}` must be higher than losing score `{str(losing_score)}`"

    # Get list of participants for tournament (and cache)
    if Path(f"/tmp/{tournament_id}.json").is_file():
        with open(f"/tmp/{tournament_id}.json", "r") as fh:
            participants = json.load(fh)
    else:
        participants = challonge._get_participants(tournament_id)
        with open(f"/tmp/{tournament_id}-{context.aws_request_id}.json", "w") as fh:
            json.dump(participants, fh)
            fh.flush()
        os.replace(
            f"/tmp/{tournament_id}-{context.aws_request_id}.json",
            f"/tmp/{tournament_id}.json",
        )
    logging.debug(json.dumps(participants))

    # Find winning team ID
    winning_team_id, winning_team_group_id = None, None
    for p in participants:
        if p["participant"]["name"].lower() == winning_team.lower():
            winning_team_id = p["participant"]["id"]
            winning_team_name = p["participant"]["name"]
            if len(p["participant"]["group_player_ids"]) > 0:
                winning_team_group_id = p["participant"]["group_player_ids"][0]

    if not (winning_team_id or winning_team_group_id):
        return f":no_entry: Team `{winning_team}` not found (<https://challonge.com/{tournament_id}>)"

    # Get team's latest match
    latest_match, scores_csv = None, None
    matches = challonge._get_matches(tournament_id)
    logging.debug(winning_team_id)
    logging.debug(winning_team_group_id)
    logging.debug(json.dumps(matches))
    for m in matches:
        if m["match"]["state"] == "open":
            if (
                m["match"]["player1_id"] == winning_team_id
                or m["match"]["player1_id"] == winning_team_group_id
            ):
                latest_match = m
                scores_csv = str(winning_score) + "-" + str(losing_score)
                losing_team_id = find_losing_team_id(
                    participants, m["match"]["player2_id"]
                )
            elif (
                m["match"]["player2_id"] == winning_team_id
                or m["match"]["player2_id"] == winning_team_group_id
            ):
                latest_match = m
                scores_csv = str(losing_score) + "-" + str(winning_score)
                losing_team_id = find_losing_team_id(
                    participants, m["match"]["player1_id"]
                )

    logging.debug(latest_match)
    logging.debug(scores_csv)
    if not latest_match or not scores_csv:
        return f":no_entry: No match in progress for {winning_team_name} (<https://challonge.com/{tournament_id}>)"

    # Update match with scores
    if (
        latest_match["match"]["player1_id"] == winning_team_group_id
        or latest_match["match"]["player2_id"] == winning_team_group_id
    ):
        winning_team_id = winning_team_group_id
    challonge._update_match(
        tournament_id, latest_match["match"]["id"], winning_team_id, scores_csv
    )

    losing_team = challonge._get_participant(tournament_id, losing_team_id)
    return f":white_check_mark: [Round {latest_match['match']['round']}] `{winning_team_name}` {winning_score}-{losing_score} `{losing_team['participant']['name']}`"


def lambda_handler(event, context):
    logging.debug(json.dumps(event))

    discord = Discord(APPLICATION_ID, event["token"])

    try:
        channel_id = event["channel_id"]
        tournament_id = RESULTS_CHANNEL_IDS[channel_id]

        message = results(event, context, tournament_id)
        discord.message_response(message)
    except Exception as e:
        logging.exception(e)
        discord.exception_alert(ALERT_WEBHOOK, context)
        discord.message_response(":warning: Command failed unexpectedly")
