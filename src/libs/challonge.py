import requests

from libs.constants import *


class Challonge:
    def __init__(self, api_key):
        self.base_url = "https://api.challonge.com/v1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36"
        }
        self.api_key = api_key

    def _get_tournament(self, tournament_id):
        res = requests.get(
            f"{self.base_url}/tournaments/{tournament_id}.json",
            params={"api_key": self.api_key},
            headers=self.headers,
        )
        res.raise_for_status()
        results = res.json()
        if "tournament" not in results:
            raise Exception("Tournament with URL `{tournament_id}` not found")
        return results

    def _get_matches(self, tournament_id):
        res = requests.get(
            f"{self.base_url}/tournaments/{tournament_id}/matches.json",
            params={"api_key": self.api_key},
            headers=self.headers,
        )
        res.raise_for_status()
        return res.json()

    def _update_match(self, tournament_id, match_id, winner_id, scores_csv):
        data = [
            ("api_key", self.api_key),
            ("match[winner_id]", winner_id),
            ("match[scores_csv]", scores_csv),
        ]

        res = requests.put(
            f"{self.base_url}/tournaments/{tournament_id}/matches/{match_id}.json",
            headers=self.headers,
            data=data,
        )
        res.raise_for_status()
        return res.json()

    def _get_participant(self, tournament_id, participant_id):
        res = requests.get(
            f"{self.base_url}/tournaments/{tournament_id}/participants/{participant_id}.json",
            params={"api_key": self.api_key},
            headers=self.headers,
        )
        res.raise_for_status()
        return res.json()

    def _get_participants(self, tournament_id):
        res = requests.get(
            f"{self.base_url}/tournaments/{tournament_id}/participants.json",
            params={"api_key": self.api_key},
            headers=self.headers,
        )
        res.raise_for_status()
        return res.json()

    def _add_bulk_participant(self, tournament_id, names):
        data = [
            ("api_key", self.api_key),
        ]
        for name in names:
            data.append(("participants[][name]", name))

        res = requests.post(
            f"{self.base_url}/tournaments/{tournament_id}/participants/bulk_add.json",
            data=data,
            headers=self.headers,
        )
        res.raise_for_status()
        print(res.text)
        return res.json()

    def add_participants_to_tournament(self, divisions):
        for i in range(len(divisions)):
            tournament_id = DIVISIONS[i + 1]["challonge"]
            self._get_tournament(DIVISIONS[i + 1]["challonge"])

            existing_participants = self._get_participants(tournament_id)
            existing_participant_names = []
            if existing_participants:
                for participant in existing_participants:
                    existing_participant_names.append(
                        participant["participant"]["name"]
                    )

            new_participants = []
            for team in divisions[i]:
                if team["team"] not in existing_participant_names:
                    new_participants.append(team["team"])

            if new_participants:
                self._add_bulk_participant(tournament_id, new_participants)

        return None
