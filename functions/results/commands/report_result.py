"""
Report result command
"""

import json
import logging
import os
from pathlib import Path
from libs.constants import RESULTS_CHANNEL_IDS

logger = logging.getLogger(__name__)


def find_losing_team_id(participants, id):
    """Find the losing team ID from participants"""
    matching_participants = [
        p
        for p in participants
        if p["participant"]["id"] == id
        or (
            p["participant"]["group_player_ids"]
            and p["participant"]["group_player_ids"][0] == id
        )
    ]
    if matching_participants:
        return matching_participants[0]["participant"]["id"]
    else:
        return None


def report_result(event, context, discord_client, logger, additional_clients, additional_config):
    """Handle result reporting command"""
    
    # Extract data from event
    discord_event = event.get("discord_event", {})
    data = discord_event.get("data", {})
    channel_id = discord_event.get("channel_id")
    
    # Get command options
    options = data.get("options", [])
    if len(options) < 3:
        return ":no_entry: Missing required parameters: winning_team, winning_score, losing_score"
    
    winning_team = options[0].get("value")
    winning_score = int(options[1].get("value"))
    losing_score = int(options[2].get("value"))
    
    # Get tournament ID from channel
    tournament_id = RESULTS_CHANNEL_IDS.get(channel_id)
    if not tournament_id:
        return ":no_entry: This channel is not configured for result reporting"
    
    challonge = additional_clients["challonge"]
    
    # Check if tournament is running
    t = challonge._get_tournament(tournament_id)
    tournament_state = t["tournament"]["state"]
    if tournament_state == "pending":
        return f':no_entry: {t["tournament"]["name"]} has not started yet <https://challonge.com/{tournament_id}>'
    elif tournament_state == "awaiting_review" or tournament_state == "complete":
        return f':no_entry: {t["tournament"]["name"]} has finished'
    
    # Validate scores
    if winning_score <= losing_score:
        return f":no_entry: Winning score `{str(winning_score)}` must be higher than losing score `{str(losing_score)}`"
    
    # Get list of participants for tournament (and cache)
    cache_file = Path(f"/tmp/{tournament_id}.json")
    if cache_file.is_file():
        with open(cache_file, "r") as fh:
            participants = json.load(fh)
    else:
        participants = challonge._get_participants(tournament_id)
        temp_cache_file = Path(f"/tmp/{tournament_id}-{context.aws_request_id}.json")
        with open(temp_cache_file, "w") as fh:
            json.dump(participants, fh)
            fh.flush()
        os.replace(temp_cache_file, cache_file)
    
    logger.debug(json.dumps(participants))
    
    # Find winning team ID
    winning_team_id, winning_team_group_id = None, None
    for p in participants:
        if p["participant"]["name"].lower() == winning_team.lower():
            winning_team_id = p["participant"]["id"]
            winning_team_name = p["participant"]["name"]
            if len(p["participant"]["group_player_ids"]) > 0:
                winning_team_group_id = p["participant"]["group_player_ids"][0]
    
    if not (winning_team_id or winning_team_group_id):
        return f":no_entry: Team `{winning_team}` not found (<https://challonge.com/{tournament_id}>)"
    
    # Get team's latest match
    latest_match, scores_csv = None, None
    matches = challonge._get_matches(tournament_id)
    logger.debug(winning_team_id)
    logger.debug(winning_team_group_id)
    logger.debug(json.dumps(matches))
    
    for m in matches:
        if m["match"]["state"] == "open":
            if (
                m["match"]["player1_id"] == winning_team_id
                or m["match"]["player1_id"] == winning_team_group_id
            ):
                latest_match = m
                scores_csv = str(winning_score) + "-" + str(losing_score)
                losing_team_id = find_losing_team_id(
                    participants, m["match"]["player2_id"]
                )
            elif (
                m["match"]["player2_id"] == winning_team_id
                or m["match"]["player2_id"] == winning_team_group_id
            ):
                latest_match = m
                scores_csv = str(losing_score) + "-" + str(winning_score)
                losing_team_id = find_losing_team_id(
                    participants, m["match"]["player1_id"]
                )
    
    logger.debug(latest_match)
    logger.debug(scores_csv)
    if not latest_match or not scores_csv:
        return f":no_entry: No match in progress for {winning_team_name} (<https://challonge.com/{tournament_id}>)"
    
    # Update match with scores
    if (
        latest_match["match"]["player1_id"] == winning_team_group_id
        or latest_match["match"]["player2_id"] == winning_team_group_id
    ):
        winning_team_id = winning_team_group_id
    challonge._update_match(
        tournament_id, latest_match["match"]["id"], winning_team_id, scores_csv
    )
    
    losing_team = challonge._get_participant(tournament_id, losing_team_id)
    return f":white_check_mark: [Round {latest_match['match']['round']}] `{winning_team_name}` {winning_score}-{losing_score} `{losing_team['participant']['name']}`" 