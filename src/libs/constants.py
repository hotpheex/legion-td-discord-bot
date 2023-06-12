COLUMNS = {
    "team": {
        "name": 2,
        "day_1": 6,
        "day_2": 7,
        "format_range": "A",
    },
    "solo": {
        "name": 9,
        "day_1": 11,
        "format_range": "I",
    },
}
COLORS = {
    "team": {
        "red": 0.414,
        "green": 0.656,
        "blue": 0.309,
    },
    "solo": {
        "red": 0.641,
        "green": 0.756,
        "blue": 0.953,
    },
}
CHECKED_IN_MSG = "Checked In"
SIGNUP_SHEET = "Sign-up"

DIVISIONS = {
    1: {"sheet": "Division 1", "challonge": "June2023NovaCupDivision1"},
    2: {"sheet": "Division 2", "challonge": "June2023NovaCupDivision2"},
    3: {"sheet": "Division 3", "challonge": "June2023NovaCupDivision3"},
    4: {"sheet": "Division 4", "challonge": "June2023NovaCupDivision4"},
    5: {"sheet": "Division 5", "challonge": "June2023NovaCupDivision5"},
}

# Division channels
CHANNEL_IDS = {
    "935115970945613884": DIVISIONS[1]["sheet"],
    "935116002000240680": DIVISIONS[2]["sheet"],
    "935116039400857620": DIVISIONS[3]["sheet"],
    "935116296587202632": DIVISIONS[4]["sheet"],
    "1086241791155650590": DIVISIONS[5]["sheet"],
    "1086242748388098150": "Sign-up",
}
# CHANNEL_IDS["1019583590234849320"] = "Division 5"  # manage-bot channel
CHANNEL_IDS["1023401872750547014"] = "Division 5"  # My bot-test Channel


# Results channels
RESULTS_CHANNEL_IDS = {
    "935117082931109918": DIVISIONS[1]["challonge"],
    "935117112500948992": DIVISIONS[2]["challonge"],
    "935117141592645632": DIVISIONS[3]["challonge"],
    "935117175767830568": DIVISIONS[4]["challonge"],
    "1086241900845076551": DIVISIONS[5]["challonge"],
}
RESULTS_CHANNEL_IDS["1023401872750547014"] = "t68j2e37"  # My bot-test Channel


def get_div_sizes(number_of_teams):
    if number_of_teams > 88:
        div3 = 32
        div4 = 32
    elif number_of_teams > 72:
        div3 = 16
        div4 = 32
    else:
        div3 = 16
        div4 = 16

    return [8, 16, div3, div4, 16]


MAX_TEAMS = 104
