"""
Handles discord command event
Responds with ACK & defer for update
Invoke async function to process command
"""

import json
import os
import traceback

import boto3
import requests
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.parameters import get_parameter
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

# Initialize Powertools
logger = Logger()
tracer = Tracer()

logger.setLevel("DEBUG")

DISCORD_PUBLIC_KEY = os.environ["DISCORD_PUBLIC_KEY"]
ALERT_WEBHOOK = get_parameter(os.environ["ALERT_WEBHOOK_PARAM"])

# Map command names to their queue URLs
COMMAND_QUEUES = {
    "manage": os.environ["MANAGE_QUEUE_URL"],
    # Add more commands as they are implemented
    # "checkin": os.environ["CHECKIN_QUEUE_URL"],
    # "results": os.environ["RESULTS_QUEUE_URL"],
}

# INTERACTION RESPONSE TYPES
# https://discord.com/developers/docs/interactions/receiving-and-responding#interaction-response-object-interaction-callback-type


def discord_body(status_code, type, message):
    logger.debug(f"Status: {status_code}")
    logger.info(f"Message: {message}")
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
        logger.exception(e)
        return False


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    logger.debug(json.dumps(event))

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
        sqs_client = boto3.client("sqs")

        try:
            # Respond to checkin with FAQ page
            if command == "signup":
                return discord_body(
                    200,
                    4,
                    "For signup and other instructions read the FAQ: <https://beta.legiontd2.com/esports/#faq>",
                )

            # Send message to appropriate queue
            queue_url = COMMAND_QUEUES.get(command)
            if queue_url:
                response = sqs_client.send_message(
                    QueueUrl=queue_url,
                    MessageBody=event["body"],
                )
                logger.debug(f"SQS Response: {response}")
                return discord_body(200, 5, "processing")
            else:
                return discord_body(200, 4, f"Unknown command: {command}")

        except Exception as e:
            logger.exception(e)
            res = requests.post(
                ALERT_WEBHOOK,
                json={
                    "content": f"`{context.function_name} - {context.log_stream_name}`\n```{traceback.format_exc()}```"
                },
            )
            logger.debug(res.status_code)
            return discord_body(200, 4, f"Unable to {command}, {e}")

    return discord_body(400, 4, "Invalid request type")
