from os import environ

from troposphere import ssm
import awacs.awslambda as almb
import awacs.ssm as assm

import api_gateway_lambda, lambda_plus_layer

from troposphere import Template, Ref, Sub, GetAtt

application_id = "1015271519414399038"
s3_layer_bucket = "s3-buckets-lambdalayerbucket-1wvx0gjtmchjj"
lambda_name_prefix = "legion-td-discord-bot"
google_api_creds = environ["GOOGLE_API_CREDS"]
google_sheet_id = "1AwWaWBdKxYCSj6LLVZrsfI_zdo0gAqduvng_DkxmeE8"
discord_public_key = "42be1d3d4136ed14b3a46a60bb11fe92c73c0d84be9337f3e6f11e21edf6e75d"

template = Template()
template.set_version("2010-09-09")

checkin_status_param = template.add_resource(
    ssm.Parameter(
        "SsmParameterCheckinStatus",
        Name=f"/{lambda_name_prefix}/checkin-status",
        Description="Tournament checkin status",
        Type="String",
        Value="false",
    )
)

template, checkin_function_arn = lambda_plus_layer.add(
    template,
    s3_layer_bucket=s3_layer_bucket,
    lambda_name=f"{lambda_name_prefix}-checkin",
    lambda_requirements=open("../src/checkin/requirements.txt").readlines(),
    lambda_code=open("../src/checkin/lambda.py").read(),
    lambda_handler="lambda_handler",
    lambda_runtime="python3.9",
    lambda_vars={
        "APPLICATION_ID": application_id,
        "GOOGLE_API_CREDS": google_api_creds,
        "GOOGLE_SHEET_ID": google_sheet_id,
    },
)

template, manage_function_arn = lambda_plus_layer.add(
    template,
    s3_layer_bucket=s3_layer_bucket,
    lambda_name=f"{lambda_name_prefix}-manage",
    lambda_requirements=open("../src/manage/requirements.txt").readlines(),
    lambda_code=open("../src/manage/lambda.py").read(),
    lambda_handler="lambda_handler",
    lambda_runtime="python3.9",
    lambda_vars={
        "APPLICATION_ID": application_id,
        "CHECKIN_STATUS_PARAM": Ref(checkin_status_param),
    },
    iam_permissions=[
        {
            "name": "use-checkin-status-param",
            "resources": [
                Sub(
                    "arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter${SsmParameterCheckinStatus}"
                )
            ],
            "actions": [assm.PutParameter, assm.GetParameter],
        }
    ],
)

template, handler_function_arn = lambda_plus_layer.add(
    template,
    s3_layer_bucket=s3_layer_bucket,
    lambda_name=f"{lambda_name_prefix}-handler",
    lambda_requirements=open("../src/handler/requirements.txt").readlines(),
    lambda_code=open("../src/handler/lambda.py").read(),
    lambda_handler="lambda_handler",
    lambda_runtime="python3.9",
    lambda_vars={
        "DISCORD_PUBLIC_KEY": discord_public_key,
        "LAMBDA_CHECKIN": GetAtt(checkin_function_arn, "Arn"),
        "LAMBDA_MANAGE": GetAtt(manage_function_arn, "Arn"),
    },
    iam_permissions=[
        {
            "name": "invoke-checkin-function",
            "resources": [GetAtt(checkin_function_arn, "Arn")],
            "actions": [almb.InvokeFunction],
        },
        {
            "name": "invoke-manage-function",
            "resources": [GetAtt(manage_function_arn, "Arn")],
            "actions": [almb.InvokeFunction],
        },
    ],
)

template = api_gateway_lambda.add(
    template,
    api_endpoints=[
        {"resource": "event", "methods": ["POST"], "lambda": handler_function_arn},
    ],
    stage_name="stage",
)

with open("template.yaml", "w") as file_handle:
    file_handle.write(template.to_yaml())
