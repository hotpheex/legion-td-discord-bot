"""
Admin commands to manage tournaments
"""
from sys import path
path.append('..')
import json
import logging
import traceback
from math import ceil
from os import environ

import boto3
from libs.challonge import Challonge
from requests import patch, post

logging.getLogger().setLevel(logging.DEBUG)


CHECKIN_STATUS_PARAM = environ["CHECKIN_STATUS_PARAM"]
APPLICATION_ID = environ["APPLICATION_ID"]
ALERT_WEBHOOK = environ["ALERT_WEBHOOK"]
CHALLONGE_API_KEY = environ["CHALLONGE_API_KEY"]


def get_checkin_status(client):
    response = client.get_parameter(Name=CHECKIN_STATUS_PARAM)
    logging.debug(response)
    return response["Parameter"]["Value"]


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


def calculate_team_seed(event):
    ratings = []
    for player in event["data"]["options"][0]["options"]:
        ratings.append(player["value"])

    team_rating = ceil((2 * max(ratings) + min(ratings)) / 3)

    return f"Team rating for `{ratings}`: `{team_rating}`"


def lambda_handler(event, context):
    logging.debug(json.dumps(event))

    client = boto3.client("ssm")
    challonge = Challonge(CHALLONGE_API_KEY)
    print(challonge)

    try:
        sub_command = event["data"]["options"][0]["name"]
        if sub_command == "checkin_status":
            current_status = get_checkin_status(client)
            message = f"Checkins are currently set to `{current_status}`"
        elif sub_command == "checkin_enabled":
            message = set_checkin_status(client, event)
        elif sub_command == "calculate_seed":
            message = calculate_team_seed(event)
        elif sub_command == "update_bracket":
            message = challonge.update_bracket(event)
        else:
            raise Exception(f"{sub_command} is not a valid command")

        response = patch(
            f"https://discord.com/api/webhooks/{APPLICATION_ID}/{event['token']}/messages/@original",
            json={"content": message},
        )
        response.raise_for_status()
        logging.info(response.status_code)
        logging.debug(response.json())
    except Exception as e:
        logging.exception(e)
        post(
            ALERT_WEBHOOK,
            json={
                "content": f"`{context.function_name} - {context.log_stream_name}`\n```{traceback.format_exc()}```"
            },
        )
        patch(
            f"https://discord.com/api/webhooks/{APPLICATION_ID}/{event['token']}/messages/@original",
            json={"content": ":warning: Command failed unexpectedly"},
        )
