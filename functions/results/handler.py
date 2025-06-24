"""
Results commands for tournament participants
"""

import os
import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from libs.command_router import CommandRouter
from libs.ssm_cache import get_ssm_param
from libs.discord import Discord
from libs.challonge import Challonge
from libs.constants import RESULTS_CHANNEL_IDS
from commands import COMMAND_REGISTRY

# Initialize logger
logger = Logger()
logger.setLevel("DEBUG")

# Read environment variables at import time
APPLICATION_ID = os.environ["APPLICATION_ID"]
ALERT_WEBHOOK_PARAM = os.environ["ALERT_WEBHOOK_PARAM"]
CHALLONGE_API_KEY_PARAM = os.environ["CHALLONGE_API_KEY_PARAM"]


def handler(event: dict, context: LambdaContext) -> str:
    """Handle EventBridge events for Discord results commands"""
    
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
    challonge = Challonge(get_ssm_param(CHALLONGE_API_KEY_PARAM))
    discord = Discord(APPLICATION_ID, token)
    alert_webhook = get_ssm_param(ALERT_WEBHOOK_PARAM)
    
    # Initialize the command router with finalized clients
    router = CommandRouter(
        command_registry=COMMAND_REGISTRY,
        discord_client=discord,
        logger=logger,
        additional_clients={
            "challonge": challonge,
        },
        additional_config={
            "APPLICATION_ID": APPLICATION_ID,
            "ALERT_WEBHOOK": alert_webhook,
        }
    )
    
    return router.handle_event(event, context) 