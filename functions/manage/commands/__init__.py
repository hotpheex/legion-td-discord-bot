# Command registry for manage subcommands

from commands.checkin_status import checkin_status
from commands.checkin_enabled import checkin_enabled
from commands.calculate_seed import calculate_seed
from commands.clear_spreadsheets import clear_spreadsheets
from commands.sort_signups import sort_signups
from commands.discord_alert import discord_alert

COMMAND_REGISTRY = {
    "checkin_status": checkin_status,
    "checkin_enabled": checkin_enabled,
    "calculate_seed": calculate_seed,
    "clear_spreadsheets": clear_spreadsheets,
    "sort_signups": sort_signups,
    "discord_alert": discord_alert,
} 