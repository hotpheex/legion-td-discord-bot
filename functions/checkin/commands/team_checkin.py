"""
Team checkin command
"""

import logging
from libs.constants import CHANNEL_IDS, COLUMNS, COLORS, CHECKED_IN_MSG, SIGNUP_SHEET

logger = logging.getLogger(__name__)


def team_checkin(event, context, discord_client, logger, additional_clients, additional_config):
    """Handle team checkin command"""
    
    # Extract data from event
    discord_event = event.get("discord_event", {})
    data = discord_event.get("data", {})
    member = discord_event.get("member", {})
    channel_id = discord_event.get("channel_id")
    
    # Get player name from member
    player_name = member.get("nick")
    if not player_name:
        player_name = member.get("user", {}).get("global_name")
    if not player_name:
        player_name = member.get("user", {}).get("username")
    
    # Get team name from command options
    options = data.get("options", [])
    if not options:
        return ":no_entry: Missing team name"
    
    team_name = options[0].get("value")
    if not team_name:
        return ":no_entry: Missing team name"
    
    # Get checkin status
    client = additional_clients["client"]
    checkin_status_param = additional_config["CHECKIN_STATUS_PARAM"]
    response = client.get_parameter(Name=checkin_status_param)
    checkin_status = response["Parameter"]["Value"]
    
    if checkin_status == "disabled":
        return ":no_entry: Tournament checkins are not currently open"
    
    # Determine which sheet to use based on checkin status and channel
    if checkin_status == "day_2":
        if CHANNEL_IDS.get(channel_id) == "Sign-up":
            return ":no_entry: Please use the appropriate #division-x channel on Day 2"
        gsheet = additional_clients["gsheet"]
        gsheet.worksheet = gsheet.spreadsheet.worksheet(CHANNEL_IDS[channel_id])
    else:
        gsheet = additional_clients["gsheet"]
    
    query_column = COLUMNS["team"]["name"]
    query_name = team_name
    
    # Find Name Cell
    name_cell = gsheet.worksheet.find(
        query=query_name, case_sensitive=False, in_column=query_column
    )
    if not name_cell:
        return f":no_entry: `{query_name}` not found in the `{CHANNEL_IDS.get(channel_id, 'Sign-up')}` sheet\nPlease make sure your Discord nickname matches your in game name"
    
    # Check if player is on the team
    if not gsheet.worksheet.find(
        query=player_name, case_sensitive=False, in_row=name_cell.row
    ):
        return f":no_entry: Player `{player_name}` is not on team `{team_name}`\nPlease make sure your Discord nickname matches your in game name"
    
    # Check if already checked in
    status_cell = gsheet.worksheet.cell(
        name_cell.row, COLUMNS["team"][checkin_status]
    )
    if status_cell.value == CHECKED_IN_MSG:
        return f":no_entry: `{query_name}` is already checked in"
    
    # Mark as checked in
    gsheet.worksheet.update_cell(
        name_cell.row, COLUMNS["team"][checkin_status], CHECKED_IN_MSG
    )
    gsheet.worksheet.format(
        f"{COLUMNS['team']['format_range']}{name_cell.row}:{status_cell.address}",
        {"backgroundColor": COLORS["team"]},
    )
    
    return f":white_check_mark: `{query_name}` checked in!" 