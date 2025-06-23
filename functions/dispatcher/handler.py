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
from pydantic import BaseModel, ValidationError
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

logger = Logger()
logger.setLevel("DEBUG")

eventbridge_client = boto3.client("events")

class DiscordCommand(BaseModel):
    type: int
    data: dict
    token: str

# Helper for Discord response

def discord_body(status_code, type, message):
    logger.debug(f"Status: {status_code}")
    logger.info(f"Message: {message}")
    return {
        "headers": {"Content-Type": "application/json"},
        "statusCode": status_code,
        "body": json.dumps({"type": type, "data": {"content": message}}),
    }

def valid_signature(event, discord_public_key):
    body = event.body
    auth_sig = event.headers["x-signature-ed25519"]
    auth_ts = event.headers["x-signature-timestamp"]
    message = auth_ts.encode() + body.encode()
    try:
        verify_key = VerifyKey(bytes.fromhex(discord_public_key))
        verify_key.verify(message, bytes.fromhex(auth_sig))
        return True
    except BadSignatureError as e:
        logger.exception(e)
        return False

def handler(event, context):
    api_event = APIGatewayProxyEvent(event)
    logger.debug(json.dumps(event))
    discord_public_key = os.environ["DISCORD_PUBLIC_KEY"]
    alert_webhook = get_parameter(os.environ["ALERT_WEBHOOK_PARAM"])
    command_bus_name = os.environ["COMMAND_BUS_NAME"]

    # Validate signature
    try:
        if not valid_signature(api_event, discord_public_key):
            return discord_body(200, 2, "Error Validating Discord Signature")
    except KeyError:
        return {"statusCode": 200, "body": ""}

    # Parse Discord command using Pydantic
    try:
        if not api_event.body:
            raise ValueError("Missing request body")
        discord_body_json = json.loads(api_event.body)
        discord_event = DiscordCommand.parse_obj(discord_body_json)
    except (ValidationError, Exception) as e:
        logger.exception(e)
        return discord_body(400, 4, "Invalid Discord command payload")

    # Ping event
    if discord_event.type == 1:
        return {"statusCode": 200, "body": json.dumps({"type": 1})}

    # Application command event
    if discord_event.type == 2:
        command = discord_event.data.get("name")
        try:
            if command == "signup":
                return discord_body(
                    200,
                    4,
                    "For signup and other instructions read the FAQ: <https://beta.legiontd2.com/esports/#faq>",
                )
            # Send the event to EventBridge
            logger.info(f"Sending event to EventBridge bus: {command_bus_name}")
            response = eventbridge_client.put_events(
                Entries=[
                    {
                        "Source": "legion-td.discord",
                        "DetailType": "DiscordCommand",
                        "Detail": json.dumps({
                            "command": command,
                            "discord_event": discord_event.dict()
                        }),
                        "EventBusName": command_bus_name,
                    }
                ]
            )
            logger.info(f"EventBridge put_events response: {response}")
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
    # Unknown event type
    return discord_body(400, 4, "Unknown Discord event type")
