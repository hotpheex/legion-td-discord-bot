"""
Admin commands to manage tournaments
"""
import json
import logging
import math
import os

import boto3
from requests.exceptions import HTTPError

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
    excluded_teams = []

    if not event["data"]["options"][0]["options"][0]["value"]:
        return "Cancelled"

    teams, solos = gsheet.get_all_checkins()

    # Ensure 8 top rated teams are always in
    teams_by_rating = sorted(teams, key=lambda x: x["rating"], reverse=True)
    div_1_size = get_div_sizes(MAX_TEAMS)[0]
    playing_teams = teams_by_rating[0: div_1_size - 1]

    logging.debug(json.dumps(playing_teams))

    # Fill with up to 104 teams in order of signup
    for team in teams:
        if len(playing_teams) == MAX_TEAMS:
            excluded_teams.append(team)
            continue
        if team not in playing_teams:
            playing_teams.append(team)

    logging.debug(json.dumps(playing_teams))
    logging.debug(json.dumps(excluded_teams))

    # If there is still room, fill with teams of solos in order of signup
    if len(playing_teams) < MAX_TEAMS:
        playing_solos = []
        excluded_solos = []
        teams_needed = MAX_TEAMS - len(playing_teams)

        for solo in solos:
            if len(playing_solos) < teams_needed * 2:
                playing_solos.append(solo)
            else:
                excluded_solos.append(solo)

        logging.debug(json.dumps(playing_solos))
        logging.debug(json.dumps(excluded_solos))

        # Pair up solos
        sorted_solos = sorted(playing_solos, key=lambda x: x["rating"], reverse=True)

        for i in range(0, len(sorted_solos), 2):
            p1 = sorted_solos[i]
            p2 = sorted_solos[i + 1]
            team_rating, _ = calculate_team_seed([p1["rating"], p2["rating"]])

            playing_teams.append(
                {
                    "team": f"{p1['player']}_{p2['player']}",
                    "player_1": p1["player"],
                    "player_2": p2["player"],
                    "rating": team_rating,
                }
            )
    else:
        excluded_solos = solos

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
    # TODO add try/except
    if not gsheet.write_teams_to_div_sheets(divisions):
        return ":warning: Failed to write teams to division sheets or Challonge"

    # Update Challonge brackets
    challonge.add_participants_to_tournament(divisions)
    try:
        challonge.add_participants_to_tournament(divisions)
    except HTTPError:
        return ":warning: Successfully sorted teams but failed to add all teams to Challonge tournaments"

    message = f":white_check_mark: Teams sorted in GSheets and added to Challonge:\n```Team Signups: {len(teams)}\nSolo Signups: {len(solos)}"
    for i in range(len(divisions)):
        message += f"\nDivision {i+1}: {len(divisions[i])}"
    if excluded_teams:
        message += f"\n\nTeams that were excluded:"
        for team in excluded_teams:
            message += f"\n{team['team']}"
    if excluded_solos:
        message += f"\n\nSolo players that were excluded:"
        for solo in excluded_solos:
            message += f"\n{solo['player']}"
    message += "\n```"
    return message

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
