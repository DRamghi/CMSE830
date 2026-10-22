"""Two-column layout. Cached HTML and a fragment preserve the map view on clicks."""
from html import escape

import pandas as pd
import streamlit as st

from housing import METRICS, PROFILE, format_value, radar_svg, grade_description, PEOPLE
from prepare import CRIME_START, CRIME_END, schools_in_study_area




def facts_html(items):
    html = ''
    for name, value in items:
        html += f'<div class="fact"><span>{escape(name)}</span><b>{escape(value)}</b></div>'
    return html


def rent_label(value):
    if value is None:
        return 'No limit'
    return f'${value:,}/mo'


def render_app(bg, schools, districts, versions, get_html, map_component, school_table, about_page):
    st.markdown('''<style>
    [data-testid="stHeader"], [data-testid="stSidebar"] {display:none;}
    .block-container {padding:.8rem 1.2rem .2rem;max-width:1800px;}
    [data-testid="stVerticalBlock"] {gap:.45rem;}
    [data-testid="stElementContainer"] {height:auto !important;flex-shrink:0 !important;}
    [data-testid="stHorizontalBlock"] {flex-wrap:nowrap !important;}
    [data-testid="stColumn"] {min-width:0 !important;}
    h1 {font-size:1.7rem !important;letter-spacing:-.5px;padding:0 0 .7rem !important;}
    h3 {font-size:1.2rem !important;padding:.1rem 0 !important;}
    p {margin:0 0 .25rem;line-height:1.4;}
    [data-testid="stCaptionContainer"] {font-size:12px;line-height:1.4;}
    [data-testid="stWidgetLabel"] p {font-size:14px;font-weight:650;}
    [data-baseweb="select"] > div {min-height:34px;}
    .st-key-main_controls [data-testid="stPopoverButton"] {padding:5px;min-height:36px;}
    .st-key-main_controls [data-testid="stPopoverButton"] p {white-space:nowrap;}
    .variable-label {font:600 14px Arial;white-space:nowrap;}
    .st-key-main_controls [data-testid="stWidgetLabel"] p {white-space:nowrap;}
    .st-key-title_row h1 {white-space:nowrap;}
    .st-key-filter_row {column-gap:32px !important;}
    .st-key-main_controls [data-testid="stElementContainer"]:has(> .stMarkdown .variable-label) {
      width:fit-content !important;flex:0 0 auto !important;height:40px !important;
      display:flex;align-items:center;}
    .st-key-main_controls .stMarkdown:has(.variable-label) {height:16px !important;}
    .st-key-main_controls [data-testid="stElementContainer"]:has([data-testid="stPageLink"]) {
      height:40px !important;display:flex;align-items:center;}
    .fact {display:flex;justify-content:space-between;font:14.7px Arial;line-height:1.45;
      padding:6px 0;border-bottom:1px solid #e0e3e5;gap:5px;}
    .fact b {white-space:nowrap;}
    .district {font:14.7px Arial;margin:8px 0;line-height:1.5;}
    .st-key-details {height:calc(100dvh - 32px) !important;max-height:calc(100dvh - 32px) !important;
      min-height:0 !important;flex:0 0 auto !important;overflow-y:auto;overflow-x:hidden;padding-right:5px;}
    .st-key-details [data-testid="stCaptionContainer"] {font-size:13.7px;}
    .neighborhood-heading h3 {padding:0 !important;margin:0;line-height:1.35;}
    .block-group-id {font:12.5px Arial;line-height:1.4;color:#6b7771;margin:7px 0 6px;}
    .layer-section {font:700 16.7px Arial;line-height:1.4;margin:16px 0 10px;}
    .layer-note {font:12px Arial;line-height:1.5;margin:0 0 10px 27px;color:#53635d;}
    .layer-note strong {color:#8b2929;}
    .st-key-details [data-testid="stExpander"] p {font-size:14.7px !important;line-height:1.6;}
    .st-key-details [data-testid="stTabs"] [role="tab"] p {font-size:15px;}
    .school-note {font:13.7px Arial;line-height:1.5;margin:0 0 16px;color:#53635d;}
    .school-facts {font:18.7px Arial;line-height:1.65;padding-left:18px;}
    .school-facts li {margin:9px 0;}
    [data-testid="stTabs"] [role="tablist"] {gap:12px;}
    @media(max-width:800px) {
      .block-container {padding:.5rem .6rem;}
      h1 {font-size:1.1rem !important;}
      h3 {font-size:1rem !important;}
      .variable-label {font-size:11px;}
      [data-testid="stWidgetLabel"] p {font-size:12px;}
      [data-baseweb="select"],button p {font-size:11px !important;}
      .fact {font-size:12.7px;flex-wrap:wrap;padding:5px 0;}
      .school-note {font:13.7px Arial;line-height:1.5;margin:0 0 16px;color:#53635d;}
    .school-facts {font-size:16.7px;}
      [data-testid="stColumn"]:has(.st-key-details) {min-width:170px !important;}
      .st-key-details [data-testid="stTabs"] [role="tablist"] {gap:6px;}
      .st-key-details [data-testid="stTabs"] [role="tab"] p {font-size:13.7px !important;}
      .st-key-details {height:calc(100dvh - 28px) !important;max-height:calc(100dvh - 28px) !important;}
    }
    </style>''',unsafe_allow_html=True)
    reference = bg
    map_schools = schools_in_study_area(schools)
    metrics = METRICS.copy()
    metrics['General crime'] = ('general_crime_count','count')
    if 'selected_bg' not in st.session_state:
        st.session_state.selected_bg = None

    # Split the page into columns first so the details panel starts at the top.
    @st.fragment
    def workspace():
        main, details = st.columns([4.2,1.15],gap='small')
        with main:
            with st.container(key='main_controls'):
                with st.container(horizontal=True,vertical_alignment='center',gap='medium',key='title_row'):
                    st.title("Find your family's neighborhood near MSU",width='content')
                    if st.button('About this page'):
                        st.switch_page(about_page)
                # Keep filters in one row to leave more vertical space for the map.
                with st.container(horizontal=True,vertical_alignment='center',gap='medium',key='filter_row'):
                    with st.container(horizontal=True,vertical_alignment='center',gap='small',width=354):
                        st.markdown('<div class="variable-label">Select Variables :</div>',unsafe_allow_html=True,width=118)
                        label = st.selectbox('Select Variables',list(metrics),index=1,label_visibility='collapsed',width=225)
                    column,unit = metrics[label]
                    with st.container(horizontal=True,vertical_alignment='center',gap='small',width=295):
                        st.markdown('<div class="variable-label">Median rent limit :</div>',unsafe_allow_html=True,width=130)
                        budget = st.selectbox('Median rent limit',[None,800,1000,1200,1500,1800,2000,2500,3000],
                            format_func=rent_label,
                            label_visibility='collapsed',width=150)
                    with st.popover('Layers & area'):
                        st.markdown('<div class="layer-section" style="margin-top:4px">Area</div>',unsafe_allow_html=True)
                        # Read the four study areas from the data. Preprocessing excludes Township block groups.
                        area_options = []
                        for names in reference.area_names:
                            for area in str(names).split(' / '):
                                if area not in area_options:
                                    area_options.append(area)
                        area_options.sort()
                        areas = st.multiselect('Area',area_options,default=area_options,
                            label_visibility='collapsed',key='map_areas')
                        st.markdown('<div class="layer-section">Layers</div>',unsafe_allow_html=True)
                        show_bg = st.checkbox('Census block groups',True)
                        with st.container(horizontal=True,vertical_alignment='center',gap='small'):
                            show_schools = st.checkbox('Public schools',True)
                            school_layers = st.multiselect('School marker levels',['Elementary','Middle','High'],
                                default=['Elementary','Middle','High'],label_visibility='collapsed',
                                key='school_marker_levels',
                                help='Choose the levels shown on the map. Combined schools appear if a selected level is offered.')
                        show_districts = st.checkbox('School district boundaries',False)
                        show_rings = st.checkbox('MSU & distance rings',True)
                        period = f'{pd.Timestamp(CRIME_START):%b %d} ~ {pd.Timestamp(CRIME_END):%b %d, %Y}'
                        show_crime = st.checkbox(f'Crime incident locations ({period})',value=column == 'general_crime_count')
                        st.markdown('<div class="layer-note">'
                            '<strong>Lansing and East Lansing only.<br>Okemos / Haslett police data unavailable.</strong></div>',
                            unsafe_allow_html=True)
                        show_gun = st.checkbox(f'GVA gun incident locations ({period})',False,
                            key='show_gun_locations')
                        st.markdown('<div class="layer-note">Approximate address-based locations.<br>'
                            'Not added to General crime; events may also appear in police records.</div>',unsafe_allow_html=True)
            mask = []
            for names in reference.area_names:
                selected_area = False
                for area in str(names).split(' / '):
                    if area in areas:
                        selected_area = True
                        break
                mask.append(selected_area)
            filtered = reference[mask].copy()
            if budget is not None:
                filtered = filtered[filtered[METRICS['Monthly rent'][0]].le(budget)]
            # School-level filters affect map markers only. The details tab lists the whole district.
            school_mask = []
            for levels in map_schools.levels:
                selected_level = False
                for level in levels:
                    if level in school_layers:
                        selected_level = True
                        break
                school_mask.append(selected_level)
            visible_schools = map_schools[school_mask]
            if st.session_state.selected_bg not in filtered.GEOID.tolist():
                st.session_state.selected_bg = None
            if filtered.empty:
                st.info('No matching block groups. Choose an area or increase the rent limit.')
            # Reuse the cached HTML on block-group clicks to preserve the iframe and map view.
            crime_max = 1
            if reference[column].notna().any():
                crime_max = max(1, float(reference[column].max()))
            html = get_html(filtered,districts,visible_schools,column,show_bg,show_schools,show_districts,show_rings,
                show_crime,show_gun,crime_max,
                float(reference[column].mean()),float(reference[column].std(ddof=0)),unit,
                cache_key=(versions,tuple(filtered.GEOID),tuple(visible_schools.school_name)))
            result = map_component(html=html,key='housing_map',default=None)
            if result and result.get('geoid') in filtered.GEOID.values:
                st.session_state.selected_bg = result['geoid']
        with details,st.container(key='details'):
            selected = st.session_state.selected_bg
            if selected is None:
                st.subheader('Neighborhood')
                st.caption('Click a block group on the map.')
                return
            row = reference[reference.GEOID.eq(selected)].iloc[0]
            # area_names lists places in descending order of overlap with the whole block group.
            # Keep both lines in one HTML block so the ID follows the full height of the title.
            st.markdown(f'<div class="neighborhood-heading"><h3>City : {escape(str(row.area_names))}</h3>'
                f'<div class="block-group-id">Block group {escape(str(row.GEOID))}</div></div>',unsafe_allow_html=True)
            profile_tab,schools_tab,people_tab = st.tabs(['Profile','Schools','People'])
            with profile_tab:
                st.image(radar_svg(row,7),width='stretch')
                profile_facts = []
                for name, (col, kind, lower_is_better) in PROFILE.items():
                    profile_facts.append((name, format_value(row.get(col), kind)))
                st.markdown(facts_html(profile_facts),unsafe_allow_html=True)
            with schools_tab:
                district_schools = school_table(row,schools)
                district_name = row.district_name if pd.notna(row.district_name) else 'Unknown district'
                st.markdown(f'<div class="school-note"><b>{escape(str(district_name))}</b> · '
                    f'{len(district_schools)} schools.<br>'
                    'All schools in the district containing the block-group center. '
                    'This list does not confirm which school a child would be assigned to.</div>',unsafe_allow_html=True)
                if district_schools.empty:
                    st.info('No district school information is available for this block group.')
                for _,school in district_schools.iterrows():
                    with st.expander(school.school_name):
                        if pd.notna(school.distance_km):
                            distance = f'{school.distance_km:.2f} km'
                        elif 'FTVirtual' in str(school.educational_settings):
                            distance = 'N/A (online school)'
                        else:
                            distance = 'N/A (location unavailable)'
                        items = [grade_description(school.grades),f'Distance: {distance}',
                                 f'District: {school.operating_district}']
                        for name,col in [('Overall','school_index'),('Proficiency','proficiency_index'),('Growth','growth_index'),('EL progress','el_progress_index')]:
                            value = school[col]
                            if pd.isna(value):
                                score = 'No data'
                            else:
                                score = f'{value:.1f}/100'
                            items.append(f'{name}: {score}')
                        school_html = '<ul class="school-facts">'
                        for value in items:
                            school_html += f'<li>{escape(value)}</li>'
                        school_html += '</ul>'
                        st.markdown(school_html,unsafe_allow_html=True)
            with people_tab:
                st.caption('ACS 2020–2024 estimates.')
                people_facts = []
                for name, col in PEOPLE.items():
                    people_facts.append((name, format_value(row.get(col), 'percent')))
                st.markdown(facts_html(people_facts),unsafe_allow_html=True)
    workspace()
