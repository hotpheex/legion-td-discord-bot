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


print(bot_key)

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
        ],
    }
    # {
    #     "name": "challonge",
    #     "description": "Challonge Commands",
    #     "dm_permission": False,
    #     "options": [
    #         {
    #             "name": "create_participants",
    #             "description": "Create Participants in Bracket",
    #             "type": 1,
    #         },
    #     ],
    # },
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
#     f"https://discord.com/api/v8/applications/{bot_id}/commands/1018746318740537365"
# )