"""
Handle checkin command
"""
import json
import os
import logging
from re import sub
from base64 import b64decode

from requests import patch
from requests.exceptions import RequestException
import gspread

logging.getLogger().setLevel(logging.DEBUG)

GOOGLE_API_CREDS = os.environ["GOOGLE_API_CREDS"]
APPLICATION_ID = os.environ["APPLICATION_ID"]
DISCORD_PING_PONG = {"statusCode": 200, "body": json.dumps({"type": 1})}

TEAM_COLUMN = 3
CHECKED_IN_COLOR = {
    "red": 0.203,
    "green": 0.658,
    "blue": 0.325,
}
CHECKED_IN_MSG = "Checked In"
CHANNEL_IDS = {"1016217034662629537": "Division 4"}
SHEET_ID = "1AwWaWBdKxYCSj6LLVZrsfI_zdo0gAqduvng_DkxmeE8"


def checkin(guild_id, body):
    # Drop creds file on fs
    with open("/tmp/google_creds.json", "w") as fh:
        fh.write(b64decode(GOOGLE_API_CREDS).decode("utf-8"))

    team_name = body["data"]["options"][0]["value"]
    player_name = body["member"]["nick"]
    if not player_name:
        player_name = body["member"]["user"]["username"]
    channel_id = body["channel_id"]

    try:
        gc = gspread.service_account(filename="/tmp/google_creds.json")
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.worksheet(CHANNEL_IDS[channel_id])

        # Find Team
        team_cell = ws.find(query=team_name, in_column=TEAM_COLUMN)

        if not team_cell:
            return f"Team `{team_name}` not found in {CHANNEL_IDS[channel_id]}"

        if not ws.find(query=player_name, in_row=team_cell.row):
            return f"Player `{player_name}` is not on team `{team_name}`"

        status_cell = ws.cell(team_cell.row, team_cell.col - 1)

        if status_cell.value == CHECKED_IN_MSG:
            return f"Team `{team_name}` is already checked in"
    except Exception as e:
        logging.error(e)

    # Mark team as checked in
    ws.update_cell(team_cell.row, team_cell.col - 1, CHECKED_IN_MSG)
    ws.format(
        f"{status_cell.address}:{team_cell.address}",
        {"backgroundColor": CHECKED_IN_COLOR},
    )

    return f"Team `{team_name}` checked in! :white_check_mark:"


def lambda_handler(event, context):
    logging.debug(json.dumps(event))

    guild_id = event["guild_id"]

    try:
        message = checkin(guild_id, event)
        logging.info(message)

        response = patch(
            f"https://discord.com/api/webhooks/{APPLICATION_ID}/{event['token']}/messages/@original",
            json={"content": message},
        )
        logging.debug(response.status_code)
        logging.debug(response.json())

    except RequestException as e:
        logging.error(e)
    except Exception as e:
        logging.error(e)
