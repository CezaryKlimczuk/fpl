from mailer import send_info
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


def get_the_best_team(from_date: date, data_source: str = 'database') -> pd.DataFrame:
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
    df_injuries = get_newly_injured_players(date.today())
    message_body.append(df_injuries.to_html())
    final_team, objective_value, team_cost = get_the_best_team(date.today())
    message_body.append(final_team.to_html())
    message_body.append(str(objective_value))
    message_body.append(str(team_cost))
    final_message = '\n'.join(message_body)
    send_info(subject=f'FPL report {date.today()}', message_content=final_message)