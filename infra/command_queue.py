from pathlib import Path
from typing import List, Optional

from aws_cdk import Duration
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lamb
from aws_cdk import aws_lambda_event_sources as events
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from .libs.constants import *


class CommandQueue(Construct):

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        command_name: str,
        layers: list[lamb.ILayerVersion] = [],
        environment: dict = {},
        timeout: Duration = LAMBDA_TIMEOUT,
        ssm_parameters: Optional[List[ssm.StringParameter]] = None,
        additional_policies: Optional[List[iam.PolicyStatement]] = None,
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

        if ssm_parameters:
            for param in ssm_parameters:
                # Use the parameter's logical ID for the environment variable name
                env_var_name = f"{param.node.id.upper()}_PARAM"
                print(
                    f"Setting environment variable: {env_var_name} = {param.parameter_name}"
                )
                environment[env_var_name] = param.parameter_name

        print(f"Final environment variables for {command_name}: {environment}")

        # Command Lambda
        function = lamb.Function(
            self,
            f"{command_name}Handler",
            runtime=LAMBDA_RUNTIME,
            handler="handler.handler",
            code=lamb.Code.from_asset(str(deployment_dir)),
            layers=layers,
            environment=environment,
            timeout=timeout,
            memory_size=256,
        )

        # Grant SSM parameter read permissions
        if ssm_parameters:
            for param in ssm_parameters:
                param.grant_read(function)

        # Add additional policies if provided
        if additional_policies:
            for policy in additional_policies:
                function.add_to_role_policy(policy)

        # Lambda trigger on queue
        function.add_event_source(events.SqsEventSource(queue))

        self.queue = queue
        self.dlq = dlq
        self.lambda_function = function
