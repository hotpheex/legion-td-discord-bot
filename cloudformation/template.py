from os import environ

import awacs.awslambda as almb
import awacs.ssm as assm
from troposphere import Template, Parameter, GetAtt, Ref, Sub, ssm

from resources import api_gateway_lambda, lambda_plus_layer

s3_layer_bucket = "s3-buckets-lambdalayerbucket-1wvx0gjtmchjj"
lambda_name_prefix = "legion-td-discord-bot"

template = Template()
template.set_version("2010-09-09")

# Parameters
application_id = template.add_parameter(
    Parameter(
        "DiscordApplicationId",
        Description="Discord Application ID",
        Type="String",
    )
)

discord_public_key = template.add_parameter(
    Parameter(
        "DiscordPublicKey",
        Description="Discord Public Key",
        Type="String",
    )
)

google_api_key = template.add_parameter(
    Parameter(
        "GoogleApiKey",
        Description="Google API Key",
        Type="String",
        NoEcho=True,
    )
)

google_sheet_id = template.add_parameter(
    Parameter(
        "GoogleSheetId",
        Description="Google Sheet ID",
        Type="String",
    )
)

# challonge_api_key = template.add_parameter(
#     Parameter(
#         "ChallongeApiKey",
#         Description="Challonge API Credentials",
#         Type="String",
#         NoEcho=True,
#     )
# )

# Resources
checkin_status_param = template.add_resource(
    ssm.Parameter(
        "SsmParameterCheckinStatus",
        Name=Sub("/${AWS::StackName}/checkin-status"),
        Description="Tournament checkin status",
        Type="String",
        Value="false",
    )
)

template, checkin_function_arn = lambda_plus_layer.add(
    template,
    s3_layer_bucket=s3_layer_bucket,
    lambda_name=f"{lambda_name_prefix}-checkin",
    local_path="../src/checkin",
    lambda_runtime="python3.9",
    lambda_vars={
        "APPLICATION_ID": Ref(application_id),
        "GOOGLE_API_KEY": Ref(google_api_key),
        "GOOGLE_SHEET_ID": Ref(google_sheet_id),
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
            "actions": [assm.GetParameter],
        }
    ],
)

template, manage_function_arn = lambda_plus_layer.add(
    template,
    s3_layer_bucket=s3_layer_bucket,
    lambda_name=f"{lambda_name_prefix}-manage",
    local_path="../src/manage",
    lambda_runtime="python3.9",
    lambda_vars={
        "APPLICATION_ID": Ref(application_id),
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

# template, challonge_function_arn = lambda_plus_layer.add(
#     template,
#     s3_layer_bucket=s3_layer_bucket,
#     lambda_name=f"{lambda_name_prefix}-challonge",
#     lambda_requirements=open("../src/challonge/requirements.txt").readlines(),
#     lambda_code=open("../src/challonge/lambda.py").read(),
#     lambda_runtime="python3.9",
#     lambda_vars={
#         "APPLICATION_ID": Ref(application_id),
#         "CHALLONGE_API_KEY": Ref(challonge_api_key),
#     },
# )

template, handler_function_arn = lambda_plus_layer.add(
    template,
    s3_layer_bucket=s3_layer_bucket,
    lambda_name=f"{lambda_name_prefix}-handler",
    local_path="../src/handler",
    lambda_runtime="python3.9",
    lambda_vars={
        "DISCORD_PUBLIC_KEY": Ref(discord_public_key),
        "LAMBDA_CHECKIN": GetAtt(checkin_function_arn, "Arn"),
        "LAMBDA_MANAGE": GetAtt(manage_function_arn, "Arn"),
        # "LAMBDA_CHALLONGE": GetAtt(challonge_function_arn, "Arn"),
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
        # {
        #     "name": "invoke-challonge-function",
        #     "resources": [GetAtt(challonge_function_arn, "Arn")],
        #     "actions": [almb.InvokeFunction],
        # },
    ],
)

template = api_gateway_lambda.add(
    template,
    handler_function=handler_function_arn,
    stage_name="stage",
)

with open("template.yaml", "w") as file_handle:
    file_handle.write(template.to_yaml())
