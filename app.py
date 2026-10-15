from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Neighborhoods near MSU", layout="wide")
st.title("Find your family's neighborhood near MSU")
st.write("Compare rent, families with children, schools, and other neighborhood features.")

# Read the CSV from the same folder as app.py and use short labels.
df = pd.read_csv(Path(__file__).parent / "housing_bg_analysis.csv")
df = df.rename(columns={
    "area_name": "City",
    "Med_Gross_Rent_ACS_20_24": "Median rent ($)",
    "Med_House_Value_BG_ACS_20_24": "Median home value ($)",
    "Med_HHD_Inc_BG_ACS_20_24": "Median household income ($)",
    "pct_College_ACS_20_24": "College degree or higher (%)",
    "pct_HHD_PPL_Und_18_ACS_20_24": "Households with children under 18 (%)",
    "Median_Age_ACS_20_24": "Median age (years)",
    "pct_Othr_Lang_ACS_20_24": "Other language at home (%)",
    "general_crime_count": "Recorded crime count",
    "district_overall_mean": "School district score",
})
district = pd.read_csv(Path(__file__).parent / "city_district.csv")
district = district.rename(columns={"city": "City", "overall_score": "School district score"})

rent = "Median rent ($)"
children = "Households with children under 18 (%)"
variables = [
    rent, "Median home value ($)", "Median household income ($)",
    "College degree or higher (%)", children, "Median age (years)",
    "Other language at home (%)", "Recorded crime count", "School district score",
]

# Graph 1: the two correlation bar charts from Part 3.1.
st.header("1. Relationships between neighborhood features")
targets = [rent, children]

corr_matrix = df[variables].corr()
chart_columns = st.columns(len(targets))
for i, name in enumerate(targets):
    corr = corr_matrix[name].drop(name).sort_values()
    bar_colors = []
    for value in corr.values:
        if value >= 0:
            bar_colors.append("#66c2a5")  # Mint: positive correlation
        else:
            bar_colors.append("#fc8d62")  # Coral: negative correlation
    fig = px.bar(
        x=corr.values, y=corr.index, orientation="h",
        title=name,
        labels={"x": "Pearson correlation", "y": "Feature"},
        range_x=[-0.2, 0.5],
    )
    fig.update_traces(marker_color=bar_colors)
    with chart_columns[i]:
        st.plotly_chart(fig, width="stretch")

# Graph 2: choose variables and filter block groups before drawing boxplots.
st.header("2. Compare distributions across cities")
cities = sorted(df["City"].unique())
city_colors = {
    "East Lansing": "#66c2a5",
    "Haslett": "#fc8d62",
    "Lansing": "#8da0cb",
    "Okemos": "#e78ac3",
}
selected_variables = st.multiselect(
    "Variables to compare", variables,
    default=[children, rent, "School district score", "Recorded crime count"],
)

min_children = float(df[children].min())
max_children = float(df[children].max())
min_rent = int(df[rent].min())
max_rent = int(df[rent].max())
slider_columns = st.columns([1, 1, 2])
with slider_columns[0]:
    child_range = st.slider(
        children, min_children, max_children,
        (min_children, max_children), step=0.01,
    )
with slider_columns[1]:
    rent_range = st.slider(
        "Median monthly rent ($)", min_rent, max_rent, (min_rent, max_rent),
    )

filtered_df = df.copy()
if child_range != (min_children, max_children):
    filtered_df = filtered_df[filtered_df[children].between(child_range[0], child_range[1])]
if rent_range != (min_rent, max_rent):
    filtered_df = filtered_df[filtered_df[rent].between(rent_range[0], rent_range[1])]

st.caption(f"Showing {len(filtered_df)} of {len(df)} block groups.")

if filtered_df.empty:
    st.warning("No block groups match. Widen the slider ranges.")
if not selected_variables:
    st.info("Choose at least one variable to see a boxplot.")
    st.stop()

box_columns = st.columns(2)
for i, variable in enumerate(selected_variables):
    # School scores use one row per school, as in the updated notebook.
    if variable == "School district score":
        plot_df = district
    else:
        plot_df = filtered_df
    with box_columns[i % 2]:
        if plot_df[variable].notna().sum() == 0:
            st.info("No available values for " + variable)
        else:
            fig = px.box(
                plot_df, x="City", y=variable, color="City",
                title=variable, points="outliers",
                category_orders={"City": cities},
                color_discrete_map=city_colors,
            )
            st.plotly_chart(fig, width="stretch")
