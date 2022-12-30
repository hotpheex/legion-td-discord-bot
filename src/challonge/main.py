"""
Admin commands to manage Challonge
"""
import json
import logging
from os import environ

import requests
from requests import RequestException

logging.getLogger().setLevel(logging.DEBUG)

BASE_URL = "https://api.challonge.com/v1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36"
}
CHALLONGE_API_KEY = environ["CHALLONGE_API_KEY"]
APPLICATION_ID = environ["APPLICATION_ID"]

# tournaments = api.get_tournaments(CHALLONGE_API_KEY)

# participants = api.get_participants(CHALLONGE_API_KEY, "legion_test_division_4")


def get_tournaments(api_key):
    res = requests.get(
        f"{BASE_URL}/tournaments.json",
        params={"api_key": api_key, "state": "pending,in_progress"},
        headers=HEADERS,
    )
    tournaments = []
    for i in res.json():
        t = i["tournament"]
        tournaments.append(
            {
                # "id": t["id"],
                "name": t["name"],
                "url": t["url"],
                "state": t["state"],
            }
        )
    return tournaments


def get_participants(api_key, tourn_id):
    res = requests.get(
        f"{BASE_URL}/tournaments/{tourn_id}/participants.json",
        params={"api_key": api_key},
        headers=HEADERS,
    )
    return res.json()


def add_participant(api_key, tourn_id, name):
    res = requests.post(
        f"{BASE_URL}/tournaments/{tourn_id}/participants.json",
        params={"api_key": api_key, "participant[name]": name},
        headers=HEADERS,
    )
    print(res.status_code)
    print(res.text)


# add_participant(CHALLONGE_API_KEY, "legion_test_division_4", "testy")


def lambda_handler(event, context):
    logging.debug(json.dumps(event))

    try:
        sub_command = event["data"]["options"][0]["name"]
        if sub_command == "create_participants":
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
