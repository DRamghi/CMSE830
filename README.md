# Neighborhoods near MSU

## Project purpose

This app helps international families compare areas near MSU. It shows rent, households with children, school scores, and recorded crime in Lansing, East Lansing, Okemos, and Haslett.

Area data may be old or missing. Crime coverage is incomplete. District information does not guarantee a school assignment.

## Setup/run instructions

Use Python 3.11 or newer.

```bash
git clone https://github.com/DRamghi/CMSE830.git
cd CMSE830
python -m pip install streamlit==1.51.0 pandas==2.3.3 plotly==6.3.0
python -m streamlit run app.py
```

Keep `housing_bg_analysis.csv` and `city_district.csv` in the same folder as `app.py`. Open the local URL shown in the terminal.
