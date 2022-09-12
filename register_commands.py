##############################################
# Run this script locally to add bot commands
##############################################
import requests
import os

# from dotenv import load_dotenv

# load_dotenv()

API_ENDPOINT = "https://discord.com/api"

bot_id = os.getenv("bot_id")
bot_key = os.getenv("bot_key")


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
                        "description": "True or False",
                        "type": 5,
                        "required": True,
                    }
                ],
            },
            {
                "name": "checkin_status",
                "description": "Current Tournament Checkin Status",
                "type": 1,
            },
        ],
    },
]


def get_oauth_token():
    data = {
        "grant_type": "client_credentials",
        "scope": "identify connections applications.commands.permissions.update",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(
        f"{API_ENDPOINT}/oauth2/token",
        data=data,
        headers=headers,
        auth=(bot_id, bot_key),
    )
    r.raise_for_status()
    return r.json()


headers = {"Authorization": f"Bot {bot_key}"}


def update_commands(url):
    for cmd in commands:
        r = requests.post(url, headers=headers, json=cmd)
        print(r.json())


def get_commands(url):
    r = requests.get(url, headers=headers)

    print(r.json())


def delete_commands(url):
    r = requests.delete(url, headers=headers)

    print(r.json())


# def update_permissions(url):


def get_command_permissions(url):
    r = requests.get(url, headers=headers)
    print(r.status_code)
    print(r.json())


def put_command_permissions(url, perms):
    r = requests.put(url, headers=headers, json=perms)
    print(r.status_code)
    print(r.json())


update_commands(f"https://discord.com/api/v8/applications/{bot_id}/commands")
# get_commands(f"https://discord.com/api/v8/applications/{bot_id}/commands")
# delete_commands(
#     f"https://discord.com/api/v8/applications/{bot_id}/commands/795912485793431583")

guild_id = "755422118719520827"
command_id = "1018746318740537365"
test_role = "1018757033329176709"

# put_command_permissions(
#     f"https://discord.com/api/v8/applications/{bot_id}/guilds/{guild_id}/commands/{command_id}/permissions",
#     {
#         # "id": command_id,
#         "permissions": [{"id": test_role, "type": 1, "permission": True}],
#     },
# )

# get_command_permissions(
#     f"https://discord.com/api/v8/applications/{bot_id}/guilds/{guild_id}/commands/permissions"
# )
