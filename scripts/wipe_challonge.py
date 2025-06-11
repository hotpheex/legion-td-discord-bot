#!/usr/bin/python3
import os

import requests

# from ..src.libs.constants import *

CHALLONGE_API_KEY = os.environ["CHALLONGE_API_KEY"]
BASE_URL = "https://api.challonge.com/v1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36"
}

DIVISIONS = {
    1: {"sheet": "Division 1", "challonge": "t68j2e37"},
    2: {"sheet": "Division 2", "challonge": "v9uncccy"},
    3: {"sheet": "Division 3", "challonge": "tf66zw7g"},
    4: {"sheet": "Division 4", "challonge": "1apsosx6"},
    5: {"sheet": "Division 5", "challonge": "iamltixa"},
}

for i in range(1, 6):
    tournament_id = DIVISIONS[i]["challonge"]

    # try:
    #     print(f"resetting {tournament_id}")
    #     res = requests.post(
    #         f"{BASE_URL}/tournaments/{tournament_id}/reset.json",
    #         # params={"api_key": CHALLONGE_API_KEY},
    #         headers=HEADERS,
    #         data=[
    #             ("api_key", CHALLONGE_API_KEY),
    #             ("include_participants", 0),
    #             ("include_matches", 0),
    #         ],
    #     )
    #     res.raise_for_status()
    #     results = res.json()
    # except Exception as err:
    #     print(err)

    try:
        print(f"clearing {tournament_id}")
        res = requests.delete(
            f"{BASE_URL}/tournaments/{tournament_id}/participants/clear.json",
            params={"api_key": CHALLONGE_API_KEY},
            headers=HEADERS,
        )
        res.raise_for_status()
        results = res.json()
        print(results)
    except Exception as err:
        print(err)
