import pandas as pd
import numpy as np
from datetime import date
from typing import List
from pulp import LpMaximize, LpProblem, LpStatus, lpSum, LpVariable
from fantasy_football.api import get_all_players
from fantasy_football.predictions import GameweekPredictions
from fantasy_football.data.db_connect import get_query

MAX_BUDGET = 850
MAX_TEAM_MEMBERS = 3
TEAM_SIZE = 11
POSITION_CONSTRAINTS = {'GKP': 1,
                        'DEF': (3, 5),
                        'MID': (2, 5),
                        'FWD': (1, 3)}
TEAM_CONSTRAINTS = {"Arsenal": 3,
                    "Aston Villa": 3,
                    "Brentford": 3,
                    "Brighton": 3,
                    "Burnley": 3,
                    "Chelsea": 3,
                    "Crystal Palace": 3,
                    "Everton": 3,
                    "Leicester": 3,
                    "Leeds": 3,
                    "Liverpool": 3,
                    "Man City": 3,
                    "Man Utd": 3,
                    "Newcastle": 3,
                    "Norwich": 3,
                    "Southampton": 3,
                    "Spurs": 3,
                    "Watford": 3,
                    "West Ham": 3,
                    "Wolves": 3}


POSITION_MAP = {'GKP': 0, 'DEF': 1, 'MID': 2, 'FWD': 3}


def create_player_variables(_df: pd.DataFrame) -> dict:
    all_ids = _df.index.to_list()
    players = {_id: LpVariable(name=f"p{_id}", lowBound=0, upBound=1, cat="Integer") for _id in all_ids}
    return players


def create_objective_function(_df: pd.DataFrame, _players_dict: dict, _target_feature: str = 'ep_next'):
    players_reward = _df.loc[_players_dict.keys()][_target_feature]
    objective_function = lpSum([players_reward.loc[_id] * _players_dict[_id] for _id in _players_dict.keys()])
    return objective_function


def create_team_size_constraint(_df: pd.DataFrame, _players_dict: dict):
    all_ids = _df.index.to_list()
    team_size_constraint = (lpSum([_players_dict[_id] for _id in all_ids]) == TEAM_SIZE, f"team_size_constraint")
    return team_size_constraint


def create_budget_constraint(_df: pd.DataFrame, _players_dict: dict, _budget: int = MAX_BUDGET, **kwargs):
    players_cost = _df.loc[_players_dict.keys()]['now_cost']
    budget_constraint = (lpSum([players_cost.loc[_id] * _players_dict[_id] for _id in _players_dict.keys()]) <= _budget, "budget_constraint")
    return budget_constraint


def create_team_constraint(_df: pd.DataFrame, _players_dict: dict, _team: str, _team_limit_dict: dict = TEAM_CONSTRAINTS, **kwargs):
    team_ids = np.array(_df.query(f"team == '{_team}'").index)
    team_constraint = (lpSum([_players_dict[_id] for _id in team_ids]) <= _team_limit_dict[_team], f"{_team}_constraint")
    return team_constraint


def create_position_constraint(_df: pd.DataFrame, _players_dict: dict, _position: str, _pos_limit_dict: dict = POSITION_CONSTRAINTS, **kwargs):
    position_ids = np.array(_df.query(f"position == '{_position}'").index)
    if _position == 'GKP':
        position_constraint = (lpSum([_players_dict[_id] for _id in position_ids]) == _pos_limit_dict[_position], f"{_position}_constraint")
        return [position_constraint]
    elif _position in ['DEF', 'MID', 'FWD']:
        min_position_constraint = (lpSum([_players_dict[_id] for _id in position_ids]) >= _pos_limit_dict[_position][0], f"min_{_position}_constraint")
        max_position_constraint = (lpSum([_players_dict[_id] for _id in position_ids]) <= _pos_limit_dict[_position][1], f"max_{_position}_constraint")
        return [min_position_constraint, max_position_constraint]


def create_must_haves_constraint(_players_dict: dict, _must_haves_ids: List[int],  **kwargs):
    must_haves_contraint = (lpSum([_players_dict[_id] for _id in _must_haves_ids]) == len(_must_haves_ids), f"must_haves_constraint")
    return must_haves_contraint


def create_must_avoid_constraint(_players_dict: dict, _must_avoid_ids: List[int],  **kwargs):
    must_avoid_contraint = (lpSum([_players_dict[_id] for _id in _must_avoid_ids]) == 0, f"must_avoid_constraint")
    return must_avoid_contraint



def create_model(_df: pd.DataFrame, _target_feature: str, **kwargs):
    players_dict = create_player_variables(_df)
    # objective
    objective_function = create_objective_function(_df, players_dict, _target_feature)
    # team_size
    team_size_constraint = create_team_size_constraint(_df, players_dict)
    # budget
    budget_constraint = create_budget_constraint(_df, players_dict, **kwargs)
    # max players from each team
    teams_constraint_list = []
    teams = _df['team'].unique()
    for team in teams:
        teams_constraint_list.append(create_team_constraint(_df, players_dict, team, **kwargs))
    # position constraints
    position_constraint_list = []
    positions = _df['position'].unique()
    for position in positions:
        position_constraint_list += create_position_constraint(_df, players_dict, position, **kwargs)
    
    # creating model
    model = LpProblem(name="Optimal_FPL_team", sense=LpMaximize)
    model += objective_function
    model += team_size_constraint
    model += budget_constraint
    for constraint in teams_constraint_list:
        model += constraint
    for constraint in position_constraint_list:
        model += constraint

    # the must-have and must-avoid players
    if "_must_haves_ids" in kwargs.keys():
        must_haves_constraint = create_must_haves_constraint(players_dict, **kwargs)
        model += must_haves_constraint
    if "_must_avoid_ids" in kwargs.keys():
        must_avoid_contraint = create_must_avoid_constraint(players_dict, **kwargs)
        model += must_avoid_contraint

    return model


def run_optimization(_target_feature: str, data_source: str = 'api', optimization_date: date = date.today(), **kwargs) -> pd.DataFrame:
    if data_source == 'api':
        all_players = get_all_players(**kwargs)
    elif data_source == 'database': 
        all_players = get_query(f"SELECT * FROM players WHERE date = '{optimization_date}'")
    cols_to_display = ['first_name', 'second_name', 'position', 'team', 'ep_next', 'now_cost', 'total_points', 'selected_by_percent']

    model = create_model(all_players, _target_feature, **kwargs)
    model.solve()
    objective_value = model.objective.value()
    print(f"Status: {model.status}, {LpStatus[model.status]}")
    print(f"Objective: {objective_value}")
    
    player_ids = []
    for var in model.variables():
        if var.value() != 0.0:
            player_ids.append(int(var.name[1:]))
    
    final_team = all_players.loc[player_ids][cols_to_display]
    final_team.sort_values(by='position', key=lambda x: x.map(POSITION_MAP), inplace=True)
    team_cost = np.sum(final_team['now_cost'])
    print(f"Cost: {team_cost}")
    return final_team, objective_value, team_cost
    

if __name__ == '__main__':
    target = 'ep_next'
    pos_dict = {'GKP': 1,
                'DEF': (3, 5),
                'MID': (2, 5),
                'FWD': (1, 3)}
    team_dict = {"Arsenal": 3,
                 "Aston Villa": 3,
                 "Brentford": 3,
                 "Brighton": 3,
                 "Burnley": 3,
                 "Chelsea": 3,
                 "Crystal Palace": 3,
                 "Everton": 3,
                 "Leicester": 3,
                 "Leeds": 3,
                 "Liverpool": 3,
                 "Man City": 3,
                 "Man Utd": 3,
                 "Newcastle": 3,
                 "Norwich": 3,
                 "Southampton": 3,
                 "Spurs": 3,
                 "Watford": 3,
                 "West Ham": 2,
                 "Wolves": 3}
    final_team, _, _ = run_optimization(target, _pos_limit_dict=pos_dict, _team_limit_dict=team_dict)
    print(final_team)