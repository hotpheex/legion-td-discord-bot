import api_gateway_lambda, lambda_plus_layer

from troposphere import Template

template = Template()
template.set_version("2010-09-09")

with open("../src/event/requirements.txt") as fh:
    lambda_requirements = fh.readlines()
with open("../src/event/lambda.py", "r") as fh:
    lambda_code = fh.read()

template, event_arn = lambda_plus_layer.add(
    template,
    s3_layer_bucket="s3-buckets-lambdalayerbucket-1wvx0gjtmchjj",
    lambda_name="legion-td-discord-bot",
    lambda_requirements=lambda_requirements,
    lambda_code=lambda_code,
    lambda_handler="lambda_function.lambda_handler",
    lambda_runtime="python3.9",
    lambda_vars={
        "DISCORD_PUBLIC_KEY": "42be1d3d4136ed14b3a46a60bb11fe92c73c0d84be9337f3e6f11e21edf6e75d"
    },
)

template = api_gateway_lambda.add(
    template,
    api_endpoints=[
        {"resource": "event", "methods": ["POST"], "lambda": event_arn},
    ],
    stage_name="stage",
)

with open("template.yaml", "w") as file_handle:
    file_handle.write(template.to_yaml())
