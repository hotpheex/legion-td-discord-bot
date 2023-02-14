import requests
from os import environ

BASE_URL = "https://api.challonge.com/v1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36"
}
CHALLONGE_API_KEY = environ["CHALLONGE_API_KEY"]


def _get_matches(tournament_id):
    res = requests.get(
        f"{BASE_URL}/tournaments/{tournament_id}/matches.json",
        params={"api_key": CHALLONGE_API_KEY},
        headers=HEADERS,
    )
    return res.json()


def _get_participant(tournament_id, participant_id):
    res = requests.get(
        f"{BASE_URL}/tournaments/{tournament_id}/participants/{participant_id}.json",
        params={"api_key": CHALLONGE_API_KEY},
        headers=HEADERS,
    )
    return res.json()


def _get_participants(tournament_id):
    res = requests.get(
        f"{BASE_URL}/tournaments/{tournament_id}/participants.json",
        params={"api_key": CHALLONGE_API_KEY},
        headers=HEADERS,
    )
    return res.json()


def _update_match(tournament_id, match_id, winner_id, scores_csv):
    data = [
        ("api_key", CHALLONGE_API_KEY),
        ("match[winner_id]", winner_id),
        ("match[scores_csv]", scores_csv),
    ]

    res = requests.put(
        f"{BASE_URL}/tournaments/{tournament_id}/matches/{match_id}.json",
        headers=HEADERS,
        data=data,
    )
    return res.json()
