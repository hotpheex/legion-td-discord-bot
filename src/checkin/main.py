"""
Handle checkin command
"""
import json
import logging
import traceback
from base64 import b64decode
from os import environ

import boto3
import gspread
from ..libs.constants import *
from requests import patch, post

# Google SA setup: https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account

logging.getLogger().setLevel(logging.INFO)

GOOGLE_API_KEY = environ["GOOGLE_API_KEY"]
GOOGLE_SHEET_ID = environ["GOOGLE_SHEET_ID"]
APPLICATION_ID = environ["APPLICATION_ID"]
CHECKIN_STATUS_PARAM = environ["CHECKIN_STATUS_PARAM"]
ALERT_WEBHOOK = environ["ALERT_WEBHOOK"]


def find_name_in_divisions(sheet, query_name, query_column):
    worksheets = sheet.worksheets()
    for sheet in worksheets:
        name_cell = sheet.find(
            query=query_name, case_sensitive=False, in_column=query_column
        )
        if name_cell:
            return sheet.title
    return False


def checkin(event, checkin_status):
    gcreds = json.loads(b64decode(GOOGLE_API_KEY).decode("utf-8"))
    gc = gspread.service_account_from_dict(gcreds, client_factory=gspread.BackoffClient)

    sub_command = event["data"]["options"][0]["name"]
    player_name = event["member"]["nick"]
    if not player_name:
        player_name = event["member"]["user"]["username"]
    channel_id = event["channel_id"]
    if sub_command == "team":
        team_name = event["data"]["options"][0]["options"][0]["value"]

    sh = gc.open_by_key(GOOGLE_SHEET_ID)
    ws = sh.worksheet(CHANNEL_IDS[channel_id])

    query_column = COLUMNS[sub_command]["name"]

    if sub_command == "team":
        query_name = team_name
    elif sub_command == "solo":
        query_name = player_name
    else:
        raise Exception(f"{sub_command} is not a valid command")

    # Find Name Cell
    name_cell = ws.find(query=query_name, case_sensitive=False, in_column=query_column)
    if not name_cell:
        division = find_name_in_divisions(sh, query_name, query_column)
        if division:
            return f":no_entry: `{query_name}` is registered in {division}"
        else:
            return f":no_entry: `{query_name}` not found in {CHANNEL_IDS[channel_id]}\nPlease make sure your Discord nickname matches your in game name"

    if sub_command == "team":
        if not ws.find(query=player_name, case_sensitive=False, in_row=name_cell.row):
            return f":no_entry: Player `{player_name}` is not on team `{team_name}`\nPlease make sure your Discord nickname matches your in game name"

    if sub_command == "solo":
        if checkin_status == "day_2":
            return f":no_entry: Solo players do not need to checkin on Day 2"

    # Check if already checked in
    status_cell = ws.cell(name_cell.row, COLUMNS[sub_command][checkin_status])
    if status_cell.value == CHECKED_IN_MSG:
        return f":no_entry: `{query_name}` is already checked in"

    # Mark as checked in
    ws.update_cell(name_cell.row, COLUMNS[sub_command][checkin_status], CHECKED_IN_MSG)
    if checkin_status == "day_1":
        ws.format(
            f"{COLUMNS[sub_command]['day_1_range']}{name_cell.row}:{status_cell.address}",
            {"backgroundColor": COLORS[sub_command]},
        )
    else:
        ws.format(
            f"{status_cell.address}:{status_cell.address}",
            {"backgroundColor": COLORS[sub_command]},
        )

    return f":white_check_mark: `{query_name}` checked in!"


def lambda_handler(event, context):
    logging.debug(json.dumps(event))

    try:
        # Checkin Status
        client = boto3.client("ssm")
        response = client.get_parameter(Name=CHECKIN_STATUS_PARAM)
        logging.debug(response)
        checkin_status = response["Parameter"]["Value"]

        if checkin_status == "disabled":
            message = f":no_entry: Tournament checkins are not currently open"
        elif event["channel_id"] not in CHANNEL_IDS:
            message = f":no_entry: `/checkin` not supported in this channel"
        else:
            message = checkin(event, checkin_status)

        logging.info(f"MESSAGE: {message}")

        response = patch(
            f"https://discord.com/api/webhooks/{APPLICATION_ID}/{event['token']}/messages/@original",
            json={"content": message},
        )
        response.raise_for_status()
        logging.info(response.status_code)
        logging.debug(response.json())
    except Exception as e:
        logging.exception(e)
        post(
            ALERT_WEBHOOK,
            json={
                "content": f"`{context.function_name} - {context.log_stream_name}`\n```{traceback.format_exc()}```"
            },
        )
        patch(
            f"https://discord.com/api/webhooks/{APPLICATION_ID}/{event['token']}/messages/@original",
            json={"content": ":warning: Command failed unexpectedly"},
        )
