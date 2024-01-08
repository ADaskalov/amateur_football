import random

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import streamlit as st
from matplotlib import colormaps
from mplsoccer import Pitch, Sbopen, VerticalPitch

import utils

st.set_page_config(layout="wide")
st.markdown(
    """
    <style>
        div[data-testid="column"]:nth-of-type(1)
        {
            text-align: end;
        }

        h2
        {
            text-align: center;
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

# Pretty graphs bit
parser = Sbopen()


@st.cache_data
def get_match_stats(match_id):
    return parser.event(match_id)


@st.cache_data
def get_matches(competition_id, season_id):
    return parser.match(competition_id=competition_id, season_id=season_id)


@st.cache_data
def get_competitions():
    return parser.competition()


comps = get_competitions()
comps_to_select = (
    comps.query('competition_gender == "male" and not competition_youth')
    .sort_values("match_available")
    .iloc[:60]
)
random.seed(int(match_date))
comp_id = random.choice(comps_to_select.index)
matches = get_matches(
    competition_id=comps_to_select.at[comp_id, "competition_id"],
    season_id=comps_to_select.at[comp_id, "season_id"],
)
match_id = random.choice(matches["match_id"])

match_stats, related, freeze, tactics = get_match_stats(match_id)
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
df_shots = match_stats.query('type_name == "Shot"').copy()

# subset the shots for each team
team1, team2 = df_shots.team_name.unique()
shots_team1 = df_shots[df_shots.team_name == team1].copy()
shots_team2 = df_shots[df_shots.team_name == team2].copy()


red = colormaps.get_cmap("Reds")(np.linspace(0, 1, 100))[60]
blue = colormaps.get_cmap("Blues")(np.linspace(0, 1, 100))[60]

# Usually in football, the data is collected so the attacking direction is left to right.
# We can shift the coordinates via: new_x_coordinate = right_side - old_x_coordinate
# This is helpful for having one team shots on the left of the pitch and the other on the right
shots_team1["x"] = pitch.dim.right - shots_team1.x


pitch_fig, pitch_axes = pitch.jointgrid(
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
    shots_team1.x,
    shots_team1.y,
    ax=pitch_axes["pitch"],
    cmap="Reds",
    levels=75,
    fill=True,
)
kde2 = pitch.kdeplot(
    shots_team2.x,
    shots_team2.y,
    ax=pitch_axes["pitch"],
    cmap="Blues",
    levels=75,
    fill=True,
)
# kdeplot on marginal axes
team1_hist_y = sns.kdeplot(y=shots_team1.y, ax=pitch_axes["left"], color=red, fill=True)
team1_hist_x = sns.kdeplot(x=shots_team1.x, ax=pitch_axes["top"], color=red, fill=True)
team2_hist_x = sns.kdeplot(x=shots_team2.x, ax=pitch_axes["top"], color=blue, fill=True)
team2_hist_y = sns.kdeplot(
    y=shots_team2.y, ax=pitch_axes["right"], color=blue, fill=True
)
txt1 = pitch_axes["pitch"].text(
    x=15,
    y=70,
    s="Ягодка",
    color=red,
    ha="center",
    va="center",
    fontsize=30,
)
txt2 = pitch_axes["pitch"].text(
    x=105,
    y=70,
    s="Черешка",
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
        "Saves": saves,
        "Blocked": blocked,
        "Off Target": off_target,
        "On Target": on_target,
        "Shots": all_shots,
        "xG": xg,
    }
    return team_stats


st.header("Изстрели")
st.write(pitch_fig)

home_stats = create_statistics(shots_team1)
away_stats = create_statistics(shots_team2)
stats_fig, stats_axes = plt.subplots(figsize=(10, 5), ncols=2, sharey=True)
stats_fig.tight_layout()
labels = tuple(home_stats.keys())


stats_axes[0].invert_xaxis()
stats_axes[0].yaxis.tick_left()

for data, ax, colour, name in zip(
    [home_stats, away_stats], stats_axes, [red, blue], ["Ягодка", "Черешка"]
):
    ax.barh(labels, data.values(), align="center", color=colour, zorder=10)
    ax.set_title(name, fontsize=18, pad=15, color=colour)
    ax.bar_label(ax.containers[0], fontsize=15, color=colour)
    # ax.set(xticklabels=[])
    ax.tick_params(bottom=False, left=False, labelbottom=False)
    for label in ax.get_yticklabels():
        label.set(fontsize=13)
    ax.set_facecolor("white")
sns.despine(stats_fig, left=True, bottom=True)
stats_axes[0].set(yticks=labels, yticklabels=labels)

plt.subplots_adjust(wspace=0, top=0.85, bottom=0.1, left=0.18, right=0.95)


st.header("Статистика")
st.write(stats_fig)

match_meta = matches.query(f"match_id == {match_id}").iloc[0]
st.write(
    f"*Actual game played: {match_meta['home_team_name']} vs {match_meta['away_team_name']}"
    f" on {match_meta['match_date']:%Y-%m-%d} for {match_meta['season_name']} {match_meta['competition_name']}"
    f" final score {match_meta['home_score']} - {match_meta['away_score']}"
)
