# Neighborhoods near MSU

[![Open app](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://find-neighborhood-near-msu.streamlit.app/)

[Open the live app](https://find-neighborhood-near-msu.streamlit.app/) — no installation needed.

This project helps international families compare housing, schools and recorded crime near MSU.
It covers 172 Census block groups in Lansing, East Lansing, Okemos and Haslett.
At least 70% of each block group's area is within 10 km of MSU Main Library.
Whole boundaries are kept. Township-labeled groups are excluded.

## Run locally

Use Python 3.11 or newer.

```bash
git clone https://github.com/DRamghi/CMSE830.git
cd CMSE830/project
python -m pip install -r requirements.txt
streamlit run app.py
```

The app shows Preprocessing, Analysis and Ready. It creates missing results and rebuilds results when inputs or calculation code change. Otherwise it uses saved results. No API key or download is needed. Preprocessing and analysis together take about one second on the development computer; map loading takes longer.

## Run in a web browser

GitHub stores the code. Streamlit Community Cloud runs the app and provides a public web address.
Visitors do not need to install Python or keep this computer running.

To deploy, sign in at [Streamlit Community Cloud](https://share.streamlit.io/) with GitHub and create an app:

- Repository: `DRamghi/CMSE830`
- Branch: `main`
- Main file path: `project/app.py`
- Python version: `3.12` in Advanced settings

Deploy the app, then share the generated `streamlit.app` address.
The app uses `project/requirements.txt` and the seven input files. No API secrets are needed.
It builds the processed files on its first run.
To use the included theme on Community Cloud, place a copy of `project/.streamlit/config.toml`
at `.streamlit/config.toml` in the repository root.

See the [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

## Project files

These 19 files are in the `project` folder. The input data are small local extracts, not full national or statewide downloads.

```text
.gitignore
README.md
requirements.txt
app.py                      Start the pipeline and Streamlit pages
prepare.py                  Clean, join and analyze the data
analysis.ipynb              Data checks, charts and interpretation
housing.py                  Variables, labels and radar tiers
map_utils.py                Map colors, markers and popups
dashboard.py                Controls and neighborhood details
about_page.py               Study area, sources and missing data
.streamlit/config.toml      App theme
map_component/index.html    Keep the map view and handle clicks
data/input/census.csv
data/input/block_groups.geojson
data/input/schools.csv
data/input/districts.geojson
data/input/crime.csv
data/input/crime_coverage.csv
data/input/gun_incidents.csv
```

The flow is **input data → prepare.py (preprocessing and analysis) → Streamlit**.
`python prepare.py` runs the calculations without opening the app.
Open `analysis.ipynb` to see population sizes and the two analysis questions.
The notebook compares crime only for Lansing and East Lansing. Okemos and Haslett are N/A in this comparison.
The school comparison uses individual schools in the four public school districts.
The app Schools tab lists all schools in the district containing the block-group center, matching the radar School score.
Schools are sorted by straight-line distance; online or unlocated schools appear last with N/A distance.
Map school-level filters and the 10 km marker limit do not restrict this district list.

The app creates three results in `data/processed/`: `neighborhoods.geojson`, `summary.csv` and `correlations.csv`.
This folder is not uploaded. Missing results are rebuilt on the first run; later runs reuse them.
Keep all seven input files.

Only the 19 files listed above are needed for this project.
The `.gitignore` file excludes other local files.

## Input data

These files are local study-area extracts. They are the starting data for this project.

| File in data/input | Source and contents |
| --- | --- |
| census.csv | [2026 Census Planning Database](https://www.census.gov/data/developers/data-sets/planning-database.html), ACS 2020–2024 estimates: housing, income, adult education, household, age, race/ethnicity and home language. Includes ages 25–44 and 45–64. Median gross rent comes from [2024 ACS 5-Year B25064](https://api.census.gov/data/2024/acs/acs5/groups/B25064.html). |
| block_groups.geojson | [2025 TIGER/Line](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) block-group boundaries. City names use TIGER place overlaps, ordered by area. |
| schools.csv | [Michigan school GIS](https://gisagocss.state.mi.us/arcgis/rest/services/CSS/Schools_Districts/MapServer/0) and [2024–25 MDE School Index](https://www.michigan.gov/mde/services/school-performance-supports/accountability/school-index), saved October 7, 2026. 111 schools for district means; 97 have locations, and 52 are within 10 km. School locations and levels were checked October 21. |
| districts.geojson | [Michigan district GIS](https://gisagocss.state.mi.us/arcgis/rest/services/OpenData/michigan_geographic_framework/MapServer/10): 15 district boundaries, saved October 7, 2026. |
| crime.csv | [Lansing Police](https://www.lansingmi.gov/crime-mapping) and [East Lansing Police / CrimeMapping.com](https://www.cityofeastlansing.com/358/Crime-Mapping): 4,597 located records, April 10–October 6, 2026. 4,101 fall in the study block groups. |
| crime_coverage.csv | Block-group coverage based on provider-city overlap: available, partial or unavailable. This is an approximation, not an official police jurisdiction boundary. |
| gun_incidents.csv | [Gun Violence Archive](https://www.gunviolencearchive.org/): April 10–October 6, 2026, saved October 7. 16 local incidents, 15 with approximate address-based coordinates and one unlocated. Eleven fall in the study block groups. A separate point layer only. |

## AI use disclosure

I used ChatGPT 6.1 Sol to help find and combine datasets, map the data, and build the Streamlit app. I checked the outputs by running the code and reviewing tables, charts, and the app. I planned the project and made the final decisions about questions, data, and visualizations. I am responsible for validation, interpretation, conclusions, and explaining all submitted work.
