import pytest
import aws_cdk as cdk
from infra.stack import LegionTdDiscordBotStack

def test_cdk_stack_creation():
    app = cdk.App()
    # Set required context for the stack
    app.node.set_context("dev", {"applicationId": "dummy_app_id", "discordPublicKey": "dummy_key"})
    app.node.set_context("layerInsights", "dummy_layer_insights")
    app.node.set_context("layerPowertools", "dummy_layer_powertools")
    stack = LegionTdDiscordBotStack(app, "TestStack")
    # Synthesize the stack to ensure it can be created
    template = app.synth().get_stack_by_name("TestStack").template
    # Basic sanity check: stack should contain at least one resource
    assert "Resources" in template
    assert len(template["Resources"]) > 0
