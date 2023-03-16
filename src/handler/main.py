"""
Handles discord command event
Responds with ACK & defer for update
Invoke async function to process command
"""
import json
import logging
import os

import boto3

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from libs.discord import Discord

if os.getenv("DEBUG") == "true":
    logging.getLogger().setLevel(logging.DEBUG)
else:
    logging.getLogger().setLevel(logging.INFO)

DISCORD_PUBLIC_KEY = os.environ["DISCORD_PUBLIC_KEY"]
DISCORD_PING_PONG = {"statusCode": 200, "body": json.dumps({"type": 1})}

ALERT_WEBHOOK = os.environ["ALERT_WEBHOOK"]

# INTERACTION RESPONSE TYPES
# https://discord.com/developers/docs/interactions/receiving-and-responding#interaction-response-object-interaction-callback-type

commands = {
    "checkin": os.environ["LAMBDA_CHECKIN"],
    "manage": os.environ["LAMBDA_MANAGE"],
    "results": os.environ["LAMBDA_RESULTS"],
}


def discord_body(status_code, type, message):
    logging.debug(f"Status: {status_code}")
    logging.info(f"Message: {message}")
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
        logging.exception(e)
        return False


def run(event, context):
    logging.debug(json.dumps(event))
    if not valid_signature(event):
        return discord_body(200, 2, "Error Validating Discord Signature")

    body = json.loads(event["body"])

    if body["type"] == 1:
        return DISCORD_PING_PONG

    if body["type"] == 2:
        command = body["data"]["name"]

    client = boto3.client("lambda")
    discord = Discord(None, None)

    try:
        command_func = commands.get(command)
        response = client.invoke(
            FunctionName=command_func,
            InvocationType="Event",
            Payload=event["body"],
        )
        logging.debug(response["StatusCode"])
        return discord_body(200, 5, "processing")
    except Exception as e:
        logging.exception(e)
        discord.exception_alert(ALERT_WEBHOOK, context)
        return discord_body(200, 4, f"Unable to {command}, {e}")
