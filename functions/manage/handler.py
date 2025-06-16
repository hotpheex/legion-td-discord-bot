import json
import os
import traceback

import requests
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.parameters import get_parameter

# Initialize Powertools
logger = Logger()
tracer = Tracer()

logger.setLevel("DEBUG")

ALERT_WEBHOOK = get_parameter(os.environ["ALERT_WEBHOOK_PARAM"])

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    logger.debug(json.dumps(event))

    try:
        # Process each record from SQS
        for record in event["Records"]:
            body = json.loads(record["body"])
            logger.info(f"Processing command: {body['data']['name']}")
            
            # TODO: Implement command processing logic
            
    except Exception as e:
        logger.exception(e)
        res = requests.post(
            ALERT_WEBHOOK,
            json={
                "content": f"`{context.function_name} - {context.log_stream_name}`\n```{traceback.format_exc()}```"
            },
        )
        logger.debug(res.status_code)
        raise e

    return {"statusCode": 200, "body": "Success"}
