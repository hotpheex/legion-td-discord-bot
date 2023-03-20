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
            name_cell = sheet.find(
                query=name, case_sensitive=False, in_column=column
            )
            if name_cell:
                return sheet.title
        return False

    def get_checked_in_teams(self):
        checked_in_cells = self.worksheet.findall(
            query=CHECKED_IN_MSG, in_column=COLUMNS["team"]["day_1"]
        )

        checked_in_rows = []
        for cell in checked_in_cells:
            if cell.value == CHECKED_IN_MSG:
                checked_in_rows.append(cell.row)
        team_names = self.worksheet.col_values(COLUMNS["team"]["name"])

        checked_in_teams = []
        for row in checked_in_rows:
            checked_in_teams.append(team_names[row - 1])

        return checked_in_teams
