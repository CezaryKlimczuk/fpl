from fantasy_football.api import get_all_players, get_teams 
from fantasy_football.data.db_connect import insert_dataframe 
from fantasy_football.mailer import send_info


if __name__ == "__main__":
    player_df = get_all_players()
    teams_df = get_teams()
    # inserting both dataframes to the db
    insert_dataframe(player_df, "players") 
    insert_dataframe(teams_df, "teams")