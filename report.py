from typing import Tuple
from mailer import send_html
import pandas as pd
from datetime import date, timedelta
from fantasy_football.data.db_connect import get_query
from fantasy_football.optimization import run_optimization


def get_newly_injured_players(from_date: date) -> pd.DataFrame:
    query = f"SELECT first_name, second_name, position, team ep_next, goals_scored, minutes, now_cost, ict_index, threat, ict_index_rank, chance_of_playing_next_round, chance_of_playing_this_round \
                FROM players WHERE date = '{from_date}' AND chance_of_playing_next_round != 'NaN' AND photo NOT IN ( \
                SELECT photo FROM players WHERE date = '{from_date - timedelta(days=1)}' AND chance_of_playing_next_round != 'NaN')"
    df_new_injuries = get_query(query)
    return df_new_injuries


def get_the_best_team(data_source: str = 'database') -> Tuple[pd.DataFrame, float, float]:
    final_team, objective_value, team_cost = run_optimization(_target_feature='ep_next', data_source=data_source, _budget=825) 
    return final_team, objective_value, team_cost


def get_the_best_transfer(from_date: date) -> pd.DataFrame:
    pass


def get_price_increases(from_date: date) -> pd.DataFrame:
    pass


def get_the_best_ep(from_date: date) -> pd.DataFrame:
    pass


if __name__ == '__main__':
    message_body = []
    # data fetching
    df_injuries = get_newly_injured_players(date.today())
    final_team, objective_value, team_cost = get_the_best_team()
    # body construction
    message_body.append('<h1>FPL daily report</h1>')
    message_body.append('<h2>New injuries since yesterday</h2>')
    message_body.append(df_injuries.to_html())
    message_body.append('<h2>Best possible team within budget constraint:</h2>')
    message_body.append(final_team.to_html())
    message_body.append(f'<p>Expected score of the optimal team: {str(objective_value)}</p>')
    message_body.append(f'<p>Total cost of the optimal team: {str(team_cost)}</p>')
    final_message = '\n'.join(message_body)
    send_html(subject=f'FPL report {date.today()}', html_content=final_message)