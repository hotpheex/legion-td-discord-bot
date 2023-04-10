"""
Admin commands to manage tournaments
"""
import json
import logging
import math
import os

import boto3

from libs.constants import *
from libs.challonge import Challonge
from libs.discord import Discord
from libs.gsheets import GoogleSheet


if os.getenv("DEBUG") == "true":
    logging.getLogger().setLevel(logging.DEBUG)
else:
    logging.getLogger().setLevel(logging.INFO)

CHECKIN_STATUS_PARAM = os.environ["CHECKIN_STATUS_PARAM"]
APPLICATION_ID = os.environ["APPLICATION_ID"]
ALERT_WEBHOOK = os.environ["ALERT_WEBHOOK"]
CHALLONGE_API_KEY = os.environ["CHALLONGE_API_KEY"]
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]


def get_checkin_status(client):
    response = client.get_parameter(Name=CHECKIN_STATUS_PARAM)
    logging.debug(response)
    return response["Parameter"]["Value"]


def set_checkin_status(client, event):
    current_status = get_checkin_status(client)
    desired_status = event["data"]["options"][0]["options"][0]["value"]

    if current_status == desired_status:
        return f"Checkins already set to `{current_status}`"
    else:
        response = client.put_parameter(
            Name=CHECKIN_STATUS_PARAM, Value=str(desired_status).lower(), Overwrite=True
        )
        logging.debug(response)
        return f"Checkins are now set to `{desired_status}`"


def calculate_team_seed(ratings):
    team_rating = math.ceil((2 * max(ratings) + min(ratings)) / 3)

    return team_rating, f"Team rating for `{ratings}`: `{team_rating}`"


def sort_signups(event, gsheet, challonge):
    if not event["data"]["options"][0]["options"][0]["value"]:
        return "Cancelled"
    teams, solos = gsheet.get_all_checkins()

    # Pair up solos
    leftover = None
    sorted_solos = sorted(solos, key=lambda x: x["rating"], reverse=True)
    if len(sorted_solos) % 2 != 0:
        leftover = sorted_solos.pop()

    for i in range(0, len(sorted_solos), 2):
        p1 = sorted_solos[i]
        p2 = sorted_solos[i + 1]
        ratings = [p1["rating"], p2["rating"]]
        team_rating, _ = calculate_team_seed(ratings)

        teams.append(
            {
                "team": f"{p1['player']} {p2['player']}",
                "player_1": p1["player"],
                "player_2": p2["player"],
                "rating": team_rating,
            }
        )

    # Sort teams into divisions
    sorted_teams = sorted(teams, key=lambda x: x["rating"], reverse=True)
    div_sizes = get_div_sizes(len(sorted_teams))

    # Sort teams into divisions
    divisions = []
    team_index = 0
    for size in div_sizes:
        divisions.append(sorted_teams[team_index : team_index + size])
        team_index += size

    # Write divs to team list sheet
    if not gsheet.write_teams_to_div_sheets(divisions):
        return "Failed to write teams to division sheets"

    # Update Challonge brackets
    challonge.add_participants_to_tournament(divisions)

    message = f":white_check_mark: Teams sorted in GSheets and added to Challonge:\n```Total teams: {len(sorted_teams)}\nSolo Signups: {len(solos)}"
    for i in range(len(divisions)):
        message += f"\nDivision {i+1}: {len(divisions[i])}"
    message += "```"
    if leftover:
        message += f"\n:cry: A solo player didn't get a team: `{leftover['player']}`"
    return message
    # return f":white_check_mark: Teams sorted in GSheets and added to Challonge:\nTotal teams: {len(sorted_teams)}\nDiv 1: {len(divisions[0])}\nDiv 2: {len(divisions[1])}\nDiv 3: {len(divisions[2])}\nDiv 4: {len(divisions[3])}\nDiv 5: {len(divisions[4])}"


def run(event, context):
    logging.debug(json.dumps(event))

    client = boto3.client("ssm")
    challonge = Challonge(CHALLONGE_API_KEY)
    discord = Discord(APPLICATION_ID, event["token"])
    gsheet = GoogleSheet(GOOGLE_API_KEY, GOOGLE_SHEET_ID, SIGNUP_SHEET)

    try:
        sub_command = event["data"]["options"][0]["name"]
        if sub_command == "checkin_status":
            current_status = get_checkin_status(client)
            message = f"Checkins are currently set to `{current_status}`"
        elif sub_command == "checkin_enabled":
            message = set_checkin_status(client, event)
        elif sub_command == "calculate_seed":
            ratings = []
            for player in event["data"]["options"][0]["options"]:
                ratings.append(player["value"])
            _, message = calculate_team_seed(ratings)
        elif sub_command == "sort_signups":
            message = sort_signups(event, gsheet, challonge)
        else:
            raise Exception(f"{sub_command} is not a valid command")

        discord.message_response(message)
    except Exception as e:
        logging.exception(e)
        discord.exception_alert(ALERT_WEBHOOK, context)
        discord.message_response(":warning: Command failed unexpectedly")
