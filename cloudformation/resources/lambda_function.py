import subprocess
from hashlib import sha512
from os import path
from shutil import copytree, make_archive
from sys import executable
from tempfile import TemporaryDirectory

import awacs.logs as alog
import awacs.sts as asts
import boto3
import troposphere.awslambda as lmd
import troposphere.iam as iam
from awacs.aws import Allow, PolicyDocument, Principal, Statement
from botocore.exceptions import ClientError
from troposphere import GetAtt, Sub


# def create_upload_deployment_archive(local_path, s3_layer_bucket, lambda_name):
#     with TemporaryDirectory() as tmpdir:
#         copytree(local_path, f"{tmpdir}/archive/handler")
#         copytree("../src/libs", f"{tmpdir}/archive/libs")

#         if path.exists(f"{tmpdir}/archive/handler/requirements.txt"):
#             subprocess.check_call(
#                 [
#                     executable,
#                     "-m",
#                     "pip",
#                     "install",
#                     "--target",
#                     f"{tmpdir}/archive",
#                     "-r",
#                     f"{tmpdir}/archive/handler/requirements.txt",
#                 ]
#             )

#         make_archive(f"{tmpdir}/archive", "zip", f"{tmpdir}/archive")

#         with open(f"{tmpdir}/archive.zip", "rb") as fh:
#             lambda_code_hash = sha512(fh.read()).hexdigest()[:10]

#         s3_client = boto3.client("s3")
#         try:
#             s3_client.upload_file(
#                 f"{tmpdir}/archive.zip",
#                 s3_layer_bucket,
#                 f"{lambda_name}/archive-{lambda_code_hash}.zip",
#             )
#         except ClientError as e:
#             raise SystemExit(e)
#         print(f"{lambda_name}/archive-{lambda_code_hash}.zip Uploaded...")

#     return lambda_code_hash


def create_upload_deployment_archive(local_path, s3_layer_bucket, lambda_name):
    copytree(local_path, f"build/{lambda_name}/archive/handler", dirs_exist_ok=True)
    copytree("../src/libs", f"build/{lambda_name}/archive/libs", dirs_exist_ok=True)

    if path.exists(f"build/{lambda_name}/archive/handler/requirements.txt"):
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

    with open(f"build/{lambda_name}/archive.zip", "rb") as fh:
        lambda_code_hash = sha512(fh.read()).hexdigest()[:10]

    s3_client = boto3.client("s3")
    try:
        s3_client.upload_file(
            f"build/{lambda_name}/archive.zip",
            s3_layer_bucket,
            f"{lambda_name}/archive-{lambda_code_hash}.zip",
        )
    except ClientError as e:
        raise SystemExit(e)
    print(f"{lambda_name}/archive-{lambda_code_hash}.zip Uploaded...")

    return lambda_code_hash


def add(
    template,
    s3_layer_bucket,
    lambda_name,
    local_path,
    lambda_runtime,
    lambda_timeout=180,
    lambda_vars={},
    iam_permissions=[],
):
    lambda_code_hash = create_upload_deployment_archive(
        local_path, s3_layer_bucket, lambda_name
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
                S3Bucket=s3_layer_bucket,
                S3Key=f"{lambda_name}/archive-{lambda_code_hash}.zip",
            ),
            Description=Sub(f"${{AWS::StackName}} {lambda_name} Function"),
            Environment=lmd.Environment(Variables=lambda_vars),
            Handler=f"handler/main.lambda_handler",
            Role=GetAtt(iam_lambda_execution_role, "Arn"),
            Runtime=lambda_runtime,
            Timeout=lambda_timeout,
        )
    )

    return template, f"{cfn_name}LambdaFunction"
