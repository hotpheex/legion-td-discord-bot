"""
Admin commands to manage tournaments
"""

import os
import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from libs.command_router import CommandRouter
from libs.ssm_cache import get_ssm_param
from libs.challonge import Challonge
from libs.discord import Discord
from libs.gsheets import GoogleSheet
from libs.constants import SIGNUP_SHEET
from commands import COMMAND_REGISTRY

# Initialize logger
logger = Logger()
logger.setLevel("DEBUG")

# Read environment variables at import time
CHECKIN_STATUS_PARAM = os.environ["CHECKIN_STATUS_PARAM"]
APPLICATION_ID = os.environ["APPLICATION_ID"]
ALERT_WEBHOOK_PARAM = os.environ["ALERT_WEBHOOK_PARAM"]
CHALLONGE_API_KEY_PARAM = os.environ["CHALLONGE_API_KEY_PARAM"]
GOOGLE_API_KEY_PARAM = os.environ["GOOGLE_API_KEY_PARAM"]
GOOGLE_SHEET_ID_PARAM = os.environ["GOOGLE_SHEET_ID_PARAM"]


def handler(event: dict, context: LambdaContext) -> str:
    """Handle EventBridge events for Discord manage commands"""
    
    # Extract Discord token from event for Discord client initialization
    try:
        from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent
        eventbridge_event = EventBridgeEvent(event)
        discord_event_detail = eventbridge_event.detail
        discord_event = discord_event_detail.get("discord_event", {})
        token = discord_event.get('token')
        
        if not token:
            logger.error("Missing Discord token in event")
            return "Missing Discord token"
            
    except Exception as e:
        logger.error(f"Failed to extract Discord token: {e}")
        return "Invalid event format"
    
    # Initialize shared clients/utilities
    client = boto3.client("ssm")
    challonge = Challonge(get_ssm_param(CHALLONGE_API_KEY_PARAM))
    gsheet = GoogleSheet(
        get_ssm_param(GOOGLE_API_KEY_PARAM), 
        get_ssm_param(GOOGLE_SHEET_ID_PARAM), 
        SIGNUP_SHEET
    )
    discord = Discord(APPLICATION_ID, token)
    alert_webhook = get_ssm_param(ALERT_WEBHOOK_PARAM)
    
    # Initialize the command router with finalized clients
    router = CommandRouter(
        command_registry=COMMAND_REGISTRY,
        discord_client=discord,
        logger=logger,
        additional_clients={
            "client": client,
            "gsheet": gsheet,
            "challonge": challonge,
        },
        additional_config={
            "CHECKIN_STATUS_PARAM": CHECKIN_STATUS_PARAM,
            "APPLICATION_ID": APPLICATION_ID,
            "ALERT_WEBHOOK": alert_webhook,
        }
    )
    
    return router.handle_event(event, context)
