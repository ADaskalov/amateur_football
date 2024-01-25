import pandas as pd
import streamlit as st

import utils

st.set_page_config(layout="wide")
st.markdown(
    """
    <style>
        div[data-testid="column"]:nth-of-type(1)
        {
            text-align: end;
        }
    </style>
    """,
    unsafe_allow_html=True,
)
conn = utils.get_gsheet_connection()
players = utils.get_player_list(conn)
match_data = utils.get_match_data(conn)


thursdays = pd.date_range(
    "2023-10-01", pd.Timestamp.now() + pd.DateOffset(days=6), freq="W-THU"
)
match_date = st.selectbox(
    "Select match date", map(lambda t: t.date(), sorted(thursdays, reverse=True))
)
assert match_date is not None, "No match date selected"
team_a_players, team_b_players = utils.get_players_per_team(
    match_data, pd.to_datetime(match_date)
)
team_a, team_b = st.columns(2, gap="medium")
with st.form("edit_form"):
    with team_a:
        st.subheader("Отбор Ягодка")
        team_a_score = st.number_input(
            "Ягодка резултат",
            min_value=0,
            max_value=50,
            value=int(team_a_players["goals"].sum()),
            step=1,
            label_visibility="collapsed",
        )

        team_a_players_edit = st.data_editor(
            team_a_players.query('name!="Other"')[["name", "goals", "assists"]],
            column_config={
                "name": st.column_config.SelectboxColumn(
                    "Name",
                    help="Name of the player",
                    width="medium",
                    options=players,
                    required=True,
                ),
                "goals": st.column_config.NumberColumn(
                    "Goals",
                    help="Number of goals",
                    min_value=0,
                    step=1,
                    required=True,
                ),
                "assists": st.column_config.NumberColumn(
                    "Assists",
                    help="Number of assists",
                    min_value=0,
                    step=1,
                    required=True,
                ),
            },
            hide_index=True,
            key="team_a_editor",
        )

    with team_b:
        st.subheader("Отбор Черешка")
        team_b_score = st.number_input(
            "Черешка резултат",
            min_value=0,
            max_value=50,
            value=int(team_b_players["goals"].sum()),
            step=1,
            label_visibility="collapsed",
        )
        team_b_players_edit = st.data_editor(
            team_b_players.query('name!="Other"')[["name", "goals", "assists"]],
            column_config={
                "name": st.column_config.SelectboxColumn(
                    "Name",
                    help="Name of the player",
                    width="medium",
                    options=players,
                    required=True,
                ),
                "goals": st.column_config.NumberColumn(
                    "Goals",
                    help="Number of goals",
                    min_value=0,
                    step=1,
                    required=True,
                ),
                "assists": st.column_config.NumberColumn(
                    "Assists",
                    help="Number of assists",
                    min_value=0,
                    step=1,
                    required=True,
                ),
            },
            hide_index=True,
            key="team_b_editor",
        )
    if st.form_submit_button("Submit", use_container_width=True, type="primary"):
        if team_a_players_edit["name"].duplicated().any():
            st.error("Team A contains duplicate players")
        elif team_b_players_edit["name"].duplicated().any():
            st.error("Team B contains duplicate players")
        elif (
            pd.concat([team_a_players_edit, team_b_players_edit], axis=0)["name"]
            .duplicated()
            .any()
        ):
            st.error("The same player appears for both teams")
        elif team_a_score < team_a_players_edit["goals"].sum():
            "Team A score must be greater than or equal to the sum of goals"
        elif team_b_score < team_b_players_edit["goals"].sum():
            "Team B score must be greater than or equal to the sum of goals"
        else:
            team_sheets = pd.concat(
                [
                    utils.enrich_team_sheet(
                        team_a_players_edit, pd.Timestamp(match_date), "A", team_a_score
                    ).squeeze(),
                    utils.enrich_team_sheet(
                        team_b_players_edit, pd.Timestamp(match_date), "B", team_b_score
                    ).squeeze(),
                ],
                ignore_index=True,
                axis=0,
            )
            utils.upload_team_sheet(conn, team_sheets)
            st.success("Match data updated successfully")
