from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_lambda as lamb
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion, PythonFunction, BundlingOptions
from aws_cdk import DockerVolume
from constructs import Construct
from pathlib import Path

from .command_queue import CommandQueue
from .libs.constants import LAMBDA_RUNTIME, BUILD_DIR


class LegionTdDiscordBotStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

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

        # Get the deployment package path
        deployment_dir = BUILD_DIR / "dispatcher"

        # Create the Lambda function using the deployment package
        dispatcher = lamb.Function(
            self,
            "DispatcherLambda",
            runtime=LAMBDA_RUNTIME,
            handler="handler.handler",
            code=lamb.Code.from_asset(str(deployment_dir)),
            environment={},
        )

        # Command: /manage
        manage_command = CommandQueue(
            self,
            "ManageCommand",
            command_name="manage",
            handler_path="functions/manage",
            layers=[libs_layer],
        )

        # # Command: /start
        # start_command = CommandQueue(self, "StartCommand",
        #                              command_name="start",
        #                              handler_path="functions/start")

        # Update dispatcher env
        dispatcher.add_environment("MANAGE_QUEUE_URL", manage_command.queue.queue_url)
        # dispatcher.add_environment("START_QUEUE_URL", start_command.queue.queue_url)

        # Grant dispatch permissions
        manage_command.queue.grant_send_messages(dispatcher)
        # start_command.queue.grant_send_messages(dispatcher)

        # HTTP API Gateway
        http_api = apigwv2.HttpApi(self, "DiscordAPI")

        http_api.add_routes(
            path="/interactions",
            methods=[apigwv2.HttpMethod.POST],
            integration=integrations.HttpLambdaIntegration(
                "DispatchIntegration",
                lamb.Function.from_function_attributes(
                    self,
                    "DispatcherRef",
                    function_arn=dispatcher.function_arn,
                    same_environment=True,
                ),
            ),
        )

        self.http_api_url = http_api.url

        CfnOutput(self, "ApiGatewayInvokeUrl", value=http_api.url or "")
