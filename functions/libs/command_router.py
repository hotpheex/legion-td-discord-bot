"""
Reusable command router for Discord command handlers
"""

from typing import Dict, Callable, Any, Optional
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent
from aws_lambda_powertools.utilities.typing import LambdaContext


class CommandRouter:
    """
    Reusable router for Discord command handlers that processes EventBridge events
    and routes to appropriate subcommand handlers.
    """
    
    def __init__(
        self,
        command_registry: Dict[str, Callable],
        discord_client: Any,
        logger: Optional[Logger] = None,
        additional_clients: Optional[Dict[str, Any]] = None,
        additional_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the command router.
        
        Args:
            command_registry: Dictionary mapping subcommand names to handler functions
            discord_client: Initialized Discord client instance
            logger: Optional logger instance (creates one if not provided)
            additional_clients: Optional dict of additional clients to pass to handlers
            additional_config: Optional dict of additional config to pass to handlers
        """
        self.command_registry = command_registry
        self.discord_client = discord_client
        self.logger = logger or Logger()
        self.additional_clients = additional_clients or {}
        self.additional_config = additional_config or {}
    
    def handle_event(self, event: dict, context: LambdaContext) -> str:
        """
        Handle an EventBridge event for Discord commands.
        
        Args:
            event: EventBridge event dict
            context: Lambda context
            
        Returns:
            Response message string
        """
        # Parse EventBridge event using Powertools
        eventbridge_event = EventBridgeEvent(event)
        self.logger.debug(f"Received EventBridge event: {eventbridge_event}")
        
        # Validate event structure
        if eventbridge_event.detail_type != "DiscordCommand":
            self.logger.warning(f"Unexpected detail_type: {eventbridge_event.detail_type}")
            return "Invalid event type"
        
        # Extract Discord event from EventBridge detail
        try:
            discord_event_detail = eventbridge_event.detail
            command = discord_event_detail.get("command")
            discord_event = discord_event_detail.get("discord_event", {})
            
            if not command or not discord_event:
                self.logger.error("Missing command or discord_event in EventBridge detail")
                return "Invalid event structure"
                
        except (KeyError, TypeError) as e:
            self.logger.error(f"Failed to parse EventBridge detail: {e}")
            return "Invalid event format"
        
        # Validate Discord token
        token = discord_event.get('token')
        if not token:
            self.logger.error("Missing Discord token in event")
            return "Missing Discord token"

        try:
            # Extract subcommand from Discord event
            discord_data = discord_event.get("data", {})
            options = discord_data.get("options", [])
            
            if not options:
                raise Exception("No command options found")
                
            sub_command = options[0].get("name")
            if not sub_command:
                raise Exception("No subcommand name found")
            
            # Get handler from registry
            handler_fn = self.command_registry.get(sub_command)
            if not handler_fn:
                raise Exception(f"{sub_command} is not a valid command")
            
            # Prepare arguments for the handler
            handler_kwargs = {
                "discord": self.discord_client,
                "logger": self.logger,
                "context": context,
                **self.additional_clients,
                **self.additional_config,
            }
            
            # Call the subcommand handler
            message = handler_fn(discord_event, **handler_kwargs)
            
            # Send response to Discord
            self.discord_client.message_response(message)
            self.logger.info(f"Successfully processed command: {sub_command}")
            return message
            
        except Exception as e:
            self.logger.exception(f"Error processing command: {e}")
            # Send error response to Discord
            self.discord_client.message_response(":warning: Command failed unexpectedly")
            return ":warning: Command failed unexpectedly" 