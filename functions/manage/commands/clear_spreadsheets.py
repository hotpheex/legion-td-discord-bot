def clear_spreadsheets(body, gsheet=None, **kwargs):
    if not body["data"]["options"][0]["options"][1]["value"]:
        return "Cancelled"
    gsheet.clear_spreadsheets(body["data"]["options"][0]["options"][0]["value"])
    return f":white_check_mark: Sheets Wiped" 