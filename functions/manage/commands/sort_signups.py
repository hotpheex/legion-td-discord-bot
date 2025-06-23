from requests.exceptions import HTTPError
from libs.constants import DIVISIONS, get_div_sizes, MAX_TEAMS, SIGNUP_SHEET

def generate_divisions(teams, solos):
    playing_solos, excluded_teams, excluded_solos = [], [], []
    div_1_size = get_div_sizes(MAX_TEAMS)[0]
    div_2_size = get_div_sizes(MAX_TEAMS)[1]
    playing_teams = sorted(teams, key=lambda x: x["rating"], reverse=True)[
        0 : div_1_size + div_2_size
    ]
    for team in teams:
        if len(playing_teams) == MAX_TEAMS:
            excluded_teams.append(team)
            continue
        if team not in playing_teams:
            playing_teams.append(team)
    if len(playing_teams) < MAX_TEAMS:
        teams_needed = MAX_TEAMS - len(playing_teams)
        for solo in solos:
            if len(playing_solos) < teams_needed * 2:
                playing_solos.append(solo)
            else:
                excluded_solos.append(solo)
        if len(playing_solos) % 2 == 1:
            excluded_solos.append(playing_solos.pop())
        sorted_solos = sorted(playing_solos, key=lambda x: x["rating"], reverse=True)
        for i in range(0, len(sorted_solos), 2):
            p1 = sorted_solos[i]
            p2 = sorted_solos[i + 1]
            team_rating = (2 * max([p1["rating"], p2["rating"]]) + min([p1["rating"], p2["rating"]])) // 3
            playing_teams.append(
                {
                    "team": f"{p1['player']}_{p2['player']}",
                    "player_1": p1["player"],
                    "player_2": p2["player"],
                    "rating": team_rating,
                }
            )
    else:
        excluded_solos = solos
    sorted_teams = sorted(playing_teams, key=lambda x: x["rating"], reverse=True)
    div_sizes = get_div_sizes(len(sorted_teams))
    divisions = []
    team_index = 0
    last_div_index = 0
    for i in range(len(div_sizes)):
        if len(sorted_teams) > sum(div_sizes[0:i]):
            last_div_index = i
    last_div = [sorted_teams[-div_sizes[last_div_index] :]]
    sorted_teams = sorted_teams[: -div_sizes[last_div_index]]
    for i in range(len(div_sizes)):
        divisions.append(sorted_teams[team_index : team_index + div_sizes[i]])
        team_index += div_sizes[i]
    divisions[last_div_index] = last_div[0]
    return (
        divisions,
        playing_teams,
        playing_solos,
        excluded_teams,
        excluded_solos,
    )

def sort_signups(body, gsheet=None, challonge=None, **kwargs):
    if not body["data"]["options"][0]["options"][0]["value"]:
        return "Cancelled"
    missing_challonges = []
    f_missing = []
    for division in DIVISIONS.values():
        tournament = division["challonge"]
        try:
            exists = challonge._get_tournament(tournament)
            if not exists:
                missing_challonges.append(tournament)
        except Exception:
            f_missing = [f"`{challonge}`" for challonge in missing_challonges]
            missing_challonges.append(tournament)
    if missing_challonges:
        return (
            f":no_entry: Tournaments are missing in Challonge: {', '.join(f_missing)}"
        )
    teams, solos = gsheet.get_all_checkins()
    divisions, playing_teams, _, excluded_teams, excluded_solos = generate_divisions(
        teams, solos
    )
    if not gsheet.write_teams_to_div_sheets(divisions):
        return ":warning: Failed to write teams to division sheets or Challonge"
    challonge.add_participants_to_tournament(divisions)
    try:
        challonge.add_participants_to_tournament(divisions)
    except HTTPError:
        return ":warning: Successfully sorted teams but failed to add all teams to Challonge tournaments"
    message = f":white_check_mark: Teams sorted in GSheets and added to Challonge:\n```Team Signups: {len(teams)}\nSolo Signups: {len(solos)}\nTotal Teams Playing: {len(playing_teams)}\n"
    for i in range(len(divisions)):
        message += f"\nDivision {i+1}: {len(divisions[i])}"
    if excluded_teams:
        message += f"\n\nTeams that were excluded:"
        for team in excluded_teams:
            message += f"\n{team['team']}"
    if excluded_solos:
        message += f"\n\nSolo players that were excluded:"
        for solo in excluded_solos:
            message += f"\n{solo['player']}"
    message += "\n```"
    return message 