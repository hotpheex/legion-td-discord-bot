import json
import os
import logging
from re import sub

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import gspread

DISCORD_PUBLIC_KEY = os.environ["DISCORD_PUBLIC_KEY"]
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


# INTERACTION RESPONSE TYPES
# NAME	VALUE	DESCRIPTION
# Pong	1	ACK a Ping
# Acknowledge	2	ACK a command without sending a message, eating the user's input
# ChannelMessage	3	respond with a message, eating the user's input
# ChannelMessageWithSource	4	respond with a message, showing the user's input
# AcknowledgeWithSource	5	ACK a command without sending a message, showing the user's input


def checkin(guild_id, body):
    team_name = body["data"]["options"][0]["value"]
    player_name = body["member"]["nick"]
    if not player_name:
        player_name = body["member"]["user"]["username"]
    channel_id = body["channel_id"]

    gc = gspread.service_account(filename="svc_account.json")
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.worksheet(CHANNEL_IDS[channel_id])

    # Find Team
    team_cell = ws.find(query=team_name, in_column=TEAM_COLUMN)

    if not team_cell:
        return f"Team '{team_name}' not found in {CHANNEL_IDS[channel_id]}"

    if not ws.find(query=player_name, in_row=team_cell.row):
        return f"Player '{player_name}' is not on team '{team_name}'"

    status_cell = ws.cell(team_cell.row, team_cell.col - 1)

    if status_cell.value == CHECKED_IN_MSG:
        return f"Team '{team_name}' is already checked in"

    # Mark team as checked in
    ws.update_cell(team_cell.row, team_cell.col - 1, CHECKED_IN_MSG)
    ws.format(
        f"{status_cell.address}:{team_cell.address}",
        {"backgroundColor": CHECKED_IN_COLOR},
    )

    return f"Team '{team_name}' checked in! :white_check_mark:"


commands = {"checkin": checkin}


def discord_body(status_code, type, message):
    print("STATUS", status_code, "MSG", message)
    return {
        "statusCode": status_code,
        "body": json.dumps({"type": type, "data": {"tts": False, "content": message}}),
    }


def valid_signature(event):
    body = event["body"]
    auth_sig = event["headers"]["x-signature-ed25519"]
    auth_ts = event["headers"]["x-signature-timestamp"]

    message = auth_ts.encode() + body.encode()

    try:
        verify_key = VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))
        verify_key.verify(message, bytes.fromhex(auth_sig))

        return True
    except BadSignatureError as e:
        print(e)
        return False


def lambda_handler(event, context):
    print(json.dumps(event))
    if not valid_signature(event):
        return discord_body(200, 2, "Error Validating Discord Signature")

    body = json.loads(event["body"])

    if body["type"] == 1:
        return DISCORD_PING_PONG

    guild_id = body["guild_id"]
    command = body["data"]["name"]
    # sub_command = body["data"]["options"][0]["name"]

    try:
        bot_func = commands.get(command)
        message = bot_func(guild_id, body)
        return discord_body(200, 4, message)
    except Exception as e:
        return discord_body(200, 4, f"Unable to {command}, {e}")
