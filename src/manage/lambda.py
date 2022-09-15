"""
Admin commands to manage tournaments
"""
import json
import logging
import os

import boto3
from requests import patch
from requests.exceptions import RequestException

logging.getLogger().setLevel(logging.INFO)

CHECKIN_STATUS_PARAM = os.environ["CHECKIN_STATUS_PARAM"]
APPLICATION_ID = os.environ["APPLICATION_ID"]


def get_checkin_status(client):
    response = client.get_parameter(Name=CHECKIN_STATUS_PARAM)
    logging.debug(response)

    if response["Parameter"]["Value"] == "true":
        return True
    elif response["Parameter"]["Value"] == "false":
        return False
    else:
        raise Exception()


def set_checkin_status(client, event):
    current_status = get_checkin_status(client)
    desired_status = event["data"]["options"][0]["options"][0]["value"]

    if current_status == desired_status:
        return f"Checkins already set to `{current_status}`"
    else:
        response = client.put_parameter(
            Name=CHECKIN_STATUS_PARAM, Value=str(desired_status).lower(), Overwrite=True
        )
        logging.debug(response)
        return f"Checkins are now set to `{desired_status}`"


def lambda_handler(event, context):
    logging.debug(json.dumps(event))

    client = boto3.client("ssm")

    try:
        sub_command = event["data"]["options"][0]["name"]
        if sub_command == "checkin_status":
            current_status = get_checkin_status(client)
            if current_status:
                message = "Checkins are currently `enabled`"
            else:
                message = "Checkins are currently `disabled`"
        elif sub_command == "checkin_enabled":
            message = set_checkin_status(client, event)

        response = patch(
            f"https://discord.com/api/webhooks/{APPLICATION_ID}/{event['token']}/messages/@original",
            json={"content": message},
        )
        logging.info(response.status_code)
        logging.debug(response.json())

    except RequestException as e:
        logging.error(e)
    except Exception as e:
        logging.error(e)

    return True
