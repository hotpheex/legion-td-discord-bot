import math

def calculate_seed(body, **kwargs):
    ratings = [
        player["value"]
        for player in body["data"]["options"][0]["options"]
    ]
    team_rating = math.ceil((2 * max(ratings) + min(ratings)) / 3)
    return f"Team rating for `{ratings}`: `{team_rating}`" 