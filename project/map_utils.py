"""Build maps and popups. Calculations are in prepare.py and page layout is in dashboard.py."""
from html import escape
import json

from branca.colormap import LinearColormap
from branca.element import MacroElement, Template
import folium
from folium.plugins import FastMarkerCluster, MarkerCluster
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from housing import COLORS, LOWER_IS_BETTER, MSU_LAT, MSU_LON, SCHOOL_COLORS, grade_description
from prepare import study_boundary


def record_html(row):
    """Use the same record date, category and agency in the map and detail list."""
    date = pd.Timestamp(row.occurred_at).strftime('%b %d, %Y · %H:%M')
    return (f'<b>{escape(date)}</b><br>{escape(str(row.category))}<br>'
            f'<small>{escape(str(row.agency))}</small>')


CRIME_COLORS = ['#fee5d9', '#fb6a4a', '#99000d']


def metric_style(value, mean, std, column):
    """Keep source values and change only color direction. The mean is neutral and the preferred direction is blue."""
    scale = LinearColormap([COLORS[0],COLORS[3],COLORS[-1]],vmin=-2,vmax=2)
    z = (value - mean) / std if pd.notna(value) and std else 0
    if column in LOWER_IS_BETTER:
        z = -z
    return {'fillColor':scale(z) if pd.notna(value) else '#8b9098',
            'color':'#5b5860','weight':.6,'fillOpacity':.62}


def school_background(levels):
    """Combined school markers use equal segments for offered levels, not enrollment shares."""
    colors = [SCHOOL_COLORS[level] for level in levels]
    if len(colors) == 1:
        return colors[0]
    stops = []
    for i, color in enumerate(colors):
        start = i * 360 / len(colors)
        end = (i + 1) * 360 / len(colors)
        stops.append(f'{color} {start:g}deg {end:g}deg')
    return 'conic-gradient(' + ','.join(stops) + ')'


def crime_style(value, maximum):
    # Unavailable data are gray; zero records are transparent. Do not use mean or standard deviation.
    if pd.isna(value):
        color, opacity = '#8b9098', .62
    elif value == 0:
        color, opacity = '#ffffff', 0
    else:
        scale = LinearColormap(CRIME_COLORS, vmin=1, vmax=max(2, maximum))
        color, opacity = scale(float(value)), .62
    return {'fillColor':color, 'fillOpacity':opacity, 'color':'#5b5860', 'weight':.6}


def location_data(records):
    """Keep every record at a shared public coordinate in one point popup."""
    points = []
    ordered = records.sort_values('occurred_at', ascending=False)
    for _, group in ordered.groupby(['x', 'y'], sort=False):
        point = group.geometry.iloc[0]
        items = []
        for row in group.itertuples():
            items.append('<li style="margin:10px 0">' + record_html(row) + '</li>')
        popup = (f'<div style="font:14px Arial;line-height:1.5;min-width:240px">'
                 f'<b>{len(group)} published record(s) at this location</b>'
                 '<ul style="max-height:250px;overflow-y:auto;padding-left:18px;margin:8px 0">'
                 + ''.join(items) + '</ul>'
                 '<small style="color:#697078">Source-provided date/time. Published location may be approximate.</small></div>')
        points.append([point.y, point.x, len(group), popup])
    return points


def add_crime_points(map_object, records):
    # Send a compact array and build markers in the browser instead of generating thousands of HTML elements.
    # Group shared locations into one marker so overlapping records remain accessible when zoomed in.
    callback = '''function(row) {
      const count = row[2];
      const size = count > 1 ? 22 : 12;
      const icon = L.divIcon({className:'crime-location', iconSize:[size,size], iconAnchor:[size/2,size/2],
        html:'<div style="width:'+size+'px;height:'+size+'px;background:#b91c1c;border:0;'
          +'border-radius:50%;box-shadow:0 1px 3px #0006;text-align:center;color:white;font:600 11px Arial;'
          +'line-height:'+size+'px">'+(count > 1 ? count : '')+'</div>'});
      return L.marker([row[0],row[1]], {icon:icon, recordCount:count, bubblingMouseEvents:false,
        title:'Crime location: '+count+' published record(s)'}).bindPopup(row[3], {maxWidth:340});
    }'''
    # Cluster labels count records, not distinct coordinates.
    cluster_icon = '''function(cluster) {
      const markers = cluster.getAllChildMarkers();
      let count = 0;
      for (const marker of markers) {
        count += marker.options.recordCount;
      }
      return L.divIcon({className:'crime-cluster',iconSize:[34,34],
        html:'<div style="width:34px;height:34px;background:#b91c1c;border:0;border-radius:50%;'
          +'color:white;text-align:center;font:bold 12px Arial;line-height:34px">'+count+'</div>'});
    }'''
    FastMarkerCluster(location_data(records), callback=callback, icon_create_function=cluster_icon,
                      name='Crime incident locations', disableClusteringAtZoom=17).add_to(map_object)


def school_table(row, schools):
    """List the same district schools used for the radar school score."""
    district_schools = schools[schools.operating_district_code.eq(row.get('district_code'))].copy()
    center = gpd.GeoSeries([Point(row.centroid_lon, row.centroid_lat)], crs=4326).to_crs(26916).iloc[0]
    district_schools['distance_km'] = district_schools.to_crs(26916).geometry.distance(center) / 1000
    # Keep online and unlocated schools in the district list and its score mean.
    # An online school's office location is not a physical school distance.
    district_schools.loc[~district_schools.distance_eligible, 'distance_km'] = float('nan')
    return district_schools.sort_values(['distance_km', 'school_name'], na_position='last')


def gun_record_html(row):
    """GVA provides dates only; do not invent incident times."""
    date = pd.Timestamp(row.occurred_at).strftime('%b %d, %Y')
    return (f'<div style="font:13px Arial;line-height:1.5;max-width:320px">'
            f'<b>GVA gun incident · {escape(date)}</b><br>'
            f'{escape(str(row.characteristics))}<br>'
            f'Victims: {int(row.victims_killed)} killed, {int(row.victims_injured)} injured<br>'
            f'Suspects: {int(row.suspects_killed)} killed, {int(row.suspects_injured)} injured<br>'
            f'<small>{escape(str(row.location_precision))}</small><br>'
            f'<a href="{escape(row.incident_url,quote=True)}" target="_blank" rel="noopener noreferrer">GVA incident {escape(row.incident_id)}</a>'
            '<br><small>Gun Violence Archive · saved Oct 7, 2026. Location is approximate.</small></div>')


def add_gun_points(map_object, records):
    """GVA is a separate point layer. Do not add it to general crime counts or block-group colors."""
    layer = folium.FeatureGroup(name='GVA gun incident locations').add_to(map_object)
    # Group incidents at the same location in one popup so one marker does not hide another record.
    for _, group in records.sort_values('occurred_at',ascending=False).groupby(['longitude','latitude']):
        text = '<hr>'.join(gun_record_html(row) for row in group.itertuples())
        point = group.geometry.iloc[0]
        label = 'G' if len(group) == 1 else f'G{len(group)}'
        folium.Marker([point.y,point.x],record_count=len(group),
            icon=folium.DivIcon(class_name='gun-location',icon_size=(24,24),icon_anchor=(12,12),
                html='<div style="width:24px;height:24px;border-radius:50%;background:#111111;color:white;text-align:center;font:bold 11px Arial;line-height:24px">'+label+'</div>'),
            popup=folium.Popup('<div style="max-height:300px;overflow-y:auto">'+text+'</div>',max_width=340),
            tooltip=f'{len(group)} GVA gun incident(s)').add_to(layer)


def make_map(frame, districts, schools, column, show_bg, show_schools, show_districts, show_rings,
             mean, std, crime_records, show_crime, crime_max, gun_records=None, show_gun=False):
    m = folium.Map(location=[42.729, -84.48], zoom_start=11,
                   tiles="OpenStreetMap", control_scale=False, zoom_snap=.25, zoom_delta=.5)
    # Fit the initial view to the 10 km circle so large outer block groups do not make the map too small.
    # Keep whole block-group polygons, including boundaries extending beyond the circle.
    xmin, ymin, xmax, ymax = gpd.GeoSeries([study_boundary()],crs=26916).to_crs(4326).total_bounds
    bounds = folium.map.FitBounds([[ymin,xmin],[ymax,xmax]],padding=(8,8))
    bounds.options['animate'] = False
    bounds.add_to(m)
    # Reduce transfer size without changing the geographic unit of Census statistics.
    display = frame[["GEOID", column, "geometry"]].to_crs(26916)
    display.geometry = display.geometry.simplify(5, preserve_topology=True)
    display = display.to_crs(4326)

    def style(feature):
        value = feature["properties"].get(column)
        if column == 'general_crime_count':
            return crime_style(value, crime_max)
        return metric_style(value,mean,std,column)

    # Send only the clicked feature GEOID through a browser event; do not show hover popups.
    polygons = folium.GeoJson(json.loads(display.to_json()), name="Block groups", show=show_bg,
                             style_function=style).add_to(m)
    if show_crime and not crime_records.empty:
        add_crime_points(m, crime_records)
    if show_gun and gun_records is not None:
        add_gun_points(m,gun_records)
    rings = folium.FeatureGroup(name="MSU & distance rings", show=show_rings).add_to(m)
    for km in [5, 10]:
        folium.Circle([MSU_LAT, MSU_LON], radius=km * 1000, color="#5c5363", weight=1.3,
                      dash_array="5,5", fill=False, interactive=False).add_to(rings)
        # Use about 111 km per latitude degree only for label placement. Leaflet measures ring radii in meters.
        folium.Marker([MSU_LAT + km / 111.2, MSU_LON], interactive=False,
                      icon=folium.DivIcon(class_name='distance-label',html=f'<span style="white-space:nowrap;font:600 11px Arial;background:#fffe;padding:2px 5px;border-radius:4px">{km} km</span>')).add_to(rings)
    def district_style(feature):
        return {"fill": False, "color": "#6b4d85", "weight": 2,
                "dashArray": "6,4", "interactive": False}

    folium.GeoJson(districts[["district_name", "geometry"]], name="School districts", show=show_districts,
                   style_function=district_style).add_to(m)
    if show_schools:
        clusters = {}
        level_groups = []
        for levels in schools.levels:
            key = tuple(levels)
            if key not in level_groups:
                level_groups.append(key)
        for levels in level_groups:
            background = school_background(levels)
            # Keep school-level colors when markers cluster at lower zoom levels.
            icon = ("function(cluster) {return L.divIcon({className:'school-cluster',html:'<div style=\"background:" + background
                    + ";color:white;border:0;border-radius:50%;width:28px;height:28px;text-align:center;font:bold 11px Arial;line-height:28px\">'"
                    + "+cluster.getChildCount()+'</div>',iconSize:[28,28]});}")
            clusters[levels] = MarkerCluster(name=' / '.join(levels) + " schools", disableClusteringAtZoom=13,
                                            icon_create_function=icon).add_to(m)
        for _, school in schools.iterrows():
            level = school.levels[0] if len(school.levels) == 1 else "Combined"
            scores = [("Overall", school.school_index), ("Proficiency", school.proficiency_index),
                      ("Growth", school.growth_index), ("English learner progress", school.el_progress_index)]
            score_lines = []
            for name, value in scores:
                if pd.notna(value):
                    score_lines.append(f"{name}: {value:.1f}")
            score_text = "<br>".join(score_lines)
            if not score_text:
                score_text = "No data"
            district = "No data" if pd.isna(school.operating_district) else escape(school.operating_district)
            # Show the school name only in the title and omit the address. Escape external text.
            text = (f'<div style="font:13px Arial;line-height:1.45;min-width:240px">'
                    f'<b style="font-size:15px">{escape(school.school_name)}</b>'
                    '<ul style="padding-left:18px;margin:9px 0">'
                    f'<li style="margin:7px 0">Level: {escape(" / ".join(school.levels))}</li>'
                    f'<li style="margin:7px 0">{escape(grade_description(school.grades))}</li>'
                    f'<li style="margin:7px 0">District: {district}</li>'
                    f'<li style="margin:7px 0">2024–25 indices /100<br>{score_text}</li></ul>'
                    '<div style="font-size:10px;color:#70757a">Location does not establish enrollment eligibility.</div></div>')
            letter = {"Elementary": "E", "Middle": "M", "High": "H", "Combined": ""}[level]
            html = (f'<div style="width:22px;height:22px;background:{school_background(school.levels)};border:0;'
                    'border-radius:50%;box-shadow:0 1px 4px #0007;text-align:center;color:white;font:bold 11px Arial;line-height:22px">'
                    f'{letter}</div>')
            folium.Marker([school.geometry.y, school.geometry.x],
                          icon=folium.DivIcon(class_name='school-marker',html=html, icon_size=(22, 22), icon_anchor=(11, 11)),
                          popup=folium.Popup(text, max_width=340)).add_to(clusters[tuple(school.levels)])
    # Use a simple pin to mark the reference point for all distances.
    pin = ('<svg width="28" height="36" viewBox="0 0 28 36" xmlns="http://www.w3.org/2000/svg">'
           '<path d="M14 1C7 1 1 6.3 1 13c0 9 13 22 13 22s13-13 13-22C27 6.3 21 1 14 1Z" fill="#204d3f"/>'
           '<circle cx="14" cy="13" r="4" fill="#f7f9f8"/></svg>')
    folium.Marker([MSU_LAT,MSU_LON],icon=folium.DivIcon(class_name='msu-reference-point',
                  html=pin,icon_size=(28,36),icon_anchor=(14,36)),tooltip='MSU Main Library reference point').add_to(rings)
    folium.Marker([MSU_LAT, MSU_LON], icon=folium.DivIcon(class_name='msu-marker',
        icon_size=(130,24),icon_anchor=(-12,26),
        html='<div style="background:#263e36;color:white;font:bold 11px Arial;border-radius:4px;padding:4px;width:110px">MSU Main Library</div>'),
        interactive=False).add_to(rings)
    # Put the legend inside the map to avoid extra page height and overlapping wrapped text.
    low_is_blue = column in LOWER_IS_BETTER
    if low_is_blue:
        left, right = 'Higher value', 'Lower value'
    else:
        left, right = 'Lower value', 'Higher value'
    legend = ''
    if show_bg:
        legend = (f'<div style="display:flex;justify-content:space-between"><span>{left}</span><span>{right}</span></div>'
              f'<div style="height:10px;margin:4px 0;background:linear-gradient(to right,{COLORS[0]},{COLORS[3]},{COLORS[-1]})"></div>'
              f'<div style="text-align:center">Mean: {escape(str(mean))} · gray: no data</div>')
    if show_bg and column == 'general_crime_count':
        # Fix the maximum across the study area so filtering does not change the color scale.
        record_label = 'General crime'
        legend = (f'<div>{record_label} · 0 = no fill</div>'
                  f'<div style="height:10px;margin:4px 0;background:linear-gradient(to right,{",".join(CRIME_COLORS)})"></div>'
                  f'<div style="display:flex;justify-content:space-between"><span>1</span><span>{crime_max:,.0f}</span></div>'
                  '<div>Gray: no data</div>')
    if show_crime:
        legend += '<div style="margin-top:4px;color:#b91c1c">● Crime locations · click for date & type</div>'
    if show_gun:
        legend += '<div style="margin-top:4px;color:#111111">● G: GVA gun incidents · approximate locations</div>'
    if show_schools:
        legend += '<div style="margin-top:4px">' + " · ".join(f'<span style="color:{SCHOOL_COLORS[name]}">● {name}</span>' for name in ['Elementary','Middle','High']) + '</div>'
        legend += (f'<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{school_background(["Elementary","Middle","High"])}"></span>'
                   ' Split colors: combined school levels</div>')
    if legend:
        m.get_root().html.add_child(folium.Element(
        '<div style="position:fixed;bottom:24px;left:12px;max-width:calc(100% - 24px);min-width:230px;z-index:1000;'
        'background:#fffffff0;padding:7px 9px;border-radius:5px;pointer-events:none;font:12px Arial;line-height:1.4">'
            + legend + '</div>'))
    # Add only the needed map events to Folium. Exclude school markers from block-group events.
    bridge = MacroElement()
    bridge._template = Template('''{% macro script(this, kwargs) %}
    const map = {{this.map_name}}, groups = {{this.group_name}};
    let chosen = null;
    function highlight(id) {
      chosen = id;
      groups.eachLayer(function(layer) {groups.resetStyle(layer);
        if(layer.feature.properties.GEOID === id) layer.setStyle({color:'#27212b',weight:3});});
    }
    groups.eachLayer(function(layer) {
      layer.on('click', function(event) {
        L.DomEvent.stopPropagation(event); highlight(layer.feature.properties.GEOID);
        window.parent.postMessage({type:'block-click',geoid:chosen},'*');
      });
    });
    map.on('moveend zoomend', function() {
      window.parent.postMessage({type:'map-view',
        view:{center:[map.getCenter().lat,map.getCenter().lng],zoom:map.getZoom()}},'*');
    });
    window.addEventListener('message', function(event) {
      if(event.source !== window.parent) return;
      if(event.data.type === 'resize-map') {map.invalidateSize({pan:false});}
      if(event.data.type === 'restore-map') {
        const view = event.data.view;
        if(view) map.setView(view.center,view.zoom,{animate:false});
        highlight(event.data.selected);
      }
    });
    document.getElementById(map.getContainer().id).style.height='100vh';
    map.invalidateSize({pan:false});
    window.parent.postMessage({type:'map-ready'},'*');
    {% endmacro %}''')
    bridge.map_name, bridge.group_name = m.get_name(), polygons.get_name()
    m.add_child(bridge)
    return m
