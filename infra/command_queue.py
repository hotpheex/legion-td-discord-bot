from aws_cdk import Duration
from aws_cdk import aws_lambda as lamb
from aws_cdk import aws_lambda_event_sources as events
from aws_cdk import aws_sqs as sqs
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from constructs import Construct
from pathlib import Path

from .libs.constants import LAMBDA_RUNTIME


class CommandQueue(Construct):

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        command_name: str,
        handler_path: str,
        layers: list[PythonLayerVersion] = [],
        handler_env: dict = {},
        timeout: Duration = Duration.seconds(10),
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
        deployment_dir = Path(__file__).parent.parent / "deployment" / command_name

        # Command Lambda
        fn = lamb.Function(
            self,
            f"{command_name}Handler",
            runtime=LAMBDA_RUNTIME,
            handler="handler.main",
            code=lamb.Code.from_asset(str(deployment_dir)),
            layers=layers,
            environment=handler_env or {},
            timeout=timeout,
        )

        # Lambda trigger on queue
        fn.add_event_source(events.SqsEventSource(queue))

        self.queue = queue
        self.dlq = dlq
        self.lambda_function = fn
