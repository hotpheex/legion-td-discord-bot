from aws_cdk import (
    Stack,
    aws_lambda as lamb,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    CfnOutput
)
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from constructs import Construct
from .command_queue import CommandQueue


LAMBDA_RUNTIME = lamb.Runtime.PYTHON_3_13


class LegionTdDiscordBotStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Libs Lambda Layer
        libs_layer = PythonLayerVersion(
            self,
            "LibsLayer",
            entry="functions/libs",
            compatible_runtimes=[LAMBDA_RUNTIME],
        )

        # Shared dispatcher lambda (validates & dispatches)
        dispatcher = lamb.Function(
            self,
            "DispatcherLambda",
            runtime=LAMBDA_RUNTIME,
            handler="handler.main",
            code=lamb.Code.from_asset("functions/dispatcher"),
            layers=[libs_layer],
            environment={
                # "JOIN_QUEUE_URL": "<to be filled after creation>",
                # "START_QUEUE_URL": "<to be filled after creation>",
            },
        )

        # Command: /manage
        manage_command = CommandQueue(
            self,
            "ManageCommand",
            runtime=LAMBDA_RUNTIME,
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
                "DispatchIntegration", dispatcher
            ),
        )

        self.http_api_url = http_api.url
    # template.add_output(
    #     Output(
    #         "ApiGatewayInvokeUrl",
    #         Value=Sub(
    #             f"https://${{RestApiGateway}}.execute-api.${{AWS::Region}}.amazonaws.com/{stage_name}"
    #         ),
    #     )
    # )