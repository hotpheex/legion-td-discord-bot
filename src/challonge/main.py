"""
Admin commands to manage Challonge
"""
import json
import logging
from os import environ

import requests
from requests import RequestException

import api

logging.getLogger().setLevel(logging.DEBUG)

APPLICATION_ID = environ["APPLICATION_ID"]

# api.create_tournament("Test Tourney", "testTourney1z2f1", "single elimination")


# tournaments = api.get_tournaments()
# print(tournaments)

tournament_url = "testTourney1z2f1"

# import challonge

# challonge.set_credentials("hotpheex", environ["CHALLONGE_API_KEY"])
# challonge.participants.bulk_add(tournament_url, ["test1", "test2", "test3"])


# api.add_participant(tournament_url, "testy2")
api.add_bulk_participant(tournament_url, ["test1", "test2", "test3", "test4"])


# participants = api.get_participants(CHALLONGE_API_KEY, "legion_test_division_4")

print(api.get_participants(tournament_url))


def lambda_handler(event, context):
    logging.debug(json.dumps(event))

    try:
        sub_command = event["data"]["options"][0]["name"]
        if sub_command == "update_bracket":
            response = requests.patch(
                f"https://discord.com/api/webhooks/{APPLICATION_ID}/{event['token']}/messages/@original",
                json={
                    "content": "testing",
                    "components": [
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 3,
                                    "options": [
                                        {
                                            "label": "label",
                                            "value": "value",
                                            "description": "description",
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                },
            )
            logging.info(response.status_code)
            logging.debug(response.text)
        logging.debug(response.json())

    except RequestException as e:
        logging.error(e)
    except Exception as e:
        logging.error(e)

    return True
