import troposphere.apigateway as agw
import troposphere.awslambda as lmb
from troposphere import GetAtt, Output, Ref, Sub


def add(template, handler_function, stage_name):
    rest_api = template.add_resource(
        agw.RestApi(
            "RestApiGateway",
            Description=Sub("${AWS::StackName}-rest-api"),
            EndpointConfiguration=agw.EndpointConfiguration(Types=["REGIONAL"]),
            Name=Sub("${AWS::StackName}-rest-api"),
        )
    )

    method = template.add_resource(
        agw.Method(
            "PostMethod",
            AuthorizationType="NONE",
            HttpMethod="POST",
            ResourceId=GetAtt(rest_api, "RootResourceId"),
            RestApiId=Ref(rest_api),
            Integration=agw.Integration(
                IntegrationHttpMethod="POST",
                Type="AWS_PROXY",
                Uri=Sub(
                    "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${lambdaArn}/invocations",
                    lambdaArn=GetAtt(handler_function, "Arn"),
                ),
            ),
            MethodResponses=[
                agw.MethodResponse(
                    ResponseModels={"application/json": "Empty"}, StatusCode="200"
                )
            ],
        )
    )

    template.add_resource(
        lmb.Permission(
            "PostMethodPermission",
            Action="lambda:InvokeFunction",
            FunctionName=GetAtt(handler_function, "Arn"),
            Principal="apigateway.amazonaws.com",
            SourceArn=Sub(
                "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${RestApiGateway}/*/POST/"
            ),
        )
    )

    template.add_resource(
        agw.Deployment(
            "ApiGatewayDeployment",
            DependsOn=method,
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
