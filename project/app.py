"""Run: streamlit run app.py. Prepare the results before opening the map."""
from pathlib import Path

import geopandas as gpd
import streamlit as st
import streamlit.components.v1 as components

from prepare import DATA, ensure_data, read_crime, read_gun_incidents, read_schools
from housing import format_value
from map_utils import make_map, school_table
from dashboard import render_app
from about_page import render_about

BASE = Path(__file__).resolve().parent
st.set_page_config(page_title='MSU Family Neighborhoods', page_icon='🌿', layout='wide')
neighborhood_map = components.declare_component('neighborhood_map', path=str(BASE/'map_component'))


# Show calculation progress on the first run and reuse saved results on later runs.
# The app and notebook share analysis functions; the server does not run the notebook.
status = st.status('Checking local data…', expanded=False)


def show_progress(stage, state, seconds):
    if state == 'running':
        status.update(label=f'{stage}…', state='running', expanded=True)
        status.write(f'{stage} started.')
    elif state == 'complete':
        status.write(f'{stage} complete · {seconds:.2f} s')
    else:
        status.write(f'{stage}: using saved results.')


try:
    pipeline_info = ensure_data(show_progress)
except (OSError, ValueError) as error:
    status.update(label='Data preparation failed', state='error', expanded=True)
    st.error(str(error))
    st.stop()

ran_pipeline = False
total = 0
for item in pipeline_info.values():
    if item['ran']:
        ran_pipeline = True
    total += item['seconds']
if ran_pipeline:
    status.update(label=f'Ready · data preparation {total:.2f} s', state='complete', expanded=False)
else:
    status.update(label='Ready · using saved data and analysis', state='complete', expanded=False)


@st.cache_data(show_spinner=False)
def load_data(versions):
    # Include file modification times in the cache key to reload updated data.
    blocks = gpd.read_file(DATA/'processed/neighborhoods.geojson').to_crs(4326)
    schools = read_schools(DATA/'input')
    districts = gpd.read_file(DATA/'input/districts.geojson').to_crs(4326)
    records = read_crime(DATA/'input', blocks)
    gun_records = read_gun_incidents(DATA/'input',blocks)
    return blocks, schools, districts, records, gun_records


@st.cache_data(show_spinner=False)
def get_map_html(_frame, _districts, _schools, column, show_bg, show_schools, show_districts,
                 show_rings, show_crime, show_gun, crime_max, mean, std, unit, cache_key):
    # A neighborhood click keeps the cache key, map HTML and map view unchanged.
    records = load_data(cache_key[0])[3] if show_crime else gpd.GeoDataFrame()
    if not records.empty:
        records = records[records.GEOID.isin(_frame.GEOID)]
    gun_records = load_data(cache_key[0])[4] if show_gun else gpd.GeoDataFrame()
    if not gun_records.empty:
        gun_records = gun_records[gun_records.GEOID.isin(_frame.GEOID)]
    m = make_map(_frame, _districts, _schools, column, show_bg, show_schools, show_districts,
                 show_rings, mean, std, records, show_crime, crime_max, gun_records, show_gun)
    return m.get_root().render().replace(f'Mean: {mean}', f'Mean: {format_value(mean, unit)}')


paths = list((DATA/'input').glob('*')) + list((DATA/'processed').glob('*'))
paths += [BASE/name for name in ['app.py','housing.py','map_utils.py','dashboard.py',
                                'about_page.py','map_component/index.html']]
versions = []
for path in sorted(paths):
    if path.is_file():
        versions.append((str(path.relative_to(BASE)), path.stat().st_mtime_ns))
versions = tuple(versions)
bg, schools, districts, records, gun_records = load_data(versions)


def show_map():
    render_app(bg, schools, districts, versions, get_map_html, neighborhood_map,
               school_table, about_page)


def show_about():
    render_about(bg, map_page)


map_page = st.Page(show_map, title='Map', default=True)
about_page = st.Page(show_about, title='About', url_path='about')
st.navigation([map_page, about_page], position='hidden').run()
