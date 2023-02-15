import json
import logging
from os import environ, replace
from pathlib import Path

import challonge
from constants import *
from requests import patch
from requests.exceptions import RequestException

logging.getLogger().setLevel(logging.INFO)

GOOGLE_API_KEY = environ["GOOGLE_API_KEY"]
GOOGLE_SHEET_ID = environ["GOOGLE_SHEET_ID"]
APPLICATION_ID = environ["APPLICATION_ID"]


def results(event, context, tournament_id):
    winning_team = event["data"]["options"][0]["value"]
    winning_score = event["data"]["options"][1]["value"]
    losing_score = event["data"]["options"][2]["value"]

    # Check is tournament is running
    t = challonge._get_tournament(tournament_id)
    tournament_state = t["tournament"]["state"]
    if tournament_state == "pending":
        return f':no_entry: {t["tournament"]["name"]} has not started yet <https://challonge.com/{tournament_id}>'
    elif (
        tournament_state == "awaiting_review"
        or tournament_state == "complete"
    ):
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
        replace(
            f"/tmp/{tournament_id}-{context.aws_request_id}.json",
            f"/tmp/{tournament_id}.json",
        )

    # Find winning team ID
    winning_team_id = None
    for p in participants:
        if p["participant"]["name"] == winning_team:
            winning_team_id = p["participant"]["id"]

    if not winning_team_id:
        return f":no_entry: Team `{winning_team}` not found (<https://challonge.com/{tournament_id}>)"

    # Get team's latest match
    matches = challonge._get_matches(tournament_id)
    latest_match, scores_csv, losing_team_id = None, None, None
    for m in matches:
        if (
            m["match"]["player1_id"] == winning_team_id
            and m["match"]["state"] == "open"
        ):
            latest_match = m
            scores_csv = str(winning_score) + "-" + str(losing_score)
            losing_team_id = m["match"]["player2_id"]
        elif (
            m["match"]["player2_id"] == winning_team_id
            and m["match"]["state"] == "open"
        ):
            latest_match = m
            scores_csv = str(losing_score) + "-" + str(winning_score)
            losing_team_id = m["match"]["player1_id"]


    if not latest_match or not scores_csv:
        return f":no_entry: No match in progress for {winning_team} (<https://challonge.com/{tournament_id}>)"

    # Update match with scores
    challonge._update_match(
        tournament_id, latest_match["match"]["id"], winning_team_id, scores_csv
    )

    losing_team = challonge._get_participant(tournament_id, losing_team_id)
    return f":white_check_mark: [Round {latest_match['match']['round']}] `{winning_team}` {winning_score}-{losing_score} `{losing_team['participant']['name']}`"


def lambda_handler(event, context):
    try:
        channel_id = event["channel_id"]
        tournament_id = CHANNEL_IDS[channel_id]

        message = results(event, context, tournament_id)
        logging.info(f"MESSAGE: {message}")

        response = patch(
            f"https://discord.com/api/webhooks/{APPLICATION_ID}/{event['token']}/messages/@original",
            json={"content": message},
        )
        response.raise_for_status()
        logging.info(response.status_code)
        logging.debug(response.json())

    except RequestException as e:
        logging.error(e)
    except Exception as e:
        logging.error(e)
