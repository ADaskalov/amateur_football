import numpy as np
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
match_data = utils.get_match_data(conn)


match_date = st.selectbox(
    "Select match date",
    match_data["date"].unique(),
    format_func=lambda dt: np.datetime_as_string(dt, unit="D"),
)
team_a_players, team_b_players = utils.get_players_per_team(match_data, match_date)
team_a, team_b = st.columns(2, gap="medium")
with team_a:
    st.subheader("Отбор Ягодка")
    st.metric(
        "Goals",
        int(team_a_players["goals"].sum()),
        label_visibility="hidden",
    )
    for i, r in team_a_players.iterrows():
        st.write(f"{'⚽' * int(r['goals'])} {r['name']}")

with team_b:
    st.subheader("Отбор Черешка")
    st.metric(
        "Goals",
        int(team_b_players["goals"].sum()),
        label_visibility="hidden",
    )
    for i, r in team_b_players.iterrows():
        st.write(f"{r['name']} {'⚽' * int(r['goals'])}")


import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import colormaps
from mplsoccer import Pitch, Sbopen, VerticalPitch

parser = Sbopen()


@st.cache_data
def get_match_stats(match_id):
    return parser.event(match_id)


match_id = 9860
df, related, freeze, tactics = get_match_stats(match_id)
# setup the mplsoccer StatsBomb Pitches
# note not much padding around the pitch so the marginal axis are tight to the pitch
# if you are using a different goal type you will need to increase the padding to see the goals
pitch = Pitch(
    pad_top=0.05, pad_right=0.05, pad_bottom=0.05, pad_left=0.05, line_zorder=2
)
vertical_pitch = VerticalPitch(
    half=True,
    pad_top=0.05,
    pad_right=0.05,
    pad_bottom=0.05,
    pad_left=0.05,
    line_zorder=2,
)


# subset the shots
df_shots = df[df.type_name == "Shot"].copy()

# subset the shots for each team
team1, team2 = df_shots.team_name.unique()
df_team1 = df_shots[df_shots.team_name == team1].copy()
df_team2 = df_shots[df_shots.team_name == team2].copy()


red = colormaps.get_cmap("Reds")(np.linspace(0, 1, 100))[60]
blue = colormaps.get_cmap("Blues")(np.linspace(0, 1, 100))[60]

# Usually in football, the data is collected so the attacking direction is left to right.
# We can shift the coordinates via: new_x_coordinate = right_side - old_x_coordinate
# This is helpful for having one team shots on the left of the pitch and the other on the right
df_team1["x"] = pitch.dim.right - df_team1.x


fig, axs = pitch.jointgrid(
    figheight=10,
    left=None,
    bottom=0.075,
    grid_height=0.8,
    axis=False,  # turn off title/ endnote/ marginal axes
    # plot without endnote/ title axes
    title_height=0,
    endnote_height=0,
)
# increase number of levels for a smoother looking heatmap
kde1 = pitch.kdeplot(
    df_team1.x, df_team1.y, ax=axs["pitch"], cmap="Reds", levels=75, fill=True
)
kde2 = pitch.kdeplot(
    df_team2.x, df_team2.y, ax=axs["pitch"], cmap="Blues", levels=75, fill=True
)
# kdeplot on marginal axes
team1_hist_y = sns.kdeplot(y=df_team1.y, ax=axs["left"], color=red, fill=True)
team1_hist_x = sns.kdeplot(x=df_team1.x, ax=axs["top"], color=red, fill=True)
team2_hist_x = sns.kdeplot(x=df_team2.x, ax=axs["top"], color=blue, fill=True)
team2_hist_y = sns.kdeplot(y=df_team2.y, ax=axs["right"], color=blue, fill=True)
txt1 = axs["pitch"].text(
    x=15,
    y=70,
    s="Ягодка",
    # fontproperties=fm.prop,
    color=red,
    ha="center",
    va="center",
    fontsize=30,
)
txt2 = axs["pitch"].text(
    x=105,
    y=70,
    s="Черешка",
    # fontproperties=fm.prop,
    color=blue,
    ha="center",
    va="center",
    fontsize=30,
)


def create_statistics(shot_df):
    outcomes = shot_df.outcome_name.value_counts()
    all_shots = outcomes.sum()
    goals = outcomes.Goal if hasattr(outcomes, "Goal") else 0
    saves = outcomes.Saved if hasattr(outcomes, "Saved") else 0
    post = outcomes.Post if hasattr(outcomes, "Post") else 0
    on_target = saves + goals
    off_target = all_shots - on_target
    blocked = outcomes.Blocked if hasattr(outcomes, "Blocked") else 0
    xg = round(shot_df.shot_statsbomb_xg.sum(), 2)

    team_stats = {
        "all_shots": all_shots,
        "on_target": on_target,
        "off_target": off_target,
        "saves": saves,
        "blocked": blocked,
        "xg": xg,
    }
    return team_stats


home_stats = create_statistics(df_team1)
away_stats = create_statistics(df_team2)
fig2, axes = plt.subplots(figsize=(10, 5), ncols=2, sharey=True)
fig2.tight_layout()
labels = tuple(home_stats.keys())
axes[0].barh(labels, home_stats.values(), align="center", color=red, zorder=10)
axes[0].invert_xaxis()
axes[0].set_title("Ягодка", fontsize=18, pad=15, color=red)
axes[0].set(yticks=labels, yticklabels=labels)
axes[0].yaxis.tick_left()
axes[1].barh(labels, away_stats.values(), align="center", color=blue, zorder=10)
axes[1].set_title("Черешка", fontsize=18, pad=15, color=blue)

plt.subplots_adjust(wspace=0, top=0.85, bottom=0.1, left=0.18, right=0.95)

for label in axes[0].get_xticklabels() + axes[0].get_yticklabels():
    label.set(fontsize=13)
for label in axes[1].get_xticklabels() + axes[1].get_yticklabels():
    label.set(fontsize=13)


st.write(fig)
st.write(fig2)
