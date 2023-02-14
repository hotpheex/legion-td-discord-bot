import logging
import json
from pathlib import Path
from os import environ, replace

from requests import patch
from requests.exceptions import RequestException


import challonge
from constants import *


logging.getLogger().setLevel(logging.DEBUG)

GOOGLE_API_KEY = environ["GOOGLE_API_KEY"]
GOOGLE_SHEET_ID = environ["GOOGLE_SHEET_ID"]
APPLICATION_ID = environ["APPLICATION_ID"]


def results(event, tournament_id, participants):
    winning_team = event["data"]["options"][0]["value"]
    winning_score = event["data"]["options"][1]["value"]
    losing_score = event["data"]["options"][2]["value"]

    # TODO check if person is on team

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
        if m["match"]["player1_id"] == winning_team_id and m["match"]["state"] == "open":
            latest_match = m
            scores_csv = str(winning_score) + "-" + str(losing_score)
            losing_team_id = m["match"]["player2_id"]
        elif m["match"]["player2_id"] == winning_team_id and m["match"]["state"] == "open":
            latest_match = m
            scores_csv = str(losing_score) + "-" + str(winning_score)
            losing_team_id = m["match"]["player1_id"]

    if not latest_match or not scores_csv:
        return f":no_entry: No match in progress for {winning_team} (<https://challonge.com/{tournament_id}>)"

    # Update match with scores
    challonge._update_match(tournament_id, latest_match["match"]["id"], winning_team_id, scores_csv)

    losing_team = challonge._get_participant(tournament_id, losing_team_id)
    return f":white_check_mark: [Round {latest_match['match']['round']}] `{winning_team}` {winning_score}-{losing_score} `{losing_team['participant']['name']}`"


def lambda_handler(event, context):
    try:
        channel_id = event["channel_id"]
        tournament_id = CHANNEL_IDS[channel_id]

        # TODO check if tourney has started & hasnt stopped
        # https://api.challonge.com/v1/documents/tournaments/show


        if Path(f"/tmp/{tournament_id}.json").is_file():
            with open(f"/tmp/{tournament_id}.json", "r") as fh:
                participants = json.load(fh)
        else:
            participants = challonge._get_participants(tournament_id)
            with open(f"/tmp/{tournament_id}-{context.aws_request_id}.json", "w") as fh:
                json.dump(participants, fh)
                fh.flush()
            replace(f"/tmp/{tournament_id}-{context.aws_request_id}.json", f"/tmp/{tournament_id}.json")

        message = results(event, tournament_id, participants)
        logging.info(f"MESSAGE: {message}")

        response = patch(
            f"https://discord.com/api/webhooks/{APPLICATION_ID}/{event['token']}/messages/@original",
            json={"content": message},
        )
        logging.info(response.status_code)
        logging.debug(response.json())

    except RequestException as e:
        logging.error(e)
    except Exception as e:
        logging.error(e)
