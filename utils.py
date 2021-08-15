import numpy as np
from fantasy_football.predictions import MatchPrediction


def match_summary(home_team, away_team) -> None:
    match = MatchPrediction(home_team, away_team, kappa=1.3)
    home_xg, away_xg = match.get_xg()
    print(f"Home ({home_team}) xG: {home_xg}")
    print(f"Away ({away_team}) xG: {away_xg}")
    result_probabilites = np.round(match.get_outcome_probs(), 3)
    print("\nOutcome probabilites:")
    print(f"{home_team}: {result_probabilites[0]}")
    print(f"Draw: {result_probabilites[1]}")
    print(f"{away_team}: {result_probabilites[2]}")
    odds = np.round(match.get_implied_odds(), 2)
    print("\nImplied odds:")
    print(list(odds))

if __name__ == '__main__':
    home = 'Man Utd'
    away = 'Leeds'
    match_summary(home, away)


