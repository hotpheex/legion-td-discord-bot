from typing import List, Optional

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lamb
from aws_cdk import aws_ssm as ssm
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from constructs import Construct
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets

from .command_handler import CommandHandler
from .libs.constants import *


class LegionTdDiscordBotStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Context
        env = self.node.try_get_context("env") or "dev"
        self.application_id = self.node.try_get_context(env)["applicationId"]
        self.discord_public_key = self.node.try_get_context(env)["discordPublicKey"]

        self.insights_arn = self.node.try_get_context("layerInsights")
        self.powertools_arn = self.node.try_get_context("layerPowertools")

        # Create SSM Parameters
        self.param_alert_webhook = self.create_ssm_parameter(
            "alert_webhook", "Discord Webhook URL for alerts"
        )
        self.param_checkin_status = self.create_ssm_parameter(
            "checkin_status", "Checkin status for the tournament"
        )
        self.param_challonge_api_key = self.create_ssm_parameter(
            "challonge_api_key", "Challonge API key"
        )
        self.param_google_api_key = self.create_ssm_parameter(
            "google_api_key", "Google API key"
        )
        self.param_google_sheet_id = self.create_ssm_parameter(
            "google_sheet_id", "Google Sheet ID"
        )

        # Create Lambda Layers
        self.lambda_layers = self.create_lambda_layers()

        # Create EventBridge Bus
        self.command_bus = events.EventBus(self, "DiscordCommandBus")

        # Create Command Handlers and Functions
        self.create_command_handlers()

        # Create Dispatcher Lambda
        self.dispatcher_lambda = self.create_dispatcher_lambda([
            self.param_alert_webhook
        ])

        # Grant Dispatcher permission to put events on the bus
        self.command_bus.grant_put_events_to(self.dispatcher_lambda)

        # Create HTTP API
        self.http_api = self.create_http_api()

    def create_lambda_layers(self):
        # Insights Lambda Layer
        layer_insights = lamb.LayerVersion.from_layer_version_arn(
            self, "InsightsLayer", self.insights_arn
        )

        # Powertools Lambda Layer
        layer_powertools = lamb.LayerVersion.from_layer_version_arn(
            self, "PowertoolsLayer", self.powertools_arn
        )

        # Libs Lambda Layer
        libs_layer = PythonLayerVersion(
            self,
            "LibsLayer",
            entry="functions/libs",
            compatible_runtimes=[LAMBDA_RUNTIME],
            bundling={
                "command": [
                    "bash",
                    "-c",
                    "mkdir -p /asset-output/python/libs && cp *.py /asset-output/python/libs/",
                ]
            },
        )

        return [layer_insights, layer_powertools, libs_layer]

    def create_command_handlers(self):
        self.manage_command = CommandHandler(
            self,
            "ManageCommand",
            command_name="manage",
            layers=self.lambda_layers,
            ssm_parameters=[
                self.param_alert_webhook,
                self.param_checkin_status,
                self.param_challonge_api_key,
                self.param_google_api_key,
                self.param_google_sheet_id,
            ],
            environment={
                "APPLICATION_ID": self.application_id,
            },
            additional_policies=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["ssm:PutParameter"],
                    resources=[
                        self.param_checkin_status.parameter_arn,
                    ],
                )
            ],
        )
        # EventBridge rule for manage command
        events.Rule(
            self,
            "ManageCommandRule",
            event_bus=self.command_bus,
            event_pattern=events.EventPattern(
                detail={"command": ["manage"]}
            ),
            targets=[targets.LambdaFunction(self.manage_command.lambda_function)],
        )

    def create_dispatcher_lambda(self, ssm_parameters: List[ssm.StringParameter]):
        dispatcher = lamb.Function(
            self,
            "DispatcherLambda",
            runtime=LAMBDA_RUNTIME,
            handler="handler.handler",
            code=lamb.Code.from_asset(str(BUILD_DIR / "dispatcher")),
            environment={
                "DISCORD_PUBLIC_KEY": self.discord_public_key,
                "APPLICATION_ID": self.application_id,
                "ALERT_WEBHOOK_PARAM": self.param_alert_webhook.parameter_name,
                "COMMAND_BUS_NAME": self.command_bus.event_bus_name,
            },
            timeout=LAMBDA_TIMEOUT,
            layers=self.lambda_layers,
        )
        for param in ssm_parameters:
            param.grant_read(dispatcher)
        return dispatcher

    def create_http_api(self):
        # HTTP API Gateway
        http_api = apigwv2.HttpApi(self, f"{self.stack_name}API")

        # Add POST route for Discord interactions
        http_api.add_routes(
            path="/interactions",
            methods=[apigwv2.HttpMethod.POST],
            integration=integrations.HttpLambdaIntegration(
                "DispatchIntegration",
                lamb.Function.from_function_attributes(
                    self,
                    "DispatcherRef",
                    function_arn=self.dispatcher_lambda.function_arn,
                    same_environment=True,
                ),
            ),
        )

        # Export the API Gateway URL
        CfnOutput(
            self,
            "ApiGatewayUrl",
            value=http_api.url or "",
            description="The URL of the Discord API Gateway endpoint",
            export_name="DiscordApiGatewayUrl",
        )

    def create_ssm_parameter(self, name: str, description: str) -> ssm.StringParameter:
        """Create a new SSM parameter without setting its value."""

        prefix = "/legion-td-discord-bot"
        param = ssm.StringParameter(
            self,
            name.replace("/", ""),
            parameter_name=f"{prefix}/{name}",
            description=description,
            string_value="PLACEHOLDER",
        )

        return param

    def grant_lambda_permissions(self, lambdas: list):
        pass  # No SQS permissions needed
