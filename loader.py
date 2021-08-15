import pandas as pd

def get_players_and_teams(round: str = '00') -> pd.DataFrame:
    df_players = pd.read_csv(f"data\\players_{round}.csv")
    df_teams = pd.read_csv(f"data\\teams_{round}.csv")
    df_positions = pd.read_csv(f"data\\positions.csv")
    
    # preprocessing players' frame 
    team_dict = dict(zip(df_teams['id'], df_teams['name']))
    position_dict = dict(zip(df_positions['id'], df_positions['singular_name_short']))
    
    df_players['team'] = df_players['team'].apply(lambda x: team_dict[x])
    df_players['position'] = df_players['element_type'].apply(lambda x: position_dict[x])
    df_players.drop(columns=['element_type'], inplace=True)

    for col in df_players.columns:
        df_players[col] = pd.to_numeric(df_players[col], errors='ignore')
    for col in df_teams.columns:
        df_teams[col] = pd.to_numeric(df_teams[col], errors='ignore')

    return df_players, df_teams