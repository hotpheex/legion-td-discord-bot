"""
Handles discord command event
Responds with ACK & defer for update
Invoke async function to process command
"""
import json
import os
import logging
from re import sub
from base64 import b64decode

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import boto3
import botocore.exceptions

logging.getLogger().setLevel(logging.INFO)

DISCORD_PUBLIC_KEY = os.environ["DISCORD_PUBLIC_KEY"]
DISCORD_PING_PONG = {"statusCode": 200, "body": json.dumps({"type": 1})}

LAMBDA_CHECKIN = os.environ["LAMBDA_CHECKIN"]
LAMBDA_MANAGE = os.environ["LAMBDA_MANAGE"]

# INTERACTION RESPONSE TYPES
# https://discord.com/developers/docs/interactions/receiving-and-responding#interaction-response-object-interaction-callback-type


commands = {"checkin": LAMBDA_CHECKIN, "manage": LAMBDA_MANAGE}


def discord_body(status_code, type, message):
    logging.debug(f"Status: {status_code}")
    logging.debug(f"Message: {message}")
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
        logging.error(e)
        return False


def lambda_handler(event, context):
    logging.debug(json.dumps(event))
    if not valid_signature(event):
        return discord_body(200, 2, "Error Validating Discord Signature")

    body = json.loads(event["body"])

    if body["type"] == 1:
        return DISCORD_PING_PONG

    command = body["data"]["name"]
    # sub_command = body["data"]["options"][0]["name"]

    client = boto3.client("lambda")

    try:
        command_func = commands.get(command)
        response = client.invoke(
            FunctionName=command_func,
            InvocationType="Event",
            Payload=event["body"],
        )
        logging.debug(response["StatusCode"])
        return discord_body(200, 5, "processing")
    except botocore.exceptions.ClientError as e:
        logging.error(e)
        return discord_body(200, 4, f"Unable to {command}, {e}")
    except Exception as e:
        logging.error(e)
        return discord_body(200, 4, f"Unable to {command}, {e}")
