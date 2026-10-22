"""Combine local extracts into one block-group dataset. Run: python prepare.py"""
from pathlib import Path
from time import perf_counter

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from housing import MSU_LAT, MSU_LON, STUDY_RADIUS_KM, MIN_STUDY_SHARE, add_tiers, school_levels, METRICS, PROFILE, PEOPLE

BASE = Path(__file__).resolve().parent
DATA = BASE / 'data'
INPUT_FILES = ['census.csv', 'block_groups.geojson', 'schools.csv',
               'districts.geojson', 'crime.csv', 'crime_coverage.csv', 'gun_incidents.csv']
CRIME_START, CRIME_END = '2026-04-10', '2026-10-06'


def study_boundary():
    """Use the same 10 km circle for distance limits and block-group area shares. Units are meters."""
    anchor = gpd.GeoSeries([Point(MSU_LON, MSU_LAT)], crs=4326).to_crs(26916).iloc[0]
    return anchor.buffer(STUDY_RADIUS_KM * 1000, quad_segs=128)


def schools_in_study_area(schools):
    """Limit school locations to the circle. District means use all schools in the input, including those outside it."""
    points = schools.to_crs(26916)
    return schools[points.geometry.notna() & points.geometry.intersects(study_boundary())].copy()


def clean_number(series):
    """Remove commas and currency symbols. Treat special negative Census values as missing."""
    text = series.astype('string').str.replace(r'[$,%]', '', regex=True).str.strip()
    values = pd.to_numeric(text, errors='coerce').astype(float)
    return values.where(values >= 0)


def read_schools(input_dir):
    """Read school scores and map locations from one table."""
    schools = pd.read_csv(input_dir / 'schools.csv', dtype={
        'school_id':str, 'operating_district_code':str})
    schools['operating_district_code'] = schools.operating_district_code.str.zfill(5)
    for col in ['school_index', 'proficiency_index', 'growth_index', 'el_progress_index']:
        schools[col] = pd.to_numeric(schools[col], errors='coerce')
    located = schools[['longitude','latitude']].notna().all(axis=1)
    geometry = gpd.points_from_xy(schools.longitude, schools.latitude)
    schools = gpd.GeoDataFrame(schools, geometry=geometry, crs=4326)
    schools.loc[~located, 'geometry'] = None
    schools['distance_eligible'] = schools.distance_eligible.astype('string').str.lower().eq('true').fillna(False)
    schools['levels'] = [school_levels(str(row.grades), row.school_name) for row in schools.itertuples()]
    # For schools such as grades 5-6 Intermediate, grade ranges may differ from the official school level.
    # Use the input override when it was checked against official district information.
    if 'level_override' in schools:
        for index in schools.index[schools.level_override.notna()]:
            schools.at[index,'levels'] = schools.at[index,'level_override'].split(' / ')
    return schools


def read_crime(input_dir, blocks):
    """Read located police records and match each point to its block group."""
    crime = pd.read_csv(input_dir / 'crime.csv', dtype={'record_id':str})
    # Remove exact duplicate records only. Do not guess matches between different agencies.
    crime = crime.drop_duplicates()
    crime['occurred_at'] = pd.to_datetime(crime.occurred_at, errors='coerce')
    end = pd.Timestamp(CRIME_END) + pd.Timedelta(days=1)
    crime = crime[crime.occurred_at.ge(CRIME_START) & crime.occurred_at.lt(end)]
    crime = crime.dropna(subset=['longitude','latitude'])
    points = gpd.GeoDataFrame(crime, geometry=gpd.points_from_xy(crime.longitude, crime.latitude), crs=4326)
    points = gpd.sjoin(points, blocks[['GEOID','geometry']], how='inner', predicate='intersects')
    # Count a record on a shared boundary in only one block group.
    points = points.sort_values('GEOID').drop_duplicates('record_id').drop(columns='index_right')
    points['x'], points['y'] = points.geometry.x, points.geometry.y
    return points


def read_gun_incidents(input_dir, blocks):
    """Read the saved GVA extract as map points, separate from general crime counts."""
    gun = pd.read_csv(input_dir / 'gun_incidents.csv', dtype={'incident_id':str})
    gun['occurred_at'] = pd.to_datetime(gun.occurred_at, errors='coerce')
    end = pd.Timestamp(CRIME_END) + pd.Timedelta(days=1)
    gun = gun[gun.occurred_at.ge(CRIME_START) & gun.occurred_at.lt(end)]
    # Keep the unlocated incident in the source CSV, but do not invent a map location.
    gun = gun.dropna(subset=['longitude','latitude']).drop_duplicates('incident_id')
    points = gpd.GeoDataFrame(gun,geometry=gpd.points_from_xy(gun.longitude,gun.latitude),crs=4326)
    points = gpd.sjoin(points,blocks[['GEOID','geometry']],how='inner',predicate='intersects')
    return points.sort_values('GEOID').drop_duplicates('incident_id').drop(columns='index_right')


def prepare_data(data_dir=DATA):
    """Calculate from local input files without live downloads or extra intermediate files."""
    input_dir, output_dir = data_dir / 'input', data_dir / 'processed'
    output_dir.mkdir(exist_ok=True)
    blocks = gpd.read_file(input_dir / 'block_groups.geojson').to_crs(4326)
    blocks['GEOID'] = blocks.GEOID.astype(str)
    blocks = blocks[~blocks.area_names.str.contains('township',case=False,na=False)].copy()
    census = pd.read_csv(input_dir / 'census.csv', dtype={'GEOID':str})
    for col in census:
        if 'ACS_' in col or 'ACSMOE_' in col or col == 'rent_moe':
            census[col] = clean_number(census[col])
    # Join Census statistics and boundaries by GEOID. Each block group must have one row.
    blocks = blocks.merge(census, on='GEOID', how='left', validate='one_to_one')
    # Keep block groups with at least 70% of their whole area inside the 10 km circle.
    # Use whole block groups for boundaries, statistics and centers. Do not clip at the circle.
    projected = blocks.to_crs(26916)
    share = projected.intersection(study_boundary()).area / projected.area
    blocks = blocks[share.ge(MIN_STUDY_SHARE)].copy()
    blocks['within_10km_pct'] = share.loc[blocks.index] * 100

    # Calculate in a meter-based coordinate system, then convert to km. Do not use degree differences as distances.
    projected = blocks.to_crs(26916)
    centers = gpd.GeoDataFrame({'GEOID':blocks.GEOID}, geometry=projected.geometry.centroid, crs=26916)
    anchor = gpd.GeoSeries([Point(MSU_LON, MSU_LAT)], crs=4326).to_crs(26916).iloc[0]
    blocks['distance_msu_km'] = centers.geometry.distance(anchor).to_numpy() / 1000
    coordinates = centers.to_crs(4326)
    blocks['centroid_lon'], blocks['centroid_lat'] = coordinates.geometry.x.to_numpy(), coordinates.geometry.y.to_numpy()

    schools = read_schools(input_dir)
    districts = gpd.read_file(input_dir / 'districts.geojson').to_crs(26916)
    districts['district_id'] = districts.district_id.astype(str).str.zfill(5)
    districts['DCODE'] = districts.DCODE.astype(str).str.zfill(5)
    # Use the district containing the block-group center as its representative district.
    # This district is a comparison reference, not a verified school assignment for each home.
    assigned = gpd.sjoin(centers, districts, how='left', predicate='within').drop_duplicates('GEOID').set_index('GEOID')
    blocks['district_id'] = blocks.GEOID.map(assigned.district_id)
    blocks['district_name'] = blocks.GEOID.map(assigned.district_name)
    blocks['district_code'] = blocks.GEOID.map(assigned.DCODE)
    school_means = schools.groupby('operating_district_code').school_index.mean()
    blocks['district_overall_mean'] = blocks.district_code.map(school_means)

    candidates = schools_in_study_area(schools)
    candidates = candidates[candidates.distance_eligible].to_crs(26916)
    nearest = gpd.sjoin_nearest(centers, candidates[['school_name','geometry']], distance_col='distance_m')
    nearest = nearest.drop_duplicates('GEOID').set_index('GEOID')
    blocks['nearest_school_km'] = blocks.GEOID.map(nearest.distance_m) / 1000
    blocks['nearest_school_name'] = blocks.GEOID.map(nearest.school_name)

    crime = read_crime(input_dir, blocks)
    coverage = pd.read_csv(input_dir / 'crime_coverage.csv', dtype={'GEOID':str}).set_index('GEOID')
    blocks['crime_coverage'] = blocks.GEOID.map(coverage.crime_coverage).fillna('Unavailable')
    counts = blocks.GEOID.map(crime.groupby('GEOID').record_id.nunique()).fillna(0)
    # An empty list in an uncovered area is not evidence of zero crime. Preserve coverage status.
    blocks['general_crime_count'] = counts.where(blocks.crime_coverage.ne('Unavailable'))
    blocks = add_tiers(blocks).sort_values(['distance_msu_km','GEOID']).reset_index(drop=True)
    blocks.to_file(output_dir / 'neighborhoods.geojson', driver='GeoJSON')
    return blocks


def analysis_columns():
    """Use numeric map, profile and population columns without duplicates."""
    columns = [col for col,_ in METRICS.values()]
    columns += [col for col,_,_ in PROFILE.values()]
    columns += list(PEOPLE.values())
    unique_columns = []
    for column in columns:
        if column not in unique_columns:
            unique_columns.append(column)
    return unique_columns


def run_analysis(data_dir=DATA):
    blocks = gpd.read_file(data_dir / 'processed/neighborhoods.geojson')
    columns = analysis_columns()
    # Save counts, medians and quartiles as well as means to describe the distributions.
    # Count means block groups with a value for this variable, not all block groups.
    rows = []
    for city, group in blocks.groupby('area_name'):
        for column in columns:
            values = pd.to_numeric(group[column], errors='coerce')
            rows.append({'city':city, 'variable':column, 'count':values.count(),
                'mean':values.mean(), 'median':values.median(),
                'q25':values.quantile(.25), 'q75':values.quantile(.75)})
    summary = pd.DataFrame(rows)
    # Keep missing values. Correlations use rows with values in both columns.
    numeric = blocks[columns].copy()
    for column in columns:
        numeric[column] = pd.to_numeric(numeric[column], errors='coerce')
    correlations = numeric.corr()
    output = data_dir / 'processed'
    output.mkdir(exist_ok=True)
    summary.to_csv(output / 'summary.csv', index=False)
    correlations.to_csv(output / 'correlations.csv', index_label='variable')
    return summary, correlations


def needs_update(outputs, inputs):
    """Rebuild if outputs are missing or inputs and calculation code are newer."""
    output_times = []
    for path in outputs:
        if not path.exists():
            return True
        output_times.append(path.stat().st_mtime_ns)
    input_times = []
    for path in inputs:
        input_times.append(path.stat().st_mtime_ns)
    return max(input_times) > min(output_times)


def ensure_data(progress=None, data_dir=DATA):
    """Share this pipeline between the app and notebook. The callback reports progress."""
    inputs = []
    missing = []
    for name in INPUT_FILES:
        path = data_dir / 'input' / name
        inputs.append(path)
        if not path.exists():
            missing.append(name)
    if missing:
        raise FileNotFoundError('Missing input files: ' + ', '.join(missing))
    processed = data_dir / 'processed' / 'neighborhoods.geojson'
    reports = [data_dir / 'processed' / name for name in ['summary.csv','correlations.csv']]
    # Use file modification times for the two pipeline stages.
    stages = [
        ('Preprocessing', [processed], inputs + [BASE/'prepare.py', BASE/'housing.py']),
        ('Analysis', reports, [processed, BASE/'prepare.py', BASE/'housing.py']),
    ]
    result = {}
    for name, outputs, sources in stages:
        needed = needs_update(outputs, sources)
        start = perf_counter()
        if progress:
            if needed:
                progress(name, 'running', 0)
            else:
                progress(name, 'cached', 0)
        if needed:
            if name == 'Preprocessing':
                prepare_data(data_dir)
            else:
                run_analysis(data_dir)
        seconds = perf_counter() - start
        result[name] = {'ran':needed, 'seconds':seconds}
        if progress and needed:
            progress(name, 'complete', seconds)
    return result


def print_progress(stage, state, seconds):
    """Print the pipeline status when running this file or the notebook."""
    print(f'{stage}: {state} ({seconds:.2f}s)')


if __name__ == '__main__':
    print(ensure_data(print_progress))
