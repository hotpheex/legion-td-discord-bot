from os import environ
import requests
import json


BASE_URL = "https://api.challonge.com/v1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36"
}
CHALLONGE_API_KEY = environ["CHALLONGE_API_KEY"]


def create_tournament(name, url, type):
    res = requests.post(
        f"{BASE_URL}/tournaments.json",
        params={
            "api_key": CHALLONGE_API_KEY,
            "tournament[name]": name,
            "tournament[url]": url,
            "tournament[tournament_type]": type,
            # "tournamen[game_id]": 128909,
        },
        headers=HEADERS,
    )

    print(json.dumps(res.json(), indent=2))


def get_tournaments():
    res = requests.get(
        f"{BASE_URL}/tournaments.json",
        params={"api_key": CHALLONGE_API_KEY, "state": "pending,in_progress"},
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


def get_participants(tourn_id):
    res = requests.get(
        f"{BASE_URL}/tournaments/{tourn_id}/participants.json",
        params={"api_key": CHALLONGE_API_KEY},
        headers=HEADERS,
    )
    return res.json()


def add_participant(tourn_id, name):
    res = requests.post(
        f"{BASE_URL}/tournaments/{tourn_id}/participants.json",
        params={
            "api_key": CHALLONGE_API_KEY,
            "participant[name]": "qwerqwer",
        },
        headers=HEADERS,
    )


def add_bulk_participant(tourn_id, names):
    data = [
        ("api_key", CHALLONGE_API_KEY),
    ]
    for player in names:
        data.append(("participants[][name]", player))

    res = requests.post(
        f"{BASE_URL}/tournaments/{tourn_id}/participants/bulk_add.json",
        data=data,
        headers=HEADERS,
    )

    return True
