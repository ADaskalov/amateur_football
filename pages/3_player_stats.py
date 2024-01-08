import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
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

starting_point = st.radio(
    "Стартова дата",
    ["since_beginning", "from_2024", "other"],
    format_func={
        "since_beginning": "Отначало",
        "from_2024": "от 2024-та",
        "other": "Друга",
    }.get,
    index=1,
    horizontal=True,
)
match starting_point:
    case "since_beginning":
        start_date = match_data["date"].min()
    case "from_2024":
        start_date = pd.Timestamp("2024-01-01")
    case "other":
        start_date = st.date_input(
            "Избери начало", pd.Timestamp.now() - pd.DateOffset(months=3)
        )
apps_data = (
    match_data.query("date >= @start_date")
    .groupby("name")
    .agg({"date": "count", "goals": "sum"})
    .query("date > 0 and name != 'Other'")
)
st.dataframe(
    apps_data.sort_values(["date", "goals"], ascending=[False, False]),
    column_config={
        "date": st.column_config.NumberColumn("Мачове"),
        "goals": st.column_config.NumberColumn("Голове"),
    },
    use_container_width=True,
    height=800,
)

heatmap_data = (
    match_data.query("date >= @start_date and name != 'Other'")
    .groupby(["name", "date"])
    .agg({"team": "count"})["team"]
    .unstack()
    .fillna(0)
)
heatmap_data.index.name = None
heatmap_data.columns = np.datetime_as_string(heatmap_data.columns, unit="D")

fig, ax = plt.subplots(figsize=(20, 10))
sns.heatmap(
    heatmap_data,
    cmap=sns.cubehelix_palette(start=2, rot=0, dark=0.75, light=1, as_cmap=True),
    vmin=0,
    vmax=1,
    cbar=False,
    ax=ax,
)
ax.tick_params(bottom=False, left=False)


print(heatmap_data)
st.write(fig)
