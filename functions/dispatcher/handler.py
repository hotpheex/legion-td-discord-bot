"""
Handles discord command event
Responds with ACK & defer for update
Invoke async function to process command
"""

import json
import os
import traceback
import requests

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from aws_lambda_powertools.utilities.parameters import get_parameter
from aws_lambda_powertools.utilities.typing import LambdaContext
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

logger = Logger()
logger.setLevel("DEBUG")

sqs_client = boto3.client("sqs")

def discord_body(status_code, type, message):
    logger.debug(f"Status: {status_code}")
    logger.info(f"Message: {message}")
    return {
        "headers": {"Content-Type": "application/json"},
        "statusCode": status_code,
        "body": json.dumps({"type": type, "data": {"content": message}}),
    }


def valid_signature(event, discord_public_key):
    body = event["body"]
    auth_sig = event["headers"]["x-signature-ed25519"]
    auth_ts = event["headers"]["x-signature-timestamp"]

    message = auth_ts.encode() + body.encode()

    try:
        verify_key = VerifyKey(bytes.fromhex(discord_public_key))
        verify_key.verify(message, bytes.fromhex(auth_sig))

        return True
    except BadSignatureError as e:
        logger.exception(e)
        return False


def handler(event, context):
    logger.debug(json.dumps(event))

    discord_public_key = os.environ["DISCORD_PUBLIC_KEY"]
    alert_webhook = get_parameter(os.environ["ALERT_WEBHOOK_PARAM"])

    commands = {
        "manage": os.environ["MANAGE_QUEUE_URL"],
    }

    try:
        if not valid_signature(event, discord_public_key):
            return discord_body(200, 2, "Error Validating Discord Signature")
    except KeyError:
        return {"statusCode": 200, "body": ""}

    body = json.loads(event["body"])

    if body["type"] == 1:
        return {"statusCode": 200, "body": json.dumps({"type": 1})}

    if body["type"] == 2:
        command = body["data"]["name"]
        try:

            # Respond to checkin with FAQ page
            if command == "signup":
                return discord_body(
                    200,
                    4,
                    "For signup and other instructions read the FAQ: <https://beta.legiontd2.com/esports/#faq>",
                )

            # Send the event to the appropriate SQS queue
            queue_url = commands.get(command)
            if not queue_url:
                return discord_body(200, 4, f"Unknown command: {command}")
            logger.info(f"Sending message to queue: {queue_url}")
            sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=event["body"],
                MessageAttributes={
                    "command": {
                        "DataType": "String",
                        "StringValue": command,
                    }
                },
            )
            logger.info("Message sent to queue successfully")
            return discord_body(200, 5, "processing")
        except Exception as e:
            logger.exception(e)
            requests.post(
                alert_webhook,
                json={
                    "content": f"`{context.function_name} - {context.log_stream_name}`\n```{traceback.format_exc()}```"
                },
            )
            return discord_body(200, 4, f"Unable to {command}, {e}")
