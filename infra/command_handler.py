from pathlib import Path
from typing import List, Optional

from aws_cdk import Duration
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lamb
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from .libs.constants import *


class CommandHandler(Construct):
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

        deployment_dir = BUILD_DIR / command_name

        if ssm_parameters:
            for param in ssm_parameters:
                env_var_name = f"{param.node.id.upper()}_PARAM"
                print(f"Setting environment variable: {env_var_name} = {param.parameter_name}")
                environment[env_var_name] = param.parameter_name

        print(f"Final environment variables for {command_name}: {environment}")

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

        if ssm_parameters:
            for param in ssm_parameters:
                param.grant_read(function)

        if additional_policies:
            for policy in additional_policies:
                function.add_to_role_policy(policy)

        self.lambda_function = function
