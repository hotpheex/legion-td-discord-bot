import os
import json
import boto3

sqs = boto3.client("sqs")

queue_map = {
    "join": os.environ["JOIN_QUEUE_URL"],
    "start": os.environ["START_QUEUE_URL"],
}

def main(event, context):
    body = json.loads(event["body"])
    command = body["data"]["name"]

    queue_url = queue_map.get(command)
    if not queue_url:
        raise Exception(f"Unknown command: {command}")

    sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(body))
    return { "statusCode": 200, "body": "OK" }
