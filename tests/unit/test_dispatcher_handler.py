import os
import json
import pytest
from unittest.mock import patch
from moto import mock_aws
import boto3

# Set up environment variables before importing the handler
os.environ["DISCORD_PUBLIC_KEY"] = "test_public_key"
os.environ["ALERT_WEBHOOK_PARAM"] = "/test/alert_webhook"
os.environ["COMMAND_BUS_NAME"] = "test-command-bus"

from functions.dispatcher import handler as dispatcher_handler

# Real Discord interaction payload from the logs
REAL_DISCORD_PAYLOAD = {
    "app_permissions": "562949953863680",
    "application_id": "1058247991867219990",
    "attachment_size_limit": 52428800,
    "authorizing_integration_owners": {"0": "755422118719520827"},
    "channel": {
        "flags": 0,
        "guild_id": "755422118719520827",
        "id": "1023401872750547014",
        "last_message_id": "1386616115584831588",
        "name": "legion-td-bot-test",
        "nsfw": False,
        "parent_id": "755439851087724655",
        "permissions": "2251799813685247",
        "position": 3,
        "rate_limit_per_user": 0,
        "topic": None,
        "type": 0,
    },
    "channel_id": "1023401872750547014",
    "context": 0,
    "data": {
        "id": "1058279054920388630",
        "name": "manage",
        "options": [
            {
                "name": "checkin_enabled",
                "options": [{"name": "enabled", "type": 3, "value": "day_1"}],
                "type": 1,
            }
        ],
        "type": 1,
    },
    "entitlement_sku_ids": [],
    "entitlements": [],
    "guild": {
        "features": ["TIERLESS_BOOSTING_SYSTEM_MESSAGE", "ENABLED_MODERATION_EXPERIENCE_FOR_NON_COMMUNITY"],
        "id": "755422118719520827",
        "locale": "en-US",
    },
    "guild_id": "755422118719520827",
    "guild_locale": "en-US",
    "id": "1386694254218444920",
    "locale": "en-US",
    "member": {
        "avatar": None,
        "banner": None,
        "communication_disabled_until": None,
        "deaf": False,
        "flags": 0,
        "joined_at": "2020-09-15T13:37:48.210000+00:00",
        "mute": False,
        "nick": None,
        "pending": False,
        "permissions": "2251799813685247",
        "premium_since": None,
        "roles": [],
        "unusual_dm_activity_until": None,
        "user": {
            "avatar": "39bc9bd8f57cd0bfaa50b8e16491acee",
            "avatar_decoration_data": None,
            "clan": None,
            "collectibles": None,
            "discriminator": "0",
            "global_name": "htphx",
            "id": "164975439356362752",
            "primary_guild": None,
            "public_flags": 4194304,
            "username": "hotpheex",
        },
    },
    "token": "aW50ZXJhY3Rpb246MTM4NjY5NDI1NDIxODQ0NDkyMDpYbndsYVgxWktWUnEyUUdjc3Rucjd0WFJXUmNadkpxY1hZTjJRMDliZkVic0VtTWViWGl6QjdWYk9DTkdzWGVNeEtQbnBPdFZndDM4dUtiM01xRFM5OGQwQ1pIVW4zWlNMRkROUElxVktWZ0tMaUt0dFpOdXhWYmdyS0xLWDZ0Rg",
    "type": 2,
    "version": 1,
}

# Real API Gateway event structure
REAL_API_GATEWAY_EVENT = {
    "version": "2.0",
    "routeKey": "POST /interactions",
    "rawPath": "/interactions",
    "rawQueryString": "",
    "headers": {
        "content-length": "1740",
        "content-type": "application/json",
        "host": "3kum34kunb.execute-api.us-east-1.amazonaws.com",
        "user-agent": "Discord-Interactions/1.0 (+https://discord.com)",
        "x-amzn-trace-id": "Root=1-685951a9-36981ffd1a8fbc1f19b2852b",
        "x-forwarded-for": "35.237.4.214",
        "x-forwarded-port": "443",
        "x-forwarded-proto": "https",
        "x-signature-ed25519": "43a3572b91a10a0649ab6881cc3b4ee233a5d8e5bf330b8513b273ab34c15d8601c42046af7bde645111ca6be33967f9d0ff2d4ca17b51bcd7c3a1e12862bc00",
        "x-signature-timestamp": "1750684073",
    },
    "requestContext": {
        "accountId": "481093024398",
        "apiId": "3kum34kunb",
        "domainName": "3kum34kunb.execute-api.us-east-1.amazonaws.com",
        "domainPrefix": "3kum34kunb",
        "http": {
            "method": "POST",
            "path": "/interactions",
            "protocol": "HTTP/1.1",
            "sourceIp": "35.237.4.214",
            "userAgent": "Discord-Interactions/1.0 (+https://discord.com)",
        },
        "requestId": "MnmymiafIAMEYog=",
        "routeKey": "POST /interactions",
        "stage": "$default",
        "time": "23/Jun/2025:13:07:53 +0000",
        "timeEpoch": 1750684073860,
    },
    "body": json.dumps(REAL_DISCORD_PAYLOAD),
    "isBase64Encoded": False,
}

def create_api_gateway_event(discord_payload, signature="test_sig", timestamp="1234567890"):
    """Create a realistic API Gateway event with Discord interaction"""
    return {
        "version": "2.0",
        "routeKey": "POST /interactions",
        "rawPath": "/interactions",
        "rawQueryString": "",
        "headers": {
            "content-type": "application/json",
            "x-signature-ed25519": signature,
            "x-signature-timestamp": timestamp,
        },
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "test-api",
            "domainName": "test-api.execute-api.us-east-1.amazonaws.com",
            "domainPrefix": "test-api",
            "http": {
                "method": "POST",
                "path": "/interactions",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "Discord-Interactions/1.0 (+https://discord.com)",
            },
            "requestId": "test-request-id",
            "routeKey": "POST /interactions",
            "stage": "$default",
            "time": "23/Jun/2025:13:07:53 +0000",
            "timeEpoch": 1750684073860,
        },
        "body": json.dumps(discord_payload),
        "isBase64Encoded": False,
    }

@pytest.fixture(autouse=True)
def setup_ssm():
    with mock_aws():
        ssm = boto3.client("ssm", region_name="us-east-1")
        ssm.put_parameter(Name="/test/alert_webhook", Value="https://discord.com/api/webhooks/test", Type="String")
        yield

@pytest.fixture
def mock_services():
    with patch("functions.dispatcher.handler.get_parameter") as mock_get_param, \
         patch("functions.dispatcher.handler.requests.post") as mock_requests, \
         patch("functions.dispatcher.handler.eventbridge_client") as mock_eventbridge:
        mock_get_param.return_value = "https://discord.com/api/webhooks/test"
        yield mock_get_param, mock_requests, mock_eventbridge

@pytest.fixture
def mock_signature():
    with patch("functions.dispatcher.handler.valid_signature") as mock_sig:
        mock_sig.return_value = True
        yield mock_sig

def test_ping_event(mock_services, mock_signature):
    """Test handling of Discord ping events (type 1)"""
    mock_get_param, mock_requests, mock_eventbridge = mock_services
    
    ping_payload = {"type": 1}
    event = create_api_gateway_event(ping_payload)
    
    response = dispatcher_handler.handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["type"] == 1
    assert "data" not in body

def test_signup_command(mock_services, mock_signature):
    """Test handling of signup command"""
    mock_get_param, mock_requests, mock_eventbridge = mock_services
    
    signup_payload = {
        "type": 2,
        "data": {"name": "signup"},
        "token": "test_token"
    }
    event = create_api_gateway_event(signup_payload)
    
    response = dispatcher_handler.handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["type"] == 4
    assert "FAQ" in body["data"]["content"]

def test_manage_command(mock_services, mock_signature):
    """Test handling of manage command - should defer response"""
    mock_get_param, mock_requests, mock_eventbridge = mock_services
    mock_eventbridge.put_events.return_value = {"FailedEntryCount": 0, "Entries": [{"EventId": "test-id"}]}
    
    # Use the real payload structure
    event = create_api_gateway_event(REAL_DISCORD_PAYLOAD)
    
    response = dispatcher_handler.handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["type"] == 5  # Deferred response
    
    # Verify EventBridge was called
    mock_eventbridge.put_events.assert_called_once()
    call_args = mock_eventbridge.put_events.call_args[1]["Entries"][0]
    assert call_args["Source"] == "legion-td.discord"
    assert call_args["DetailType"] == "DiscordCommand"
    
    # Verify the detail contains the command
    detail = json.loads(call_args["Detail"])
    assert detail["command"] == "manage"

def test_invalid_signature(mock_services):
    """Test handling when Discord signature is invalid"""
    mock_get_param, mock_requests, mock_eventbridge = mock_services
    
    with patch("functions.dispatcher.handler.valid_signature") as mock_sig:
        mock_sig.return_value = False
        
        event = create_api_gateway_event(REAL_DISCORD_PAYLOAD)
        response = dispatcher_handler.handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["type"] == 2
        assert "Error Validating" in body["data"]["content"]

def test_missing_body(mock_services, mock_signature):
    """Test handling when request body is missing"""
    mock_get_param, mock_requests, mock_eventbridge = mock_services
    
    event = create_api_gateway_event(REAL_DISCORD_PAYLOAD)
    event["body"] = None
    
    response = dispatcher_handler.handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["type"] == 4
    assert "Invalid Discord command payload" in body["data"]["content"]

def test_eventbridge_failure(mock_services, mock_signature):
    """Test handling when EventBridge put_events fails"""
    mock_get_param, mock_requests, mock_eventbridge = mock_services
    mock_eventbridge.put_events.side_effect = Exception("EventBridge error")
    
    event = create_api_gateway_event(REAL_DISCORD_PAYLOAD)
    
    response = dispatcher_handler.handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["type"] == 4
    assert "Unable to manage" in body["data"]["content"]
    
    # Verify alert webhook was called
    assert mock_requests.called

def test_unknown_event_type(mock_services, mock_signature):
    """Test handling of unknown event types"""
    mock_get_param, mock_requests, mock_eventbridge = mock_services
    
    unknown_payload = {"type": 999, "data": {}, "token": "test"}
    event = create_api_gateway_event(unknown_payload)
    
    response = dispatcher_handler.handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["type"] == 4
    assert "Unknown Discord event type" in body["data"]["content"]

def test_real_payload_structure(mock_services, mock_signature):
    """Test with the exact real payload structure from the logs"""
    mock_get_param, mock_requests, mock_eventbridge = mock_services
    mock_eventbridge.put_events.return_value = {"FailedEntryCount": 0, "Entries": [{"EventId": "test-id"}]}
    
    response = dispatcher_handler.handler(REAL_API_GATEWAY_EVENT, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["type"] == 5  # Deferred response
    
    # Verify the command was extracted correctly
    mock_eventbridge.put_events.assert_called_once()
    call_args = mock_eventbridge.put_events.call_args[1]["Entries"][0]
    detail = json.loads(call_args["Detail"])
    assert detail["command"] == "manage" 