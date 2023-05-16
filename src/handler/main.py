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

global DISCORD_PUBLIC_KEY
global ALERT_WEBHOOK


# INTERACTION RESPONSE TYPES
# https://discord.com/developers/docs/interactions/receiving-and-responding#interaction-response-object-interaction-callback-type


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


def lambda_handler(event, context):
    logging.debug(json.dumps(event))

    commands = {
        "checkin": os.environ["LAMBDA_CHECKIN"],
        "manage": os.environ["LAMBDA_MANAGE"],
        "results": os.environ["LAMBDA_RESULTS"],
    }

    DISCORD_PUBLIC_KEY = os.environ["DISCORD_PUBLIC_KEY"]
    ALERT_WEBHOOK = os.environ["ALERT_WEBHOOK"]

    try:
        if not valid_signature(event):
            return discord_body(200, 2, "Error Validating Discord Signature")
    except KeyError:
        return {"statusCode": 200, "body": ""}

    body = json.loads(event["body"])

    if body["type"] == 1:
        return {"statusCode": 200, "body": json.dumps({"type": 1})}

    if body["type"] == 2:
        command = body["data"]["name"]

    client = boto3.client("lambda")
    discord = Discord(None, None)

    try:
        # Respond to checkin with FAQ page
        if command == "signup":
            return discord_body(
                200,
                4,
                "For signup and other instructions read the FAQ: <https://beta.legiontd2.com/esports/#faq>",
            )

        # Invoke the appropriate lambda
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
