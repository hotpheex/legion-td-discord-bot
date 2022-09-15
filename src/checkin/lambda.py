"""
Handle checkin command
"""
import json
import logging
import os
from base64 import b64decode

import boto3
import gspread
from requests import patch
from requests.exceptions import RequestException

# Google SA setup: https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account

logging.getLogger().setLevel(logging.INFO)

GOOGLE_API_CREDS = os.environ["GOOGLE_API_CREDS"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
APPLICATION_ID = os.environ["APPLICATION_ID"]
CHECKIN_STATUS_PARAM = os.environ["CHECKIN_STATUS_PARAM"]

TEAM_COLUMN = 3
SOLO_COLUMN = 8
CHECKED_IN_COLOR = {
    "red": 0.203,
    "green": 0.658,
    "blue": 0.325,
}
CHECKED_IN_MSG = "Checked In"
CHANNEL_IDS = {
    "935116296587202632": "Division 4",
    "935116039400857620": "Division 3",
    "935116002000240680": "Division 2",
    "935115970945613884": "Division 1",
}
# Test Channel
CHANNEL_IDS["1019583590234849320"] = "Bot Test"


def get_checkin_status():
    client = boto3.client("ssm")
    response = client.get_parameter(Name=CHECKIN_STATUS_PARAM)
    logging.debug(response)

    if response["Parameter"]["Value"] == "true":
        return True
    elif response["Parameter"]["Value"] == "false":
        return False
    else:
        raise Exception()


def checkin(body):
    # Drop creds file on fs
    with open("/tmp/google_creds.json", "w") as fh:
        fh.write(b64decode(GOOGLE_API_CREDS).decode("utf-8"))

    sub_command = body["data"]["options"][0]["name"]
    player_name = body["member"]["nick"]
    if not player_name:
        player_name = body["member"]["user"]["username"]
    channel_id = body["channel_id"]
    if sub_command == "team":
        team_name = body["data"]["options"][0]["options"][0]["value"]

    gc = gspread.service_account(filename="/tmp/google_creds.json")
    sh = gc.open_by_key(GOOGLE_SHEET_ID)
    ws = sh.worksheet(CHANNEL_IDS[channel_id])

    if sub_command == "team":
        query_name = team_name
        query_column = TEAM_COLUMN
    elif sub_command == "solo":
        query_name = player_name
        query_column = SOLO_COLUMN
    else:
        raise Exception(f"{sub_command} is not a valid command")

    # Find Name Cell
    name_cell = ws.find(query=query_name, case_sensitive=False, in_column=query_column)
    if not name_cell:
        return f":no_entry: `{query_name}` not found in {CHANNEL_IDS[channel_id]}\nPlease make sure your Discord nickname matches your in game name"

    if sub_command == "team":
        if not ws.find(query=player_name, case_sensitive=False, in_row=name_cell.row):
            return f":no_entry: Player `{player_name}` is not on team `{team_name}`\nPlease make sure your Discord nickname matches your in game name"

    if sub_command == "solo":
        if player_name.lower() != name_cell.value.lower():
            return f":no_entry: Your nickname isn't `{name_cell.value}`!\nPlease make sure your Discord nickname matches your in game name"

    # Check if already checked in
    status_cell = ws.cell(name_cell.row, name_cell.col - 1)
    if status_cell.value == CHECKED_IN_MSG:
        return f":no_entry: `{query_name}` is already checked in"

    # Mark as checked in
    ws.update_cell(name_cell.row, name_cell.col - 1, CHECKED_IN_MSG)
    ws.format(
        f"{status_cell.address}:{name_cell.address}",
        {"backgroundColor": CHECKED_IN_COLOR},
    )

    return f":white_check_mark: `{query_name}` checked in!"


def lambda_handler(event, context):
    logging.debug(json.dumps(event))

    try:
        if not get_checkin_status():
            message = f":no_entry: Tournament checkins are not currently open"
        elif event["channel_id"] not in CHANNEL_IDS:
            message = f":no_entry: `/checkin` not supported in this channel"
        else:
            message = checkin(event)

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

    return True
