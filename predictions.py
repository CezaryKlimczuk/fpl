import os
import yaml
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Iterable, Tuple
from scipy.stats import poisson
from fantasy_football.statistical_utils import get_goal_data, bivariate_poisson_sum, calculate_odds
from fantasy_football.api import get_all_players, get_fixtures


HALF_SEASON = 19
KAPPA = 1


class MatchPrediction:
    def __init__(self, home_team: str, away_team: str, kappa: float = KAPPA):
        self.home_team = home_team
        self.away_team = away_team

        goal_dict = get_goal_data()
        df_home_goals = pd.DataFrame(goal_dict['home'])
        df_away_goals = pd.DataFrame(goal_dict['away'])

        avg_scored_home = df_home_goals['scored'].mean()
        avg_lost_home = df_home_goals['lost'].mean()
        avg_scored_away = df_away_goals['scored'].mean()
        avg_lost_away = df_away_goals['lost'].mean()

        self.home_offensive_str = (df_home_goals.loc[home_team]['scored'] / avg_scored_home) ** kappa
        self.home_defensive_str = (df_home_goals.loc[home_team]['lost'] / avg_lost_home) ** kappa
        self.away_offensive_str = (df_away_goals.loc[away_team]['scored'] / avg_scored_away) ** kappa
        self.away_defensive_str = (df_away_goals.loc[away_team]['lost'] / avg_lost_away) ** kappa

        self.home_xg = avg_scored_home * self.home_offensive_str * self.away_defensive_str / HALF_SEASON
        self.away_xg = avg_scored_away * self.away_offensive_str * self.home_defensive_str / HALF_SEASON

        self.outcome_probs = None
        self.clean_sheet_probs = None
        self.implied_odds = None

    def get_xg(self):
        return self.home_xg, self.away_xg

    def get_outcome_probs(self):
        if self.outcome_probs is None:
            self.outcome_probs = bivariate_poisson_sum(self.home_xg, self.away_xg)
        return self.outcome_probs

    def get_clean_sheet_probs(self):
        if self.clean_sheet_probs is None:
            # home cleansheet is given by away_xg and vice versa !!!!
            self.clean_sheet_probs = poisson.pmf(0, self.away_xg), poisson.pmf(0, self.home_xg)
        return self.clean_sheet_probs

    def get_implied_odds(self):
        if self.implied_odds is None:
            if self.outcome_probs is None:
                self.get_outcome_probs()
            self.implied_odds = calculate_odds(self.outcome_probs)
        return self.implied_odds


def calculate_expected_points(player_info: pd.Series) -> float:
    position, prob_playing, ex_goals, ex_assists, cleansheet_prob = player_info
    if position == 'GKP':
        ex_score = 4 * cleansheet_prob + 2 
    elif position == 'DEF':
        ex_score = 6 * ex_goals + 3 * ex_assists + 4 * cleansheet_prob + 2
    elif position == 'MID':
        ex_score = 5 * ex_goals + 3 * ex_assists + 1 * cleansheet_prob + 2
    elif position == 'FWD':
        ex_score = 4 * ex_goals + 3 * ex_assists + 2
    return ex_score * prob_playing


class GameweekPredictions:
    def __init__(self, gameweek: int) -> None:
        self.gameweek = gameweek
        self.fixtures = get_fixtures().query(f"event == {self.gameweek}")
        self.players = get_all_players()
        self.xg_dict = None
        self.cs_dict = None
        self.total_goals_dict = None
        self.total_assists_dict = None

    def predict_xg_and_cs(self):
        self.fixtures['home_xg'], self.fixtures['away_xg'] = zip(*self.fixtures[['team_h', 'team_a']].apply(lambda x: MatchPrediction(x[0], x[1]).get_xg(), axis=1))
        self.fixtures['home_cs_prob'], self.fixtures['away_cs_prob'] = zip(*self.fixtures[['team_h', 'team_a']].apply(lambda x: MatchPrediction(x[0], x[1]).get_clean_sheet_probs(), axis=1))

    def get_xg_dict(self) -> dict:
        if self.xg_dict is None:
            self.xg_dict = dict(zip(list(self.fixtures['team_h']) + list(self.fixtures['team_a']), list(self.fixtures['home_xg']) + list(self.fixtures['away_xg'])))
        return self.xg_dict

    def get_cs_prob_dict(self) -> dict:
        if self.cs_dict is None:
            self.cs_dict = dict(zip(list(self.fixtures['team_h']) + list(self.fixtures['team_a']), list(self.fixtures['home_cs_prob']) + list(self.fixtures['away_cs_prob'])))
        return self.cs_dict

    def get_goals_dict(self) -> dict:
        if self.total_goals_dict is None:
            self.total_goals_dict = self.players.groupby('team').sum()['goals_scored'].clip(lower=1).to_dict()
        return self.total_goals_dict

    def get_assists_dict(self) -> dict:
        if self.total_assists_dict is None:
            self.total_assists_dict = self.players.groupby('team').sum()['assists'].clip(lower=1).to_dict()
        return self.total_assists_dict

    def map_expected_points(self):
        # mapping teams' expected goals and cleansheet probilities, and aggregated data
        self.players['team_xg'] =  self.players['team'].apply(lambda x: self.get_xg_dict()[x])
        self.players['team_cs_prob'] =  self.players['team'].apply(lambda x: self.get_cs_prob_dict()[x])
        self.players['team_total_goals'] =  self.players['team'].apply(lambda x: self.get_goals_dict()[x])
        self.players['team_total_assists'] =  self.players['team'].apply(lambda x: self.get_assists_dict()[x])

        # calculating players' impact on goals, assists
        self.players['goal_share_flat'] = self.players['goals_scored'] / self.players['team_total_goals']
        self.players['goal_share_adj'] = self.players['goals_scored'] ** 2 / self.players['team_total_goals'] ** 2
        self.players['assist_share_flat'] = self.players['goals_scored'] / self.players['team_total_assists']
        self.players['assist_share_adj'] = self.players['goals_scored'] ** 2 / self.players['team_total_assists'] ** 2
        self.players['expected_goals'], self.players['expected_assists'] = self.players['team_xg'] * self.players['goal_share_adj'], self.players['team_xg'] / 2 * self.players['assist_share_adj']

        # Estimating probability of appearance
        self.players['chance_of_playing_next_round'] = self.players['chance_of_playing_next_round'].fillna(100)
        self.players['prob_playing'] = (self.players['minutes'] / 2500).clip(upper=1) * self.players['chance_of_playing_next_round'] / 100

        # calculating expected points based on given metrics
        self.players['expected_points'] = self.players[['position', 'prob_playing', 'expected_goals', 'expected_assists', 'team_cs_prob']].apply(calculate_expected_points, axis=1)


if __name__ == '__main__':
    pass