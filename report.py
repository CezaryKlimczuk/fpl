import sys
from typing import Tuple
from mailer import send_html
import pandas as pd
from datetime import date, timedelta
from fantasy_football.data.db_connect import get_query, insert_dataframe
from fantasy_football.optimization import run_optimization
from fantasy_football.api import get_all_players, get_teams


CURRENT_TEAM = [17, 119, 134, 135, 229, 233, 237, 254, 256, 257, 362] 
CURRENT_BUDGET = 825

def get_newly_injured_players(from_date: date) -> pd.DataFrame:
    query = f"SELECT first_name, second_name, position, team ep_next, goals_scored, minutes, now_cost, ict_index, threat, ict_index_rank, chance_of_playing_next_round, chance_of_playing_this_round \
                FROM players WHERE date = '{from_date}' AND chance_of_playing_next_round != 'NaN' AND player_id NOT IN ( \
                SELECT player_id FROM players WHERE date = '{from_date - timedelta(days=1)}' AND chance_of_playing_next_round != 'NaN')"
    df_new_injuries = get_query(query)
    return df_new_injuries


def get_the_best_team(data_source: str = 'api') -> Tuple[pd.DataFrame, float, float]:
    final_team, objective_value, team_cost = run_optimization(_target_feature='ep_next', data_source=data_source, _budget=CURRENT_BUDGET) 
    return final_team, objective_value, team_cost


def get_the_best_transfer(data_source: str = 'api') -> pd.DataFrame:
    current_team, current_value, current_cost = run_optimization(_target_feature='ep_next', data_source=data_source, _budget=CURRENT_BUDGET, _team_members_ids=CURRENT_TEAM, _allowed_changes=0)
    better_team, better_value, better_cost = run_optimization(_target_feature='ep_next', data_source=data_source, _budget=CURRENT_BUDGET, _team_members_ids=CURRENT_TEAM, _allowed_changes=1) 
    return current_team, current_value, current_cost, better_team, better_value, better_cost 


def get_price_changes(from_date: date) -> pd.DataFrame:
    query = f"SELECT today.first_name, today.second_name, today.team, today.position, yesterday.now_cost as cost_yesterday, today.now_cost as cost_today, today.now_cost - yesterday.now_cost as change \
            FROM (SELECT * FROM players WHERE date = '{from_date}') today FULL JOIN (SELECT * FROM players WHERE date = '{from_date - timedelta(days=1)}') yesterday ON today.player_id = yesterday.player_id \
            ORDER BY change DESC;"
    df_price_changes = get_query(query)
    return df_price_changes


def get_ep_changes(from_date: date) -> pd.DataFrame:
    query = f"SELECT today.first_name, today.second_name, today.team, today.position, yesterday.ep_next as ep_yesterday, today.ep_next as ep_today, today.ep_next - yesterday.ep_next as change \
            FROM (SELECT * FROM players WHERE date = '{from_date}') today FULL JOIN (SELECT * FROM players WHERE date = '{from_date - timedelta(days=1)}') yesterday ON today.player_id = yesterday.player_id \
            ORDER BY change DESC;"
    df_ep_changes = get_query(query)
    return df_ep_changes


def get_the_best_ep(from_date: date) -> pd.DataFrame:
    pass


def update_database():
    player_df = get_all_players()
    teams_df = get_teams()
    # inserting both dataframes to the db
    insert_dataframe(player_df, "players") 
    insert_dataframe(teams_df, "teams")

if __name__ == '__main__':
    message_body = []
    message_body.append('<h1>FPL daily report</h1>')

    # updating today's date
    if sys.platform == 'linux':
        update_database()
        message_body.append('<p>Database updated successfully.</p>')

    # grabbing data on injuries, cost and ep chages
    df_injuries = get_newly_injured_players(date.today())
    df_price_changes = get_price_changes(date.today())
    df_price_changes = pd.concat([df_price_changes.head(10), df_price_changes.tail(10)], axis=0)
    df_ep_changes = get_ep_changes(date.today())
    df_ep_changes = pd.concat([df_ep_changes.head(10), df_ep_changes.tail(10)], axis=0)
    message_body.append('<h2>New injuries since yesterday</h2>')
    message_body.append(df_injuries.to_html())
    message_body.append('<h2>Price changes since yesterday:</h2>')
    message_body.append(df_price_changes.to_html())
    message_body.append('<h2>Expected score changes since yesterday:</h2>')
    message_body.append(df_ep_changes.to_html())

    # fetching the best possible team for the upcoming round
    best_team, best_value, best_cost = get_the_best_team()
    message_body.append('<h2>Best possible team within budget constraint:</h2>')
    message_body.append(f'<p>Expected score: {str(best_value)} and cost: {str(best_cost)} of the optimal team</p>')
    message_body.append(best_team.to_html())

    # transfer suggestions
    current_team, current_value, current_cost, better_team, better_value, better_cost = get_the_best_transfer() 
    message_body.append('<h2>Optimal transfer suggestion:</h2>')
    message_body.append(f'<p>Expected score now:{str(current_value)} and after: {str(better_value)}</p>')
    message_body.append(f'<p>Cost now:{str(current_cost)} and after: {str(better_cost)}</p>')
    message_body.append(current_team.to_html())
    message_body.append(better_team.to_html())
    ids_out = [idd for idd in current_team['player_id'] if idd not in better_team['player_id']]
    ids_in = [idd for idd in better_team['player_id'] if idd not in current_team['player_id']]
    players_out = current_team.query(f"player_id in {ids_out}")
    players_out['substitution'] = 'out'
    players_in = better_team.query(f"player_id in {ids_in}")
    players_in['substitution'] = 'in'
    df_subs = pd.concat([players_out, players_in], axis=0)
    message_body.append(df_subs.to_html())

    # wrapping up
    final_message = '\n'.join(message_body)
    send_html(subject=f'FPL report {date.today()}', html_content=final_message)