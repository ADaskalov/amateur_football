import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

import utils

sns.set_theme(style="darkgrid")
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
funds_data = utils.get_funds(conn).sort_values("date", ascending=True)

cum_funds_data = funds_data.groupby("date").agg(
    {
        "amount": "sum",
        "description": lambda x: ", ".join(x[x.notnull()].tolist())
        if x.notnull().any()
        else "",
    }
)
cum_funds_data["amount"] = cum_funds_data["amount"].cumsum()

a4_dims = (20, 10)
fig, ax = plt.subplots(figsize=a4_dims)

palette = ["r", "b", "g"]

p1 = sns.lineplot(
    x="date",
    y="amount",
    markers=True,
    dashes=False,
    data=cum_funds_data,
    palette=palette,
)
ax.set_ylabel("Сума")
ax.set_xlabel("Дата")
st.metric(
    f"Общо събрано (към {cum_funds_data.index[-1]:%d.%m.%Y})",
    value=f'{int(cum_funds_data["amount"].iloc[-1])} лв.',
    delta=cum_funds_data["amount"].diff().iloc[-1],
)
st.header("Каса")
st.write(fig)
st.dataframe(
    funds_data.sort_values("date", ascending=False),
    hide_index=True,
    use_container_width=True,
    column_config={
        "date": st.column_config.DateColumn("Дата"),
        "amount": st.column_config.NumberColumn("Сума (лв.)"),
        "description": st.column_config.TextColumn("Описание"),
    },
)
