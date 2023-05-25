import random
from unittest.mock import MagicMock

import pytest

# from libs.challonge import Challonge
from manage import main


def generate_checkins(num_teams, num_solos):
    teams = []
    for i in range(num_teams):
        team_name = f"Team {i+1}"
        player_1 = f"Player {2*i+1}"
        player_2 = f"Player {2*i+2}"
        rating = random.randint(1400, 2400)
        team = {
            "team": team_name,
            "player_1": player_1,
            "player_2": player_2,
            "rating": rating,
        }
        teams.append(team)

    solos = []
    for i in range(num_solos):
        player = f"Player {2*num_teams+i+1}"
        rating = random.randint(800, 2800)
        solo = {
            "player": player,
            "rating": rating,
        }
        solos.append(solo)

    return teams, solos


def run_generate_divisions(
    i_teams,
    i_solos,
    o_divs_0,
    o_divs_1,
    o_divs_2,
    o_divs_3,
    o_divs_4,
    o_playing_teams,
    o_playing_solos,
    o_excluded_teams,
    o_excluded_solos,
):
    teams, solos = generate_checkins(i_teams, i_solos)
    (
        divisions,
        playing_teams,
        playing_solos,
        excluded_teams,
        excluded_solos,
    ) = main.generate_divisions(teams, solos)

    assert len(divisions[0]) == o_divs_0
    assert len(divisions[1]) == o_divs_1
    assert len(divisions[2]) == o_divs_2
    assert len(divisions[3]) == o_divs_3
    assert len(divisions[4]) == o_divs_4
    assert len(playing_teams) == o_playing_teams
    assert len(playing_solos) == o_playing_solos
    assert len(excluded_teams) == o_excluded_teams
    assert len(excluded_solos) == o_excluded_solos


# class MockGsheet:
#     def __init__(self, num_teams, num_solos):
#         self.num_teams = num_teams
#         self.num_solos = num_solos

#     def get_all_checkins(self):
#         teams, solos = generate_checkins(self.num_teams, self.num_solos)
#         return teams, solos

#     def write_teams_to_div_sheets(self, divisions):
#         return True


# class MockChallonge:
#     def add_participants_to_tournament(self, divisions):
#         return True


# @pytest.fixture(autouse=True)
# def env_setup(monkeypatch):
#     monkeypatch.setenv("CHECKIN_STATUS_PARAM", "a")
#     monkeypatch.setenv("APPLICATION_ID", "b")
#     monkeypatch.setenv("ALERT_WEBHOOK", "c")
#     monkeypatch.setenv("CHALLONGE_API_KEY", "d")
#     monkeypatch.setenv(
#         "GOOGLE_API_KEY",
#         "eyJ0eXBlIjoic2VydmljZV9hY2NvdW50IiwicHJvamVjdF9pZCI6InByb2plY3RfaWQiLCJwcml2YXRlX2tleV9pZCI6ImZkZDhmYWU0MTc1YmU4ZGYwMTlmNTM0NmI2YWNkM2RmYTNjOTQ2OWEiLCJwcml2YXRlX2tleSI6Ii0tLS0tQkVHSU4gUFJJVkFURSBLRVktLS0tLQpNSUlFdkFJQkFEQU5CZ2txaGtpRzl3MEJBUUVGQUFTQ0JLWXdnZ1NpQWdFQUFvSUJBUUQzMEliUWYzazJpMXBpClcza3kvVUJXOGxJZWtjL1VJQ1dmaDFqOXlhaDVaYktnU0NqNXZkeWpVUm90RXNoUzd6a3daSVkwRjlMYS9QSEEKcmdHTjkwZzIrd0EwaWJqSkFqdVloMG8xbTdVY24zeGlQbkRsVHkxZHpFNmFTcFc5ZGtHUDRVdnZGSHgxSVJaUQpTSmRFVkQ4aTBMVkRXd2N3MDZ6Tkh4R3hEMEVwVVVIQk9aRkp3SStVR2Z1ZndVWHNCZkRuZTRjdk9qblJkS1RRCnpFRjc0WG1jeTlMaGtRZVFSbktTRm5FVzhpSHNXRUw5OXVQUUxPa1crTHJIc0dlVXlWbVZMTW5NY01yei9OVTkKMlJIQ2ZmdW83dytBRFdsVmszbVRJV2J2SU4vWEd5NW44elprdTZiWWJ0Z3J0K2dKUVRCdHJ0eks0bDJpWkRpUQplZkhxckpQVkFnTUJBQUVDZ2dFQVJRRlFpeGMvenYwem1qY1M0ZFIzQWUwSWJSZDZPUDAwZ3BZU0QzeFQ5ZmI2CnZ2YzRBc0dIQWZ5aFlnaHFFZEJpM01yd0lzQksxUkVlUktKT1RSaG5FTlRidDkxMzlHWVZMMmFqY29DWTFqejkKT2ZpTTgxanRCQWg5L2FoQVhKYjNkK2N4VlhpUVhIeG1YdzlSVWtKNlRUeWl2NzE5anBQNGpDeTh2SWFvaExTcwpwU1VTWFRYK05EdU50Z1B2VHJKRXVoemtqTzZIWkF5b0c1WGlwRWt3UTRYUjJlTlNTZnpwUG1JTk1lUVd1MHRlCk9PdjlsOTROV3BtQU5qeHVlRFNjYXJmVVFlRmMzS0pHRlZYeG94L2ROMThObzJudGNQaW1RWXU5VHpYY0kvejUKVzlJOWxjeVNXQ0E3amFtZVFvTW9pTThPeVZidmR5RS8zQU9Qb1AyOXBRS0JnUURha1UwcUxMOGROV0dXbXk2cQo1UWtnRERTcGJHYVQ3NzFJcElkMzF5bndMbHdCejNKS1hjUk9GVjJWOGVSWm9FOWFJNzRHV0JwRHpObE1ZbVFZClo0NlZ5aWdINW9JNnU1a2g4L0FhSGNtYkxLaUNuZnRUVEZzQ1VINGF4aERyMVBIT09teG9UdStocVlETzgzajUKRnREZnNqR0pvQUEyQmg3Q3phQisvS084U3dLQmdRRFhTNHE1T24ySkI3N1dCZkIvd2s2WXVndmtsQXRDdHJ0UwpvNk03enRGN1ZkYURNTTJtTXRHRmkwNmlKVHo1WFRaNnFIRDIrL0VyY3FjV0ZDd1RzWmY5UDFDNTdrZmxIZHJOCk5sTzhXb2Ztd0kxTG9JTUQvcENONFJhK3ZrMkhGb2lzYzBtV09CSDJkb3NGN0I2Tm1DTkRuSm5FUDFwNDlUZmUKOGVYREZnU2NYd0tCZ0V0SngrbmlOZ2JxcjI0QWtJZS9rM0FkcERwRUkrV0xySWtNVzdtMVBUWUYwaDJ4aHE0RgpOS3l0QVdxNFF5OTRZRDB0bUxSNHZydGlJZXdFN0hQWG9DOEt6dFZCMnRRK2NOWllQL25QRHZaTDROUDFkWEJSCkdmeG5HN2svUnU3bGtGRzRvRVVpQTd1Tk50aVMxN1g5M1A5aFUxMFQ1MTYwcHYzMWRQYXBNZ0dYQW9HQUxtNTIKVHBoVXRwYmJDMkZnaXMwbkVqMGRqNEIySlQ4dml4VUxnVHlMWlNRUURWOGJHdnJld1FSWVF4UHc0SDYvM3hndwp0TE9GUWErS1pYS1lSdThJTG0vWFF5SW1rejByRVJMa1lEek9EbS84aVJEbThKZVlLV0VmL0tjaUpUNHczN0JGCmNJWkxLWEpMYlUyTkVWQjhXbnFObHd0cXdhZHhFejNzSlhTOExkVUNnWUFNK0hlMUdGUXlPa0ppRDRWS0pKYXUKM2NTT3RETGNYdDdyT2ZBaEVsSmsxK3pWL1RRNjBGTlRoRVgyZ1hMbEpYWjVuRWVsRlBZK0FncDVWYlNEYzFkdgpsV2VVbGtBbjFHUThyNUFHK2hIRy91WmRvQ0ZXMFVJWVFEZ3V5ditJMDhiQnZub29lK0RkK2hJYzZIQ2R5N25aCnVxS1kzUnd6WEdSbk00SjBGcitQOHc9PQotLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tCiIsImNsaWVudF9lbWFpbCI6InRlc3RAdGVzdC5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsImNsaWVudF9pZCI6IjEwNzYxNTY2MzMyOTk4MjkyMjAxNiIsImF1dGhfdXJpIjoiaHR0cHM6Ly9hY2NvdW50cy5nb29nbGUuY29tL28vb2F1dGgyL2F1dGgiLCJ0b2tlbl91cmkiOiJodHRwczovL29hdXRoMi5nb29nbGVhcGlzLmNvbS90b2tlbiIsImF1dGhfcHJvdmlkZXJfeDUwOV9jZXJ0X3VybCI6Imh0dHBzOi8vd3d3Lmdvb2dsZWFwaXMuY29tL29hdXRoMi92MS9jZXJ0cyIsImNsaWVudF94NTA5X2NlcnRfdXJsIjoiaHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vcm9ib3QvdjEvbWV0YWRhdGEveDUwOS90ZXN0LTg1MiU0MHRlc3QuaWFtLmdzZXJ2aWNlYWNjb3VudC5jb20iLCJ1bml2ZXJzZV9kb21haW4iOiJnb29nbGVhcGlzLmNvbSJ9Cg==",
#     )
#     monkeypatch.setenv("GOOGLE_SHEET_ID", "f")
#     monkeypatch.setenv("DEBUG", "true")


def test_calculate_team_seed():
    rating, message = main.calculate_team_seed([2330, 1895])
    assert rating == 2185
    assert message == "Team rating for `[2330, 1895]`: `2185`"


def test_get_checkin_status():
    client = MagicMock()
    client.get_parameter.return_value = {"Parameter": {"Value": "disabled"}}
    status = main.get_checkin_status(client, "a")
    assert status == "disabled"


def test_set_checkin_status_enabled():
    client = MagicMock()
    client.put_parameter.return_value = {}
    event = {
        "data": {
            "options": [
                {
                    "name": "checkin_enabled",
                    "options": [
                        {
                            "name": "checkin_enabled",
                            "value": "day_1",
                        }
                    ],
                }
            ]
        }
    }
    message = main.set_checkin_status(client, event, "a")
    assert message == "Checkins are now set to `day_1`"


def test_divs_leftover_teams():
    run_generate_divisions(
        i_teams=106,
        i_solos=11,
        o_divs_0=8,
        o_divs_1=16,
        o_divs_2=32,
        o_divs_3=32,
        o_divs_4=16,
        o_playing_teams=main.MAX_TEAMS,
        o_playing_solos=0,
        o_excluded_teams=2,
        o_excluded_solos=11,
    )


def test_divs_leftover_solos():
    run_generate_divisions(
        i_teams=90,
        i_solos=35,
        o_divs_0=8,
        o_divs_1=16,
        o_divs_2=32,
        o_divs_3=32,
        o_divs_4=16,
        o_playing_teams=main.MAX_TEAMS,
        o_playing_solos=28,
        o_excluded_teams=0,
        o_excluded_solos=7,
    )


def test_divs_sizes_lt_72_teams():
    run_generate_divisions(
        i_teams=69,
        i_solos=3,
        o_divs_0=8,
        o_divs_1=16,
        o_divs_2=16,
        o_divs_3=14,
        o_divs_4=16,
        o_playing_teams=70,
        o_playing_solos=2,
        o_excluded_teams=0,
        o_excluded_solos=1,
    )


def test_divs_sizes_gt_72_teams():
    run_generate_divisions(
        i_teams=70,
        i_solos=9,
        o_divs_0=8,
        o_divs_1=16,
        o_divs_2=16,
        o_divs_3=18,
        o_divs_4=16,
        o_playing_teams=74,
        o_playing_solos=8,
        o_excluded_teams=0,
        o_excluded_solos=1,
    )


def test_divs_sizes_gt_88_teams():
    run_generate_divisions(
        i_teams=80,
        i_solos=22,
        o_divs_0=8,
        o_divs_1=16,
        o_divs_2=32,
        o_divs_3=19,
        o_divs_4=16,
        o_playing_teams=91,
        o_playing_solos=22,
        o_excluded_teams=0,
        o_excluded_solos=0,
    )
