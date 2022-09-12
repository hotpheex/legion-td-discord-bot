"""
Handle checkin command
"""
import json
import os
import logging
from base64 import b64decode

from requests import patch
from requests.exceptions import RequestException
import gspread

logging.getLogger().setLevel(logging.DEBUG)

GOOGLE_API_CREDS = os.environ["GOOGLE_API_CREDS"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
APPLICATION_ID = os.environ["APPLICATION_ID"]

TEAM_COLUMN = 3
SOLO_COLUMN = 8
CHECKED_IN_COLOR = {
    "red": 0.203,
    "green": 0.658,
    "blue": 0.325,
}
CHECKED_IN_MSG = "Checked In"
CHANNEL_IDS = {"1016217034662629537": "Division 4"}
# CHANNEL_IDS = {
#     "935116296587202632": "Division 4",
#     "935116039400857620": "Division 3",
#     "935116002000240680": "Division 2",
#     "935115970945613884": "Division 1",
# }


def checkin(guild_id, body):
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
        raise Exception(f"{sub_command} not a valid command")

    # Find Name Cell
    name_cell = ws.find(query=query_name, case_sensitive=False, in_column=query_column)
    if not name_cell:
        return f":no_entry: `{query_name}` not found in {CHANNEL_IDS[channel_id]}"

    if sub_command == "team":
        if not ws.find(query=player_name, case_sensitive=False, in_row=name_cell.row):
            return f":no_entry: Player `{player_name}` is not on team `{team_name}`"

    if sub_command == "solo":
        if player_name.lower() != name_cell.value.lower():
            return f":no_entry: Your nickname isn't `{name_cell.value}`!"

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

    guild_id = event["guild_id"]

    try:
        if event["channel_id"] not in CHANNEL_IDS:
            message = f":no_entry: `/checkin` not supported in this channel"
        else:
            message = checkin(guild_id, event)

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
