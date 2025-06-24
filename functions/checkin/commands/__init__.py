# Command registry for checkin subcommands

from commands.team_checkin import team_checkin
from commands.solo_checkin import solo_checkin

COMMAND_REGISTRY = {
    "team": team_checkin,
    "solo": solo_checkin,
} 