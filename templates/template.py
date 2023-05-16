import awacs.awslambda as almb
import awacs.ssm as assm
from resources import api_gateway_lambda, lambda_function
from troposphere import GetAtt, Parameter, Ref, Sub, Template, ssm

s3_layer_bucket = "s3-buckets-lambdalayerbucket-1wvx0gjtmchjj"
lambda_name_prefix = "legion-td-discord-bot"

template = Template()
template.set_version("2010-09-09")

# Parameters
debug = template.add_parameter(
    Parameter(
        "EnableDebug",
        Description="Enable debug logging",
        Type="String",
        Default="false",
    )
)

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

challonge_api_key = template.add_parameter(
    Parameter(
        "ChallongeApiKey",
        Description="Challonge API Credentials",
        Type="String",
        NoEcho=True,
    )
)

alert_webhook = template.add_parameter(
    Parameter(
        "AlertWebhook",
        Description="Exception Alert Discord Webhook",
        Type="String",
        NoEcho=True,
    )
)

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

template, checkin_function_arn = lambda_function.add(
    template,
    s3_layer_bucket=s3_layer_bucket,
    lambda_name=f"{lambda_name_prefix}-checkin",
    local_path="../src/checkin",
    lambda_vars={
        "DEBUG": Ref(debug),
        "APPLICATION_ID": Ref(application_id),
        "GOOGLE_API_KEY": Ref(google_api_key),
        "GOOGLE_SHEET_ID": Ref(google_sheet_id),
        "CHECKIN_STATUS_PARAM": Ref(checkin_status_param),
        "ALERT_WEBHOOK": Ref(alert_webhook),
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

template, results_function_arn = lambda_function.add(
    template,
    s3_layer_bucket=s3_layer_bucket,
    lambda_name=f"{lambda_name_prefix}-results",
    local_path="../src/results",
    lambda_vars={
        "DEBUG": Ref(debug),
        "APPLICATION_ID": Ref(application_id),
        "GOOGLE_API_KEY": Ref(google_api_key),
        "GOOGLE_SHEET_ID": Ref(google_sheet_id),
        "CHALLONGE_API_KEY": Ref(challonge_api_key),
        "ALERT_WEBHOOK": Ref(alert_webhook),
    },
    iam_permissions=[],
)

template, manage_function_arn = lambda_function.add(
    template,
    s3_layer_bucket=s3_layer_bucket,
    lambda_name=f"{lambda_name_prefix}-manage",
    local_path="../src/manage",
    lambda_vars={
        "DEBUG": Ref(debug),
        "APPLICATION_ID": Ref(application_id),
        "CHECKIN_STATUS_PARAM": Ref(checkin_status_param),
        "CHALLONGE_API_KEY": Ref(challonge_api_key),
        "GOOGLE_API_KEY": Ref(google_api_key),
        "GOOGLE_SHEET_ID": Ref(google_sheet_id),
        "ALERT_WEBHOOK": Ref(alert_webhook),
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

template, handler_function_arn = lambda_function.add(
    template,
    s3_layer_bucket=s3_layer_bucket,
    lambda_name=f"{lambda_name_prefix}-handler",
    local_path="../src/handler",
    lambda_vars={
        "DEBUG": Ref(debug),
        "DISCORD_PUBLIC_KEY": Ref(discord_public_key),
        "LAMBDA_CHECKIN": GetAtt(checkin_function_arn, "Arn"),
        "LAMBDA_MANAGE": GetAtt(manage_function_arn, "Arn"),
        "LAMBDA_RESULTS": GetAtt(results_function_arn, "Arn"),
        "ALERT_WEBHOOK": Ref(alert_webhook),
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
        {
            "name": "invoke-results-function",
            "resources": [GetAtt(results_function_arn, "Arn")],
            "actions": [almb.InvokeFunction],
        },
    ],
)

template = api_gateway_lambda.add(
    template,
    handler_function=handler_function_arn,
    stage_name="stage",
)

with open("template.yaml", "w") as file_handle:
    file_handle.write(template.to_yaml())
