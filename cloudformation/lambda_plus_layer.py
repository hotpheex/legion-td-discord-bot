import subprocess
import sys
from tempfile import TemporaryDirectory
from shutil import make_archive
from venv import create
from hashlib import sha512

from awacs.aws import Allow, PolicyDocument, Principal, Statement
import awacs.sts as asts
import awacs.ssm as assm
import awacs.logs as alog
import awacs.elasticfilesystem as aefs

from troposphere import Ref, Tags, Sub, ImportValue, GetAtt
import troposphere.awslambda as lmd
import troposphere.apigateway as agw
import troposphere.iam as iam
import troposphere.ecs as ecs
import troposphere.elasticloadbalancingv2 as alb
import troposphere.route53 as r53
import troposphere.efs as efs
import troposphere.ec2 as ec2
import troposphere.logs as logs

import boto3
from botocore.exceptions import ClientError


def create_upload_deployment_archive(
    lambda_requirements, lambda_code, lambda_code_hash, s3_layer_bucket, lambda_name
):
    with TemporaryDirectory() as tmpdir:
        for dependency in lambda_requirements:
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--target",
                    f"{tmpdir}/archive",
                    dependency,
                ]
            )

        with open(f"{tmpdir}/archive/lambda_function.py", "w") as fh:
            fh.write(lambda_code)

        make_archive(f"{tmpdir}/archive", "zip", f"{tmpdir}/archive")

        s3_client = boto3.client("s3")
        try:
            response = s3_client.upload_file(
                f"{tmpdir}/archive.zip",
                s3_layer_bucket,
                f"{lambda_name}/archive-{lambda_code_hash}.zip",
            )
        except ClientError as e:
            raise SystemExit(e)
        print(f"{lambda_name}/archive-{lambda_code_hash}.zip Uploaded...")
    return True


def add(
    template,
    s3_layer_bucket,
    lambda_name,
    lambda_requirements,
    lambda_code,
    lambda_handler,
    lambda_runtime,
    lambda_vars={},
    iam_permissions=[],
):
    lambda_code_hash = sha512(lambda_code.encode("utf-8")).hexdigest()[:10]

    create_upload_deployment_archive(
        lambda_requirements, lambda_code, lambda_code_hash, s3_layer_bucket, lambda_name
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

    # lambda_layer = template.add_resource(
    #     lmd.LayerVersion(
    #         f"{cfn_name}LambdaLayer",
    #         LayerName=lambda_name,
    #         Content=lmd.Content(
    #             S3Bucket=s3_layer_bucket,
    #             S3Key=f"{lambda_name}/archive.zip",
    #         ),
    #     )
    # )

    lambda_function = template.add_resource(
        lmd.Function(
            f"{cfn_name}LambdaFunction",
            # Code=lmd.Code(ZipFile=lambda_code),
            # FunctionName=lambda_name,
            Code=lmd.Code(
                S3Bucket=s3_layer_bucket,
                S3Key=f"{lambda_name}/archive-{lambda_code_hash}.zip",
            ),
            Description=f"{lambda_name} Function",
            Environment=lmd.Environment(Variables=lambda_vars),
            Handler=f"lambda_function.{lambda_handler}",
            Role=GetAtt(iam_lambda_execution_role, "Arn"),
            Runtime=lambda_runtime,
            # Layers=[Ref(lambda_layer)],
        )
    )

    return template, f"{cfn_name}LambdaFunction"
