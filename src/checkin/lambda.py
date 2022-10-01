"""
Handle checkin command
"""
from gettext import find
import json
import logging
import os
from base64 import b64decode

import boto3
import gspread
from requests import patch
from requests.exceptions import RequestException

# Google SA setup: https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account

logging.getLogger().setLevel(logging.DEBUG)

GOOGLE_API_CREDS = os.environ["GOOGLE_API_CREDS"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
APPLICATION_ID = os.environ["APPLICATION_ID"]
CHECKIN_STATUS_PARAM = os.environ["CHECKIN_STATUS_PARAM"]

COLUMNS = {
    "team": {
        "name": 2,
        "day_1": 6,
        "day_2": 7,
        "day_1_range": "A",
    },
    "solo": {
        "name": 8,
        "day_1": 10,
        "day_1_range": "H",
    },
}
COLORS = {
    "team": {
        "red": 0.414,
        "green": 0.656,
        "blue": 0.309,
    },
    "solo": {
        "red": 0.641,
        "green": 0.756,
        "blue": 0.953,
    },
}
CHECKED_IN_MSG = "Checked In"
CHANNEL_IDS = {
    "935116296587202632": "Division 4",
    "935116039400857620": "Division 3",
    "935116002000240680": "Division 2",
    "935115970945613884": "Division 1",
}
# Test Channel
CHANNEL_IDS["1023401872750547014"] = "Division 4"


def get_checkin_status():
    client = boto3.client("ssm")
    response = client.get_parameter(Name=CHECKIN_STATUS_PARAM)
    logging.debug(response)
    return response["Parameter"]["Value"]


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
    gcreds = json.loads(b64decode(GOOGLE_API_CREDS).decode("utf-8"))
    gc = gspread.service_account_from_dict(gcreds)

    sub_command = event["data"]["options"][0]["name"]
    player_name = event["member"]["nick"]
    if not player_name:
        player_name = event["member"]["user"]["username"]
    channel_id = event["channel_id"]
    if sub_command == "team":
        team_name = event["data"]["options"][0]["options"][0]["value"]

    # TEST SHEET
    if event["guild_id"] == "755422118719520827":
        GOOGLE_SHEET_ID = "1AwWaWBdKxYCSj6LLVZrsfI_zdo0gAqduvng_DkxmeE8"

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
        # if player_name.lower() != name_cell.value.lower():
        #     return f":no_entry: Your nickname isn't `{name_cell.value}`!\nPlease make sure your Discord nickname matches your in game name"
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
        checkin_status = get_checkin_status()
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
        logging.info(response.status_code)
        logging.debug(response.json())

    except RequestException as e:
        logging.error(e)
    except Exception as e:
        logging.error(e)

    return True
