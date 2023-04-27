import json
import base64
import gspread

from libs.constants import *


class GoogleSheet:
    def __init__(self, api_key, document_id, worksheet_id):
        creds = json.loads(base64.b64decode(api_key).decode("utf-8"))
        gc = gspread.service_account_from_dict(
            creds, client_factory=gspread.BackoffClient
        )
        self.document = gc.open_by_key(document_id)
        self.worksheet = self.document.worksheet(worksheet_id)

    def search_player_all_divs(self, name, column):
        worksheets = self.document.worksheets()
        for sheet in worksheets:
            name_cell = sheet.find(query=name, case_sensitive=False, in_column=column)
            if name_cell:
                return sheet.title
        return False

    def get_all_checkins(self):
        all_records = self.worksheet.get_values()

        checked_in_solos = []
        for row in all_records:
            if row[10] == CHECKED_IN_MSG:
                solo = {
                    "player": row[8],
                    "rating": round(float(row[9])),
                }
                if solo not in checked_in_solos:
                    checked_in_solos.append(solo)

        checked_in_teams = []
        for row in all_records:
            if row[5] == CHECKED_IN_MSG:
                team = {
                    "team": row[1],
                    "player_1": row[2],
                    "player_2": row[3],
                    "rating": round(float(row[4])),
                }
                if team not in checked_in_teams:
                    checked_in_teams.append(team)

        return checked_in_teams, checked_in_solos

    def write_teams_to_div_sheets(self, divisions):
        for i in range(len(divisions)):
            updates = []
            for o in range(len(divisions[i])):
                team = divisions[i][o]
                updates.append(
                    {
                        "range": f"B{o+2}:F{o+2}",
                        "values": [
                            [
                                team["team"],
                                team["player_1"],
                                team["player_2"],
                                team["rating"],
                                CHECKED_IN_MSG,
                            ]
                        ],
                    }
                )

            self.document.worksheet(DIVISIONS[i + 1]["sheet"]).batch_update(updates)

        return True
