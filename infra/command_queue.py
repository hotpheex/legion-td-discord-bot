from pathlib import Path
from typing import List, Optional

from aws_cdk import Duration
from aws_cdk import aws_lambda as lamb
from aws_cdk import aws_lambda_event_sources as events
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from .libs.constants import BUILD_DIR, LAMBDA_RUNTIME


class CommandQueue(Construct):

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        command_name: str,
        layers: list[lamb.ILayerVersion] = [],
        handler_env: dict = {},
        timeout: Duration = Duration.seconds(10),
        ssm_parameters: Optional[List[ssm.StringParameter]] = None,
    ) -> None:
        super().__init__(scope, id)

        # DLQ
        dlq = sqs.Queue(self, f"{command_name}DLQ", retention_period=Duration.days(14))

        # Main queue
        queue = sqs.Queue(
            self,
            f"{command_name}Queue",
            visibility_timeout=timeout,
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=3, queue=dlq),
        )

        # Get the deployment package path
        deployment_dir = BUILD_DIR / command_name

        # Add SSM parameters to environment variables
        env = handler_env.copy()
        if ssm_parameters:
            for param in ssm_parameters:
                # Use the parameter's logical ID for the environment variable name
                env_var_name = f"{param.node.id.upper()}_PARAM"
                print(f"Setting environment variable: {env_var_name} = {param.parameter_name}")
                env[env_var_name] = param.parameter_name

        print(f"Final environment variables for {command_name}: {env}")

        # Command Lambda
        function = lamb.Function(
            self,
            f"{command_name}Handler",
            runtime=LAMBDA_RUNTIME,
            handler="handler.main",
            code=lamb.Code.from_asset(str(deployment_dir)),
            layers=layers,
            environment=env,
            timeout=timeout,
        )

        # Grant SSM parameter read permissions
        if ssm_parameters:
            for param in ssm_parameters:
                param.grant_read(function)

        # Lambda trigger on queue
        function.add_event_source(events.SqsEventSource(queue))

        self.queue = queue
        self.dlq = dlq
        self.lambda_function = function
