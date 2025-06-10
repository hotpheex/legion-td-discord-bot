from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
)
from constructs import Construct
from .command_queue import CommandQueue

class LegionTdDiscordBotStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Shared dispatcher lambda (validates & dispatches)
        dispatcher = _lambda.Function(self, "DispatcherLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="dispatcher.main",
            code=_lambda.Code.from_asset("functions/dispatcher"),
            environment={
                # "JOIN_QUEUE_URL": "<to be filled after creation>",
                # "START_QUEUE_URL": "<to be filled after creation>",
            },
        )

        # # Command: /join
        # join_command = CommandQueue(self, "JoinCommand",
        #                             command_name="join",
        #                             handler_path="functions/join")

        # # Command: /start
        # start_command = CommandQueue(self, "StartCommand",
        #                              command_name="start",
        #                              handler_path="functions/start")

        # # Update dispatcher env
        # dispatcher.add_environment("JOIN_QUEUE_URL", join_command.queue.queue_url)
        # dispatcher.add_environment("START_QUEUE_URL", start_command.queue.queue_url)

        # # Grant dispatch permissions
        # join_command.queue.grant_send_messages(dispatcher)
        # start_command.queue.grant_send_messages(dispatcher)

        # HTTP API Gateway
        http_api = apigwv2.HttpApi(self, "DiscordAPI")

        http_api.add_routes(
            path="/interactions",
            methods=[apigwv2.HttpMethod.POST],
            integration=integrations.HttpLambdaIntegration("DispatchIntegration", dispatcher)
        )

        self.http_api_url = http_api.url
