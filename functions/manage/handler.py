"""
Admin commands to manage tournaments
"""

import json
import math
import os

import boto3
from aws_lambda_powertools import Logger
from libs.ssm_cache import get_ssm_param
from libs.challonge import Challonge
from libs.constants import *
from libs.discord import Discord
from libs.gsheets import GoogleSheet
from requests.exceptions import HTTPError
from .commands import COMMAND_REGISTRY
from .commands import discord_alert

# Initialize Powertools
logger = Logger()

logger.setLevel("DEBUG")

# Read environment variables at import time
CHECKIN_STATUS_PARAM = os.environ["CHECKIN_STATUS_PARAM"]
APPLICATION_ID = os.environ["APPLICATION_ID"]
ALERT_WEBHOOK_PARAM = os.environ["ALERT_WEBHOOK_PARAM"]
CHALLONGE_API_KEY_PARAM = os.environ["CHALLONGE_API_KEY_PARAM"]
GOOGLE_API_KEY_PARAM = os.environ["GOOGLE_API_KEY_PARAM"]
GOOGLE_SHEET_ID_PARAM = os.environ["GOOGLE_SHEET_ID_PARAM"]

def get_checkin_status(client, checkin_status_param):
    response = client.get_parameter(Name=checkin_status_param)
    logger.debug(response)
    return response["Parameter"]["Value"]


def set_checkin_status(client, event, checkin_status_param):
    current_status = get_checkin_status(client, checkin_status_param)
    desired_status = event["data"]["options"][0]["options"][0]["value"]

    if current_status == desired_status:
        return f"Checkins already set to `{current_status}`"
    else:
        response = client.put_parameter(
            Name=checkin_status_param, Value=str(desired_status).lower(), Overwrite=True
        )
        logger.debug(response)
        return f"Checkins are now set to `{desired_status}`"


def calculate_team_seed(ratings):
    team_rating = math.ceil((2 * max(ratings) + min(ratings)) / 3)
    return team_rating, f"Team rating for `{ratings}`: `{team_rating}`"


def clear_google_sheets(gsheet, event):
    if not event["data"]["options"][0]["options"][1]["value"]:
        return "Cancelled"

    gsheet.clear_spreadsheets(event["data"]["options"][0]["options"][0]["value"])
    return f":white_check_mark: Sheets Wiped"


def generate_divisions(teams, solos):
    playing_solos, excluded_teams, excluded_solos = [], [], []

    # Ensure 16 top rated teams are always in (div 1 & 2)
    div_1_size = get_div_sizes(MAX_TEAMS)[0]
    div_2_size = get_div_sizes(MAX_TEAMS)[1]
    playing_teams = sorted(teams, key=lambda x: x["rating"], reverse=True)[
        0 : div_1_size + div_2_size
    ]

    logger.debug("include_div_1-2 " + json.dumps(playing_teams))

    # Fill with up to MAX_TEAMS teams in order of signup
    for team in teams:
        if len(playing_teams) == MAX_TEAMS:
            excluded_teams.append(team)
            continue
        if team not in playing_teams:
            playing_teams.append(team)

    # If there are not enough teams, fill with solos in order of signup
    if len(playing_teams) < MAX_TEAMS:
        teams_needed = MAX_TEAMS - len(playing_teams)

        # Sort solos by rating
        for solo in solos:
            if len(playing_solos) < teams_needed * 2:
                playing_solos.append(solo)
            else:
                excluded_solos.append(solo)

        # If there is an odd number of solos, exclude the lowest rated
        if len(playing_solos) % 2 == 1:
            excluded_solos.append(playing_solos.pop())

        # Sort solos into teams
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

    # Sort teams by rating
    sorted_teams = sorted(playing_teams, key=lambda x: x["rating"], reverse=True)
    div_sizes = get_div_sizes(len(sorted_teams))
    divisions = []
    team_index = 0

    # Determine last division that will contain players
    last_div_index = 0
    for i in range(len(div_sizes)):
        if len(sorted_teams) > sum(div_sizes[0:i]):
            last_div_index = i

    logger.debug("last_div_index " + str(last_div_index))

    # Fill last division with teams
    last_div = [sorted_teams[-div_sizes[last_div_index] :]]
    sorted_teams = sorted_teams[: -div_sizes[last_div_index]]

    logger.debug("last_div " + json.dumps(last_div))

    # Fill other divisions with teams top to bottom
    for i in range(len(div_sizes)):
        divisions.append(sorted_teams[team_index : team_index + div_sizes[i]])
        team_index += div_sizes[i]

    # Add the last division
    divisions[last_div_index] = last_div[0]

    logger.debug("playing_solos " + json.dumps(playing_solos))
    logger.debug("playing_teams " + json.dumps(playing_teams))
    logger.debug("excluded_solos " + json.dumps(excluded_solos))
    logger.debug("excluded_teams " + json.dumps(excluded_teams))

    return (
        divisions,
        playing_teams,
        playing_solos,
        excluded_teams,
        excluded_solos,
    )


def sort_signups(event, gsheet, challonge):
    if not event["data"]["options"][0]["options"][0]["value"]:
        return "Cancelled"

    # Check Challonge ID's are correct
    missing_challonges = []
    f_missing = []
    for division in DIVISIONS.values():
        tournament = division["challonge"]
        try:
            exists = challonge._get_tournament(tournament)
            if not exists:
                missing_challonges.append(tournament)
        except Exception:
            f_missing = [f"`{challonge}`" for challonge in missing_challonges]
            missing_challonges.append(tournament)

    if missing_challonges:
        return (
            f":no_entry: Tournaments are missing in Challonge: {', '.join(f_missing)}"
        )

    # Get checkins from Google Sheets
    teams, solos = gsheet.get_all_checkins()
    divisions, playing_teams, _, excluded_teams, excluded_solos = generate_divisions(
        teams, solos
    )

    # TODO add try/except
    # Write divs to team list sheet
    if not gsheet.write_teams_to_div_sheets(divisions):
        return ":warning: Failed to write teams to division sheets or Challonge"

    # Update Challonge brackets
    challonge.add_participants_to_tournament(divisions)
    try:
        challonge.add_participants_to_tournament(divisions)
    except HTTPError:
        return ":warning: Successfully sorted teams but failed to add all teams to Challonge tournaments"

    message = f":white_check_mark: Teams sorted in GSheets and added to Challonge:\n```Team Signups: {len(teams)}\nSolo Signups: {len(solos)}\nTotal Teams Playing: {len(playing_teams)}\n"
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


def handler(event, context):
    logger.debug(json.dumps(event))
    detail = event.get('detail', {})
    body = detail.get('discord_event', {})
    token = body.get('token')
    discord = Discord(APPLICATION_ID, token)

    # Shared clients/utilities
    client = boto3.client("ssm")
    challonge = Challonge(get_ssm_param(CHALLONGE_API_KEY_PARAM))
    gsheet = GoogleSheet(get_ssm_param(GOOGLE_API_KEY_PARAM), get_ssm_param(GOOGLE_SHEET_ID_PARAM), SIGNUP_SHEET)
    ALERT_WEBHOOK = get_ssm_param(ALERT_WEBHOOK_PARAM)

    try:
        sub_command = body["data"]["options"][0]["name"]
        handler_fn = COMMAND_REGISTRY.get(sub_command)
        if not handler_fn:
            raise Exception(f"{sub_command} is not a valid command")
        # Call the subcommand handler, passing all shared clients/utilities and config
        message = handler_fn(
            body,
            client=client,
            gsheet=gsheet,
            challonge=challonge,
            discord=discord,
            logger=logger,
            context=context,
            CHECKIN_STATUS_PARAM=CHECKIN_STATUS_PARAM,
            APPLICATION_ID=APPLICATION_ID,
            ALERT_WEBHOOK=ALERT_WEBHOOK,
        )
        discord.message_response(message)
        return message
    except Exception as e:
        logger.exception(e)
        # Call the discord_alert subcommand
        discord_alert(body, logger=logger, discord=discord, context=context, alert_webhook=ALERT_WEBHOOK)
        discord.message_response(":warning: Command failed unexpectedly")
        return ":warning: Command failed unexpectedly"
