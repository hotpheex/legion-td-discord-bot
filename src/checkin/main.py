"""
Handle checkin command
"""
import json
import logging
import os

import boto3

from libs.constants import *
from libs.discord import Discord
from libs.gsheets import GoogleSheet
from libs.platform import post_to_platform

# Google SA setup: https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account

if os.getenv("DEBUG") == "true":
    logging.getLogger().setLevel(logging.DEBUG)
else:
    logging.getLogger().setLevel(logging.INFO)

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
APPLICATION_ID = os.environ["APPLICATION_ID"]
CHECKIN_STATUS_PARAM = os.environ["CHECKIN_STATUS_PARAM"]
ALERT_WEBHOOK = os.environ["ALERT_WEBHOOK"]


def checkin(event, checkin_status):
    logging.info(event)
    sub_command = event["data"]["options"][0]["name"]
    player_name = event["member"]["nick"]
    if not player_name:
        player_name = event["member"]["user"]["global_name"]
    if not player_name:
        player_name = event["member"]["user"]["username"]
    channel_id = event["channel_id"]
    if sub_command == "team":
        team_name = event["data"]["options"][0]["options"][0]["value"]

    if checkin_status == "day_2":
        if sub_command == "solo":
            return f":no_entry: Solo players should check in as their team on Day 2"
        if CHANNEL_IDS[channel_id] == "Sign-up":
            return f":no_entry: Please use the appropriate #division-x channel on Day 2"
        gsheet = GoogleSheet(GOOGLE_API_KEY, GOOGLE_SHEET_ID, CHANNEL_IDS[channel_id])
    else:
        gsheet = GoogleSheet(GOOGLE_API_KEY, GOOGLE_SHEET_ID, SIGNUP_SHEET)

    query_column = COLUMNS[sub_command]["name"]

    if sub_command == "team":
        query_name = team_name
    elif sub_command == "solo":
        query_name = player_name
    else:
        raise Exception(f"{sub_command} is not a valid command")

    # Find Name Cell
    name_cell = gsheet.worksheet.find(
        query=query_name, case_sensitive=False, in_column=query_column
    )
    if not name_cell:
        return f":no_entry: `{query_name}` not found in the `{CHANNEL_IDS[channel_id]}` sheet\nPlease make sure your Discord nickname matches your in game name"
        # TODO Find and suggest the correct div channel
        # division = gsheet.search_player_all_divs(query_name, query_column)
        # if division:
        #     return f":no_entry: `{query_name}` is registered in {division}"
        # else:
        #     return f":no_entry: `{query_name}` not found in {CHANNEL_IDS[channel_id]}\nPlease make sure your Discord nickname matches your in game name"

    if sub_command == "team":
        if not gsheet.worksheet.find(
            query=player_name, case_sensitive=False, in_row=name_cell.row
        ):
            return f":no_entry: Player `{player_name}` is not on team `{team_name}`\nPlease make sure your Discord nickname matches your in game name"

    # Check if already checked in
    status_cell = gsheet.worksheet.cell(
        name_cell.row, COLUMNS[sub_command][checkin_status]
    )
    if status_cell.value == CHECKED_IN_MSG:
        return f":no_entry: `{query_name}` is already checked in"

    # Mark as checked in
    gsheet.worksheet.update_cell(
        name_cell.row, COLUMNS[sub_command][checkin_status], CHECKED_IN_MSG
    )
    gsheet.worksheet.format(
        f"{COLUMNS[sub_command]['format_range']}{name_cell.row}:{status_cell.address}",
        {"backgroundColor": COLORS[sub_command]},
    )

    return f":white_check_mark: `{query_name}` checked in!"


def build_checkin_payload(event, checkin_status):
    """Build the `/legacy/checkin` bridge payload from a check-in event.

    Mirrors how `checkin()` itself reads the event: a `team` sub-command
    carries a team name; a `solo` sub-command carries a player name (with
    the same nick -> global_name -> username fallback) and, when available,
    the interaction's Discord user id to bootstrap Player identity.
    """
    sub_command = event["data"]["options"][0]["name"]
    if sub_command == "team":
        team_name = event["data"]["options"][0]["options"][0]["value"]
        return {"team_name": team_name, "day": checkin_status}

    member = event.get("member", {})
    user = member.get("user", {})
    player_name = member.get("nick") or user.get("global_name") or user.get("username")
    payload = {"player_name": player_name, "day": checkin_status}
    discord_user_id = user.get("id")
    if discord_user_id:
        payload["discord_user_id"] = discord_user_id
    return payload


def lambda_handler(event, context):
    logging.debug(json.dumps(event))

    discord = Discord(APPLICATION_ID, event["token"])

    try:
        # Checkin Status
        client = boto3.client("ssm")
        response = client.get_parameter(Name=CHECKIN_STATUS_PARAM)
        logging.debug(response)
        checkin_status = response["Parameter"]["Value"]

        if checkin_status == "disabled":
            message = f":no_entry: Tournament checkins are not currently open"
        else:
            message = checkin(event, checkin_status)

        discord.message_response(message)

        # Parallel-run bridge: mirror the check-in to the new platform AFTER
        # the Discord reply. Fail-open -- never affects the handler.
        if checkin_status != "disabled":
            try:
                post_to_platform(
                    "/legacy/checkin", build_checkin_payload(event, checkin_status)
                )
            except Exception as bridge_error:  # noqa: BLE001 -- belt-and-braces
                logging.warning("Platform bridge hook failed: %s", bridge_error)
    except Exception as e:
        logging.exception(e)
        discord.exception_alert(ALERT_WEBHOOK, context)
        discord.message_response(":warning: Command failed unexpectedly")
