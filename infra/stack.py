from typing import List, Optional

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_lambda as lamb
from aws_cdk import aws_ssm as ssm
from aws_cdk.aws_lambda_python_alpha import (BundlingOptions, PythonFunction,
                                             PythonLayerVersion)
from constructs import Construct

from .command_queue import CommandQueue
from .libs.constants import BUILD_DIR, LAMBDA_RUNTIME


class LegionTdDiscordBotStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, discord_public_key: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # Context
        self.discord_public_key = discord_public_key
        self.insights_arn = self.node.try_get_context("layerInsights")
        self.powertools_arn = self.node.try_get_context("layerPowertools")

        # Create SSM Parameters
        self.alert_webhook = self.create_ssm_parameter("alert_webhook", "Discord Webhook URL for alerts")

        # Create Lambda Layers
        self.lambda_layers = self.create_lambda_layers()

        # Create Command Queues and Functions
        self.create_command_queues()

        # Create Dispatcher Lambda
        self.dispatcher_lambda = self.create_dispatcher_lambda([self.alert_webhook])

        # Grant Lambda Permissions
        self.grant_lambda_permissions([self.manage_command])

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


    def create_command_queues(self):
        self.manage_command = CommandQueue(
            self,
            "ManageCommand",
            command_name="manage",
            layers=self.lambda_layers,
            ssm_parameters=[self.alert_webhook],
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
                "ALERT_WEBHOOK_PARAM": self.alert_webhook.parameter_name,
                "MANAGE_QUEUE_URL": self.manage_command.queue.queue_url,
            },
            layers=self.lambda_layers,
        )

        # Grant permission to read SSM parameters
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
            export_name="DiscordApiGatewayUrl"
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

    def grant_lambda_permissions(self, lambdas: list[CommandQueue]):
        for lambda_function in lambdas:
            lambda_function.queue.grant_send_messages(self.dispatcher_lambda)
