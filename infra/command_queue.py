from aws_cdk import (
    aws_lambda as _lambda,
    aws_sqs as sqs,
    aws_lambda_event_sources as events,
    Duration,
    Stack
)
from constructs import Construct

class CommandQueue(Construct):

    def __init__(self, scope: Construct, id: str, *,
                 command_name: str,
                 handler_path: str,
                 handler_env: dict = None,
                 timeout: Duration = Duration.seconds(10)) -> None:
        super().__init__(scope, id)

        # DLQ
        dlq = sqs.Queue(self, f"{command_name}DLQ",
                        retention_period=Duration.days(14))

        # Main queue
        queue = sqs.Queue(self, f"{command_name}Queue",
                          visibility_timeout=timeout,
                          dead_letter_queue=sqs.DeadLetterQueue(
                              max_receive_count=3,
                              queue=dlq
                          ))

        # Command Lambda
        fn = _lambda.Function(self, f"{command_name}Handler",
                              runtime=_lambda.Runtime.PYTHON_3_11,
                              handler="handler.main",
                              code=_lambda.Code.from_asset(handler_path),
                              environment=handler_env or {},
                              timeout=timeout)

        # Lambda trigger on queue
        fn.add_event_source(events.SqsEventSource(queue))

        self.queue = queue
        self.dlq = dlq
        self.lambda_function = fn
