# from awacs.aws import Allow, PolicyDocument, Principal, Statement
# import awacs.sts as asts
# import awacs.ssm as assm
# import awacs.logs as alogs
# import awacs.elasticfilesystem as aefs

import troposphere.apigateway as agw
import troposphere.awslambda as lmb
from troposphere import GetAtt, Output, Ref, Sub


def add(
    template,
    api_endpoints,
    stage_name,
):
    rest_api = template.add_resource(
        agw.RestApi(
            "RestApiGateway",
            Description=Sub("${AWS::StackName}-rest-api"),
            EndpointConfiguration=agw.EndpointConfiguration(Types=["REGIONAL"]),
            Name=Sub("${AWS::StackName}-rest-api"),
        )
    )

    methods = []
    for endpoint in api_endpoints:
        resource = template.add_resource(
            agw.Resource(
                f'{endpoint["resource"]}ApiResource',
                ParentId=GetAtt(rest_api, "RootResourceId"),
                PathPart=endpoint["resource"],
                RestApiId=Ref(rest_api),
            )
        )

        for method in endpoint["methods"]:
            resource_name = f'{endpoint["resource"]}{method}Method'
            methods.append(resource_name)
            template.add_resource(
                agw.Method(
                    resource_name,
                    AuthorizationType="NONE",
                    HttpMethod=method,
                    ResourceId=GetAtt(resource, "ResourceId"),
                    RestApiId=Ref(rest_api),
                    Integration=agw.Integration(
                        IntegrationHttpMethod=method,
                        Type="AWS_PROXY",
                        Uri=Sub(
                            "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${lambdaArn}/invocations",
                            lambdaArn=GetAtt(endpoint["lambda"], "Arn"),
                        ),
                    ),
                )
            )

            template.add_resource(
                lmb.Permission(
                    f"{resource_name}Permission",
                    Action="lambda:InvokeFunction",
                    FunctionName=GetAtt(endpoint["lambda"], "Arn"),
                    Principal="apigateway.amazonaws.com",
                    SourceArn=Sub(
                        f"arn:aws:execute-api:${{AWS::Region}}:${{AWS::AccountId}}:${{RestApiGateway}}/*/{method}/{endpoint['resource']}"
                    )
                    # arn:aws:execute-api:ap-southeast-2:220346651581:eg2aogc4kk/*/POST/event
                )
            )

    api_gateway_deployment = template.add_resource(
        agw.Deployment(
            "ApiGatewayDeployment",
            DependsOn=methods,
            RestApiId=Ref(rest_api),
            StageName=stage_name,
        )
    )

    template.add_output(
        Output(
            "ApiGatewayInvokeUrl",
            Value=Sub(
                f"https://${{RestApiGateway}}.execute-api.${{AWS::Region}}.amazonaws.com/{stage_name}"
            ),
        )
    )

    return template
