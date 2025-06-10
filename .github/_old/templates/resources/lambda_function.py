import subprocess
import hashlib
import os
from shutil import copytree, make_archive, rmtree
from sys import executable

import awacs.logs as alog
import awacs.sts as asts
import boto3
import troposphere.awslambda as lmd
import troposphere.iam as iam
from awacs.aws import Allow, PolicyDocument, Principal, Statement
from botocore.exceptions import ClientError
from troposphere import GetAtt, Ref, Sub

def create_hash(directory):
    sha256_hash = hashlib.sha256()

    for root, _, files in os.walk(directory):
        for names in files:
            filepath = os.path.join(root, names)
            try:
                with open(filepath, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
            except Exception as e:
                print("Couldn't open %s" % filepath)
                print("Exception: %s" % str(e))
                pass
    return sha256_hash.hexdigest()[:12]

def create_upload_deployment_archive(local_path, s3_lambda_bucket, lambda_name):
    s3_client = boto3.client("s3")

    if os.path.exists(f"build/{lambda_name}/archive"):
        rmtree(f"build/{lambda_name}/archive")

    copytree(local_path, f"build/{lambda_name}/archive/handler", dirs_exist_ok=True)
    if lambda_name != "legion-td-discord-bot-handler":
        copytree("src/libs", f"build/{lambda_name}/archive/libs", dirs_exist_ok=True)


    hash = create_hash(f"build/{lambda_name}/archive")

    try:
        # If the object exists, skip building
        object_name = f"{lambda_name}/archive-{hash}.zip"
        s3_client.head_object(Bucket=s3_lambda_bucket, Key=object_name)
        print(f"\033[92mSkipping {object_name}...\033[0m")
        return hash
    except:
        print(f"\033[93mBuilding {object_name}...\033[0m")

    if os.path.exists(f"build/{lambda_name}/archive/handler/requirements.txt"):
        subprocess.check_call(
            [
                executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "--target",
                f"build/{lambda_name}/archive",
                "-r",
                f"build/{lambda_name}/archive/handler/requirements.txt",
            ]
        )

    make_archive(f"build/{lambda_name}/archive", "zip", f"build/{lambda_name}/archive")

    try:
        # Object does not exist, so upload the file
        s3_client.upload_file(
            f"build/{lambda_name}/archive.zip",
            s3_lambda_bucket,
            object_name,
        )
        print(f"\033[93m'{object_name}' uploaded to the bucket\033[0m")
    except ClientError as err:
        raise SystemExit(err)

    return hash


def add(
    template,
    s3_lambda_bucket,
    lambda_name,
    local_path,
    lambda_timeout=180,
    lambda_vars={},
    iam_permissions=[],
):
    archive_hash = create_upload_deployment_archive(
        local_path, s3_lambda_bucket, lambda_name
    )

    cfn_name = lambda_name.replace("-", " ").title().replace(" ", "")

    iam_statements = []

    iam_permissions.append(
        {
            "name": "log-to-cloudwatch",
            "resources": [
                "*"
                # Sub(
                #     f"arn:aws:logs:${{AWS::Region}}:${{AWS::AccountId}}:log-group:/aws/lambda/{lambda_name}*"
                # )
            ],
            "actions": [
                alog.CreateLogGroup,
                alog.CreateLogStream,
                alog.PutLogEvents,
            ],
        }
    )

    for statement in iam_permissions:
        iam_statements.append(
            iam.Policy(
                PolicyName=f"{lambda_name}-{statement['name']}",
                PolicyDocument=PolicyDocument(
                    Statement=[
                        Statement(
                            Effect=Allow,
                            Resource=statement["resources"],
                            Action=statement["actions"],
                        )
                    ]
                ),
            )
        )

    iam_lambda_execution_role = template.add_resource(
        iam.Role(
            f"{cfn_name}LambdaExecutionRole",
            AssumeRolePolicyDocument=PolicyDocument(
                Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[asts.AssumeRole],
                        Principal=Principal("Service", ["lambda.amazonaws.com"]),
                    )
                ]
            ),
            Path="/",
            Policies=iam_statements,
        )
    )

    lambda_function = template.add_resource(
        lmd.Function(
            f"{cfn_name}LambdaFunction",
            Code=lmd.Code(
                S3Bucket=s3_lambda_bucket,
                S3Key=f"{lambda_name}/archive-{archive_hash}.zip",
            ),
            Description=Sub(f"${{AWS::StackName}} {lambda_name} Function"),
            Environment=lmd.Environment(Variables=lambda_vars),
            Handler=f"handler/main.lambda_handler",
            Role=GetAtt(iam_lambda_execution_role, "Arn"),
            Runtime="python3.10",
            Timeout=lambda_timeout,
        )
    )

    lambda_invoke_config = template.add_resource(
        lmd.EventInvokeConfig(
            f"{cfn_name}LambdaInvokeConfig",
            FunctionName=Ref(lambda_function),
            MaximumRetryAttempts=0,
            Qualifier="$LATEST",
        )
    )

    return template, f"{cfn_name}LambdaFunction"
