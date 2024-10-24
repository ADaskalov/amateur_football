import itertools
import re

import numpy as np
import pandas as pd
import streamlit as st

import utils


def get_player_outcome_summary(md):
    outcome_summary = (
        md.groupby("name")["sign"]
        .value_counts()
        .unstack()
        .fillna(0)
        .astype(int)
        .drop("Other")
        .sort_values(["W", "D"], ascending=False)
    )[["W", "D", "L"]]
    outcome_summary["Win %"] = outcome_summary["W"] / outcome_summary.sum(axis=1)
    return outcome_summary


def calculate_player_ratings(match_data_with_outcomes: pd.DataFrame) -> pd.Series:
    player_rating = pd.Series(
        index=match_data_with_outcomes["name"].unique(), data=1500
    )
    for dt in match_data_with_outcomes["date"].unique():
        md_dt = match_data_with_outcomes.query(f'date=="{dt}"').copy()
        md_dt["rating"] = md_dt["name"].map(player_rating)
        outcome = md_dt["outcome"].iloc[0]
        normalized_outcome = 1 / (np.exp(-outcome) + 1)  # sigmoid function
        team_ratings = md_dt.groupby("team")["rating"].mean().to_dict()
        team_rating_change = 32 * (
            normalized_outcome
            - 1 / (1 + 10 ** ((team_ratings["A"] - team_ratings["B"]) / 400))
        )

        for i, r in md_dt.iterrows():
            sign_of_change = ((r["team"] == "A") - 0.5) * 2
            player_rating[r["name"]] += sign_of_change * team_rating_change
    return player_rating.sort_values()


gc = utils.get_gsheet_connection()
md = utils.get_match_data(gc)
match_data_with_outcomes = utils.get_match_outcome(md)
player_ratings = calculate_player_ratings(match_data_with_outcomes)
if st.checkbox("Show raw data", value=False):
    st.dataframe(get_player_outcome_summary(match_data_with_outcomes))
    st.dataframe(player_ratings)


def split_teams(list_of_players: list, player_ratings: pd.Series) -> pd.Series:
    try:
        players_to_choose_from = player_ratings.loc[list_of_players].copy()
    except KeyError:
        missing_players = set(list_of_players).difference(set(player_ratings.index))
        st.write(f"These are missing {missing_players}")
        return pd.Series(dtype = int)
    results = dict()
    for team_split in range(2**11):
        if team_split.bit_count() == 6:
            results[team_split] = abs(
                (
                    players_to_choose_from
                    * np.array(list(str(bin(team_split))[2:].zfill(12))).astype(int)
                ).mean()
                * 2
                - players_to_choose_from.mean()
            )
    return pd.Series(results).sort_values()


with st.form("split_teams"):
    player_list_raw = st.text_area("Enter 12 players")
    if st.form_submit_button("Split teams"):
        player_list = player_list_raw.split("\n")
        player_list = list(map(lambda t: re.sub("^\d+\. ", "", t).strip(), player_list))
        team_splits = split_teams(player_list, player_ratings)
        for team_split, score in team_splits.iloc[:3].items():
            st.write(f"Score: {score*1000:.4f}")
            col1, col2 = st.columns(2)
            with col1:
                st.write(
                    sorted(
                        list(
                            itertools.compress(
                                player_list,
                                list(
                                    np.array(
                                        list(str(bin(team_split))[2:].zfill(12))  # type: ignore
                                    ).astype(bool)
                                ),
                            )
                        )
                    )
                )
            with col2:
                st.write(
                    sorted(
                        list(
                            itertools.compress(
                                player_list,
                                list(
                                    ~np.array(
                                        list(str(bin(team_split))[2:].zfill(12))  # type: ignore
                                    ).astype(bool)
                                ),
                            )
                        )
                    )
                )
