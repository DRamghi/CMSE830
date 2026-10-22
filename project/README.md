# Neighborhoods near MSU

[![Open app](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://find-neighborhood-near-msu.streamlit.app/)

[Open the live app](https://find-neighborhood-near-msu.streamlit.app/) — no installation needed.

This project helps international families compare housing, schools and recorded crime near MSU.
It covers 172 Census block groups near MSU in Lansing, East Lansing, Okemos and Haslett.

## How to read the information

- **Schools are a comparison reference, not a confirmed school assignment.** For each block group, the app uses all schools in the school district containing its center point. The school score is their mean available OverallIndex. This does not confirm which district or school an individual home or child would be assigned to.
- **Rent combines housing types and sizes.** It is the Census median gross rent for rental homes paying cash rent, without separating apartments from houses or small homes from large homes. It is not a comparison of similar-sized homes or a current listing price.
- **Missing data:** The datasets used in this analysis contain missing values, shown in gray on the map. Crime comparisons in the notebook use only Lansing and East Lansing because Okemos and Haslett have incomplete coverage.
- **Census estimates:** The ACS statistics are based on a sample survey and have sampling error. They are estimates, not exact values for every household or resident.
- Recorded crime counts are published records, not population-adjusted crime rates. GVA gun incidents are a separate map layer and are not added to police counts.

## Run locally

Use Python 3.11 or newer.

```bash
git clone https://github.com/DRamghi/CMSE830.git
cd CMSE830/project
python -m pip install -r requirements.txt
streamlit run app.py
```

The app automatically prepares missing results and uses saved results when available.
No API key or data download is needed.

## Project files

The following 19 files are in `project/`:

```text
.gitignore
README.md
requirements.txt
app.py                      Start the app
prepare.py                  Clean, join and analyze data
analysis.ipynb              Data checks, charts and interpretation
housing.py                  Variables and radar tiers
map_utils.py                Map colors, markers and popups
dashboard.py                Controls and neighborhood details
about_page.py               Data information and AI disclosure
.streamlit/config.toml      Theme
map_component/index.html    Map view and clicks
data/input/census.csv
data/input/block_groups.geojson
data/input/schools.csv
data/input/districts.geojson
data/input/crime.csv
data/input/crime_coverage.csv
data/input/gun_incidents.csv
```

**Input data → prepare.py → analysis and Streamlit.**
The app creates its results in `data/processed/`. Open `analysis.ipynb` for the two analysis questions.

## Data sources

The input files are local study-area extracts.

| File in data/input | Source and contents |
| --- | --- |
| census.csv | [2026 Census Planning Database](https://www.census.gov/data/developers/data-sets/planning-database.html): ACS 2020–2024 housing, income, education, household and population estimates. Median gross rent: [2024 ACS 5-Year B25064](https://api.census.gov/data/2024/acs/acs5/groups/B25064.html). |
| block_groups.geojson | [2025 TIGER/Line](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html): block-group boundaries and place names. |
| schools.csv | [Michigan school GIS](https://gisagocss.state.mi.us/arcgis/rest/services/CSS/Schools_Districts/MapServer/0): school locations; [2024–25 MDE School Index](https://www.michigan.gov/mde/services/school-performance-supports/accountability/school-index): school scores. |
| districts.geojson | [Michigan district GIS](https://gisagocss.state.mi.us/arcgis/rest/services/OpenData/michigan_geographic_framework/MapServer/10): school district boundaries. |
| crime.csv | [Lansing Police](https://www.lansingmi.gov/crime-mapping) and [East Lansing Police / CrimeMapping.com](https://www.cityofeastlansing.com/358/Crime-Mapping): published records for April 10–October 6, 2026. |
| crime_coverage.csv | Coverage labels based on overlap with provider cities: available, partial or unavailable. |
| gun_incidents.csv | [Gun Violence Archive](https://www.gunviolencearchive.org/): incidents for April 10–October 6, 2026, with approximate locations. |

## AI use disclosure

I used ChatGPT 6.1 Sol to help find and combine datasets, map the data, and build the Streamlit app. I checked the outputs by running the code and reviewing tables, charts, and the app. I planned the project and made the final decisions about questions, data, and visualizations. I am responsible for validation, interpretation, conclusions, and explaining all submitted work.
