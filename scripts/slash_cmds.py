##############################################
# Run this script locally to add bot commands
##############################################
import json
import os
import sys

import requests

args = sys.argv
if len(args) < 2 or (args[1] not in ["dev", "prod"]):
    raise SystemExit("python3 register_commands.py <dev | prod>")
else:
    env = args[1]

API_ENDPOINT = "https://discord.com/api"

bot_id = os.getenv(f"bot_id_{env}")
bot_key = os.getenv(f"bot_key_{env}")


commands = [
    {
        "name": "checkin",
        "description": "Checkin to a Tournament",
        "dm_permission": False,
        "options": [
            {
                "name": "team",
                "description": "Team Checkin",
                "type": 1,
                "options": [
                    {
                        "name": "name",
                        "description": "Name of a Team",
                        "type": 3,
                        "required": True,
                    }
                ],
            },
            {"name": "solo", "description": "Solo Checkin", "type": 1},
        ],
    },
    {
        "name": "manage",
        "description": "Tournament admin commands",
        "dm_permission": False,
        "options": [
            {
                "name": "checkin_enabled",
                "description": "Enable/Disable Tournament Checkins",
                "type": 1,
                "options": [
                    {
                        "name": "enabled",
                        "description": "Choose an option",
                        "type": 3,
                        "required": True,
                        "choices": [
                            {"name": "Day 1", "value": "day_1"},
                            {"name": "Day 2", "value": "day_2"},
                            {"name": "Disabled", "value": "disabled"},
                        ],
                    }
                ],
            },
            {
                "name": "checkin_status",
                "description": "Current Tournament Checkin Status",
                "type": 1,
            },
            # {
            #     "name": "update_bracket",
            #     "description": "Update participants in a bracket",
            #     "type": 1,
            #     "options": [
            #         {
            #             "name": "tournament_id",
            #             "description": "Tournament URL / ID",
            #             "type": 3,
            #             "required": True,
            #         },
            #         {
            #             "name": "division",
            #             "description": "Choose a Division",
            #             "type": 3,
            #             "required": True,
            #             "choices": [
            #                 {"name": "Division 1", "value": "Division 1"},
            #                 {"name": "Division 2", "value": "Division 2"},
            #                 {"name": "Division 3", "value": "Division 3"},
            #                 {"name": "Division 4", "value": "Division 4"},
            #             ],
            #         },
            #     ],
            # },
            {
                "name": "calculate_seed",
                "description": "Calculate a Team Seed for two players",
                "type": 1,
                "options": [
                    {
                        "name": "player_1",
                        "description": "Player 1",
                        "type": 4,
                        "required": True,
                    },
                    {
                        "name": "player_2",
                        "description": "Player 2",
                        "type": 4,
                        "required": True,
                    },
                ],
            },
            {
                "name": "sort_signups",
                "description": "Sort checked-in signups into Divisions",
                "type": 1,
                "options": [
                    {
                        "name": "confirm",
                        "description": "Are you sure?",
                        "type": 5,
                        "required": True,
                    }
                ],
            },
        ],
    },
    {
        "name": "results",
        "description": "Report results for a match",
        "dm_permission": False,
        "options": [
            {
                "name": "winning_team",
                "description": "Winning team name",
                "type": 3,
                "required": True,
            },
            {
                "name": "winning_score",
                "description": "Score of winning team",
                "type": 4,
                "required": True,
            },
            {
                "name": "losing_score",
                "description": "Score of losing team",
                "type": 4,
                "required": True,
            },
        ],
    },
]


headers = {"Authorization": f"Bot {bot_key}"}


def update_commands(url):
    for cmd in commands:
        r = requests.post(url, headers=headers, json=cmd)
        print(r.content.decode("utf-8"))


def get_commands(url):
    r = requests.get(url, headers=headers)

    cmds = r.json()
    for cmd in cmds:
        print(json.dumps(cmd))


def delete_commands(url):
    r = requests.delete(url, headers=headers)

    print(r.content)


update_commands(f"https://discord.com/api/v8/applications/{bot_id}/commands")
# get_commands(f"https://discord.com/api/v8/applications/{bot_id}/commands")
# delete_commands(
#     f"https://discord.com/api/v8/applications/{bot_id}/commands/1033232910590947418"
# )
