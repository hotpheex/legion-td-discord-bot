from os import environ

import requests

CHALLONGE_API_KEY = environ['CHALLONGE_API_KEY']
BASE_URL = "https://api.challonge.com/v1"
EMAIL = "games@pheex.me"


def bulk_add_participants(tourn_id, participants):
    res = requests.post(f"{BASE_URL}/tournaments/{tourn_id}/participants/bulk_add", auth=(EMAIL, CHALLONGE_API_KEY))
    print(res.status_code)
    print(res.text)

participants = [
    "qwer",
    "asdf",
    "zxcv",
    "erty",
    "dfgh"
]

bulk_add_participants("legion_test_division_4", participants)