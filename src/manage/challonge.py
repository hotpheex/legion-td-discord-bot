import json
import logging
from os import environ
from base64 import b64decode

import requests
import gspread

from constants import *

logging.getLogger().setLevel(logging.DEBUG)

APPLICATION_ID = environ["APPLICATION_ID"]
GOOGLE_API_KEY = environ["GOOGLE_API_KEY"]
GOOGLE_SHEET_ID = environ["GOOGLE_SHEET_ID"]
BASE_URL = "https://api.challonge.com/v1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36"
}
CHALLONGE_API_KEY = environ["CHALLONGE_API_KEY"]


"""API Calls"""


def _get_tournament(tournament_id):
    res = requests.get(
        f"{BASE_URL}/tournaments/{tournament_id}.json",
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


def _add_bulk_participant(tournament_id, names):
    data = [
        ("api_key", CHALLONGE_API_KEY),
    ]
    for name in names:
        data.append(("participants[][name]", name))

    res = requests.post(
        f"{BASE_URL}/tournaments/{tournament_id}/participants/bulk_add.json",
        data=data,
        headers=HEADERS,
    )

    return res.json()


"""Challonge Commands"""


def get_checked_in_teams(division):
    gcreds = json.loads(b64decode(GOOGLE_API_KEY).decode("utf-8"))
    gc = gspread.service_account_from_dict(gcreds, client_factory=gspread.BackoffClient)
    sh = gc.open_by_key(GOOGLE_SHEET_ID)
    ws = sh.worksheet(division)

    checked_in_cells = ws.findall(
        query=CHECKED_IN_MSG, in_column=COLUMNS["team"]["day_1"]
    )

    checked_in_rows = []
    for cell in checked_in_cells:
        if cell.value == CHECKED_IN_MSG:
            checked_in_rows.append(cell.row)
    team_names = ws.col_values(COLUMNS["team"]["name"])

    checked_in_teams = []
    for row in checked_in_rows:
        checked_in_teams.append(team_names[row - 1])

    return checked_in_teams


def update_bracket(event):
    for i in event["data"]["options"][0]["options"]:
        if i["name"] == "tournament_id":
            tournament_id = i["value"]
        if i["name"] == "division":
            division = i["value"]

    tournament = _get_tournament(tournament_id)

    if "tournament" not in tournament:
        return f":no_entry: Tournament with URL `{tournament_id}` not found"

    checked_in_teams = get_checked_in_teams(division)

    existing_participants = _get_participants(tournament_id)
    existing_participant_names = []
    if existing_participants:
        for participant in existing_participants:
            existing_participant_names.append(participant["participant"]["name"])

    participants = []
    for team in checked_in_teams:
        if team not in existing_participant_names:
            participants.append(team)

    result = _add_bulk_participant(tournament_id, participants)
    if "errors" not in result:
        return f":white_check_mark: Tournament `{tournament_id}` participants updated"
    else:
        return f":no_entry: Failed to update Tournament `{tournament_id}`: `{json.dumps(result)}`"
