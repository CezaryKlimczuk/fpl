"""
This module provides function to query data in an approachable way from FPL endpoints
"""
import os
import yaml
import requests
import pandas as pd
from datetime import date
from pathlib import Path

STATIC_ENDPOINT = "https://fantasy.premierleague.com/api/bootstrap-static/"
FIXTURES_ENDPOINT = "https://fantasy.premierleague.com/api/fixtures/"
CONFIG_PATH = Path(os.path.abspath(__file__)).parent / "config"

with open(CONFIG_PATH / "team_dict.yaml") as f:
    TEAM_DICT = yaml.safe_load(f)
    f.close()
with open(CONFIG_PATH / "positions_dict.yaml") as f:
    POSITION_DICT = yaml.safe_load(f)
    f.close()


def get_all_players() -> pd.DataFrame:
    response = requests.get(STATIC_ENDPOINT).json()
    players = pd.DataFrame(response['elements'])
    players['team'] = players['team'].apply(lambda x: TEAM_DICT[x])
    players['position'] = players['element_type'].apply(lambda x: POSITION_DICT[x])
    players.drop(columns=['element_type'], inplace=True)
    for col in players.columns:
        players[col] = pd.to_numeric(players[col], errors='ignore')
    players.set_index('id', inplace=True)
    players['date'] = date.today()
    players =  players[['date'] + list(players.columns[:-1])]
    return players


def get_player_history(_id: int) -> pd.DataFrame:
    response = requests.get(f"https://fantasy.premierleague.com/api/element-summary/{_id}/").json()
    player_hist = pd.DataFrame(response['history_past'])
    for col in player_hist.columns:
        player_hist[col] = pd.to_numeric(player_hist[col], errors='ignore')
    return player_hist


def get_teams() -> pd.DataFrame:
    response = requests.get(STATIC_ENDPOINT).json()
    teams = pd.DataFrame(response['teams'])
    for col in teams.columns:
        teams[col] = pd.to_numeric(teams[col], errors='ignore')
    teams['date'] = date.today()
    teams =  teams[['date'] + list(teams.columns[:-1])]
    return teams


def get_fixtures() -> pd.DataFrame:
    fixtures_response = requests.get(FIXTURES_ENDPOINT).json()
    fixtures = pd.DataFrame(fixtures_response)
    fixtures['team_h'] = fixtures['team_h'].apply(lambda x: TEAM_DICT[x])
    fixtures['team_a'] = fixtures['team_a'].apply(lambda x: TEAM_DICT[x])
    return fixtures