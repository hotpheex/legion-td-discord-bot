import json
import os
import logging
from re import sub

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

DISCORD_PUBLIC_KEY = os.environ["DISCORD_PUBLIC_KEY"]
DISCORD_PING_PONG = {"statusCode": 200, "body": json.dumps({"type": 1})}

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
    return f"{team_name} Checked In! :white_check_mark:"


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
