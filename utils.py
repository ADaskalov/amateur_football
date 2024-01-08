import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

column_names = ["date", "team", "name", "goals"]


@st.cache_resource
def get_gsheet_connection():
    return st.connection("gsheets", type=GSheetsConnection)


def get_player_list(conn: GSheetsConnection) -> list:
    players = conn.read(worksheet="Players", usecols=[0], nrows=100)
    players = players.query("name.notnull()")["name"].tolist()
    return sorted(players)


def get_match_data(conn: GSheetsConnection) -> pd.DataFrame:
    match_data = conn.read(
        worksheet="game_data", usecols=range(len(column_names)), nrows=4000
    )
    match_data["date"] = pd.to_datetime(match_data["date"])
    match_data = match_data.query("name.notnull()")
    return match_data


def get_funds(conn: GSheetsConnection) -> pd.DataFrame:
    funds_data = conn.read(worksheet="funds", usecols=range(3), nrows=400)
    funds_data["date"] = pd.to_datetime(funds_data["date"])
    funds_data = funds_data.query("amount.notnull()")
    return funds_data


def get_empty_team_sheet(match_date: pd.Timestamp) -> pd.DataFrame:
    team_sheet = pd.DataFrame(index=range(6), columns=["name", "goals", "date"])
    team_sheet["date"] = match_date
    team_sheet["goals"] = 0
    return team_sheet


def get_players_per_team(match_data: pd.DataFrame, match_date: pd.Timestamp) -> tuple:
    if match_data.query(f"date == '{match_date}'").empty:
        return get_empty_team_sheet(match_date), get_empty_team_sheet(match_date)
    team_a_players = match_data.query(
        f"date == '{match_date}' and team == 'A'"
    ).sort_values("goals", ascending=False)
    team_b_players = match_data.query(
        f"date == '{match_date}' and team == 'B'"
    ).sort_values("goals", ascending=False)
    return team_a_players, team_b_players


def enrich_team_sheet(
    team_sheet_df: pd.DataFrame, match_date: pd.Timestamp, team: str, total_goals
) -> pd.DataFrame:
    other_goals = int(total_goals - team_sheet_df["goals"].sum())
    assert (
        other_goals >= 0
    ), f"Total goals {total_goals} is less than sum of goals {team_sheet_df['goals'].sum()}"
    other_row = pd.Series({"name": "Other", "goals": other_goals})
    team_sheet_df = team_sheet_df.append(other_row, ignore_index=True)
    team_sheet_df["date"] = pd.to_datetime(match_date)
    team_sheet_df["team"] = team
    team_sheet_df["goals"] = team_sheet_df["goals"].fillna(0).astype(int)
    team_sheet_df["total_goals"] = total_goals
    return team_sheet_df


def upload_team_sheet(conn: GSheetsConnection, team_sheet: pd.DataFrame):
    match_data = get_match_data(conn)
    match_data = pd.concat(
        [match_data[~match_data["date"].isin(team_sheet["date"].unique())], team_sheet],
        ignore_index=True,
    ).sort_values("date", ascending=False)
    conn.update(data=match_data[column_names], worksheet="game_data")

    st.cache_data.clear()


# extra_players = set(match_data["name"]).difference(set(players).union(set(["Other"])))
# assert len(extra_players) == 0, f"Extra players: {extra_players}"
# assert match_data["team"].isin(["A", "B"]).all(), "Team must be A or B"
