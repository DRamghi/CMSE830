"""A short page about the study area, data sources and missing values."""
import streamlit as st

from prepare import CRIME_START, CRIME_END


def render_about(bg, map_page):
    st.markdown('''<style>
    [data-testid="stHeader"], [data-testid="stSidebar"] {display:none;}
    .block-container {max-width:1050px;padding:1rem 1.5rem;}
    h1 {font-size:1.8rem !important;}
    .about-section {border:1px solid #dce4e1;border-radius:10px;padding:14px 18px;margin:12px 0;}
    .about-section h3 {font-size:18px;color:#23483e;margin:0 0 8px;padding:0;}
    .about-section p,.about-section li {font-size:14px;line-height:1.6;}
    .about-section p {margin:5px 0;}
    .about-section ul {margin:0;padding-left:20px;}
    </style>''', unsafe_allow_html=True)
    st.page_link(map_page, label='← Back to map')
    st.title('About this page')
    st.markdown(f'''<section class="about-section"><h3>Study area · {len(bg)} block groups</h3>
    <p>Lansing · East Lansing · Okemos · Haslett</p>
    <p>At least 70% of each block group's area is within 10 km of MSU Main Library.
    Whole boundaries are shown. Township-labeled block groups are excluded.</p></section>
    <section class="about-section"><h3>Data sources</h3><ul>
    <li><a href="https://www.census.gov/data/developers/data-sets/planning-database.html">2026 Census Planning Database</a>:
    ACS 2020–2024 housing, income, adult education and population estimates.</li>
    <li><a href="https://api.census.gov/data/2024/acs/acs5/groups/B25064.html">2024 ACS 5-Year, B25064</a>: median gross rent.</li>
    <li><a href="https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html">2025 TIGER/Line</a>:
    Census block groups and place boundaries.</li>
    <li><a href="https://gisagocss.state.mi.us/arcgis/rest/services/CSS/Schools_Districts/MapServer">Michigan school GIS</a> and
    <a href="https://gisagocss.state.mi.us/arcgis/rest/services/OpenData/michigan_geographic_framework/MapServer/10">district GIS</a>:
    public school locations and district boundaries.</li>
    <li><a href="https://www.michigan.gov/mde/services/school-performance-supports/accountability/school-index">2024–25 MDE School Index</a>:
    school scores. The district value is the mean available OverallIndex of its schools.
    The Schools tab lists the same district schools, ordered by distance.</li>
    <li><a href="https://www.lansingmi.gov/crime-mapping">Lansing Police</a> and
    <a href="https://www.cityofeastlansing.com/358/Crime-Mapping">East Lansing Police / CrimeMapping.com</a>:
    police records, {CRIME_START} to {CRIME_END}. No separate Okemos / Haslett police feed is available.</li>
    <li><a href="https://www.gunviolencearchive.org/">Gun Violence Archive</a>:
    gun incidents for the same period, saved October 7, 2026. Approximate address-based locations;
    not added to police counts. Events may appear in both sources.</li>
    </ul></section>
    <section class="about-section"><h3>Missing values</h3>
    <p>Gray map areas and N/A mean data are unavailable. Source tables and analysis keep these values blank.</p>
    <p>Missing radar axes are drawn at the center to connect the polygon, labeled N/A in orange-brown.
    This does not mean an observed score of zero.</p>
    <p>For crime, zero means no published records in an area with data coverage.
    Missing coverage is not treated as zero crime.</p></section>
    <section class="about-section"><h3>AI use disclosure</h3>
    <p>I used ChatGPT 6.1 Sol to help find and combine datasets, map the data, and build the Streamlit app. I checked the outputs by running the code and reviewing tables, charts, and the app. I planned the project and made the final decisions about questions, data, and visualizations. I am responsible for validation, interpretation, conclusions, and explaining all submitted work.</p></section>''', unsafe_allow_html=True)
