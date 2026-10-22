"""Small calculation functions shared by the map and details panel."""
import math
import re

import pandas as pd

# MSU Main Library center at 366 W Circle Dr, OSM way 26072753.
# Markers, distance rings and block-group distances share this reference point.
MSU_LAT, MSU_LON = 42.7308851, -84.4832076
STUDY_RADIUS_KM = 10
MIN_STUDY_SHARE = .70
# Blue follows the preferred direction. Lower rent, poverty and distances are blue.
COLORS = ["#b84616", "#e87533", "#f4b183", "#f4f1eb", "#9ccbea", "#448dc2", "#17558d"]
SCHOOL_COLORS = {"Elementary": "#e6a21a", "Middle": "#8a57b2", "High": "#228b73", "Combined": "#454d59"}
LOWER_IS_BETTER = {'Med_Gross_Rent_ACS_20_24', 'pct_Prs_Blw_Pov_Lev_ACS_20_24',
                   'distance_msu_km', 'nearest_school_km'}

# Display label, source column and unit. Education describes residents aged 25+, not parents.
METRICS = {
    "Monthly rent": ("Med_Gross_Rent_ACS_20_24", "currency"),
    "Home value": ("Med_House_Value_BG_ACS_20_24", "currency"),
    "Household income": ("Med_HHD_Inc_BG_ACS_20_24", "currency"),
    "Households with under 18": ("pct_HHD_PPL_Und_18_ACS_20_24", "percent"),
    "Bachelor's+ (adults 25+)": ("pct_College_ACS_20_24", "percent"),
    "Vacant housing": ("pct_Vacant_Units_ACS_20_24", "percent"),
    "Renter households": ("pct_Renter_Occp_HU_ACS_20_24", "percent"),
    "Poverty": ("pct_Prs_Blw_Pov_Lev_ACS_20_24", "percent"),
    "Distance to MSU": ("distance_msu_km", "km"),
    "Nearest public school": ("nearest_school_km", "km"),
}
# Keep radar variables separate from map variables. True means lower is preferred.
PROFILE = {
    "Monthly rent": ("Med_Gross_Rent_ACS_20_24", "currency", True),
    "General crime": ("general_crime_count", "count", True),
    "Distance to MSU": ("distance_msu_km", "km", True),
    "District school average": ("district_overall_mean", "score", False),
    "Nearest public school": ("nearest_school_km", "km", True),
    "Households with someone under 18": ("pct_HHD_PPL_Und_18_ACS_20_24", "percent", False),
    "Bachelor's+ (adults 25+)": ("pct_College_ACS_20_24", "percent", False),
}
SHORT_LABELS = ["Rent", "General crime", "MSU proximity", "School score", "School proximity", "Household with under 18", "Adults BA+"]


PEOPLE = {
    'Households with someone under 18':'pct_HHD_PPL_Und_18_ACS_20_24',
    'Residents aged 5–17':'pct_Pop_5_17_ACS_20_24',
    'Residents aged 18–24':'pct_Pop_18_24_ACS_20_24',
    'Residents aged 25–44':'pct_Pop_25_44_ACS_20_24',
    'Residents aged 45–64':'pct_Pop_45_64_ACS_20_24',
    'Residents aged 65+':'pct_Pop_65plus_ACS_20_24',
    'Other language at home (age 5+)':'pct_Othr_Lang_ACS_20_24',
    'Hispanic / Latino (any race)':'pct_Hispanic_ACS_20_24',
    'Non-Hispanic White':'pct_NH_White_alone_ACS_20_24',
    'Non-Hispanic Black':'pct_NH_Blk_alone_ACS_20_24',
    'Non-Hispanic Asian':'pct_NH_Asian_alone_ACS_20_24',
    'Non-Hispanic American Indian / Alaska Native':'pct_NH_AIAN_alone_ACS_20_24',
    'Non-Hispanic Native Hawaiian / Pacific Islander':'pct_NH_NHOPI_alone_ACS_20_24',
    'Non-Hispanic other race':'pct_NH_SOR_alone_ACS_20_24',
    'Non-Hispanic multiracial':'pct_NH_Multi_Races_ACS_20_24',
}

def serves_grade(grades, selected):
    """Expand ranges such as 'KG,1-4' to check whether a grade is offered."""
    if selected == "Any grade":
        return True
    target = 0 if selected == "Kindergarten" else int(selected)
    text = str(grades)
    available = {0} if "KG" in text else set()
    for first, last in re.findall(r"(\d+)\s*-\s*(\d+)", text):
        available.update(range(int(first), int(last) + 1))
    for number in re.findall(r"\b\d+\b", text):
        available.add(int(number))
    return target in available


def school_levels(grades, name=""):
    """Infer school levels from grades, using names for cases such as middle schools serving grades 5-6."""
    available = set()
    for grade in range(13):
        if grade == 0:
            selected = "Kindergarten"
        else:
            selected = str(grade)
        if serves_grade(grades, selected):
            available.add(grade)
    levels = []
    elementary = available & set(range(6))
    middle = available & {6, 7, 8}
    if "middle" in name.lower() and available and max(available) <= 8:
        elementary, middle = set(), available
    if elementary:
        levels.append("Elementary")
    if middle:
        levels.append("Middle")
    if available & {9, 10, 11, 12}:
        levels.append("High")
    return levels


def grade_description(grades):
    """DevK and KG are different programs. Numeric ranges show the grades offered."""
    result = []
    for token in str(grades).split(","):
        token = token.strip()
        if token == "DevK":
            description = "Developmental kindergarten"
        elif token == "KG":
            description = "Kindergarten"
        elif token == "PK":
            description = "Pre-kindergarten"
        elif "-" in token:
            description = "Grades " + token.replace("-", "–")
        else:
            description = "Grade " + token
        result.append(description)
    return "; ".join(result)


def format_value(value, unit):
    if pd.isna(value):
        return "No data"
    if unit == "currency":
        return f"${value:,.0f}"
    if unit == "percent":
        return f"{value:.1f}%"
    if unit == "score":
        return f"{value:.1f}/100"
    if unit == "count":
        # Individual counts are integers, but mean block-group counts can have decimals.
        return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.1f}"
    return f"{value:.1f} km"


def tier_values(series):
    """Create seven tiers using distance from the mean in standard deviations. Preserve ties and missing values."""
    # Nullable Float64 can retain original values behind its missing-value mask.
    # Convert to plain float64 with NaN so missing entries do not affect tier calculations.
    values = pd.to_numeric(series, errors="coerce").astype("float64")
    mean, std = values.mean(), values.std(ddof=0)
    result = pd.Series(pd.NA, index=series.index, dtype="Int64")
    valid = values.notna()
    if not valid.any():
        return result
    if std == 0:
        result.loc[valid] = 4
        return result
    z = (values - mean) / std
    # An exact mean gets tier 4; values just below or above it get tier 3 or 5.
    for index, value in z.dropna().items():
        if value < -1:
            grade = 1
        elif value < -.5:
            grade = 2
        elif value < 0:
            grade = 3
        elif value == 0:
            grade = 4
        elif value <= .5:
            grade = 5
        elif value <= 1:
            grade = 6
        else:
            grade = 7
        result.loc[index] = grade
    return result


def add_tiers(frame):
    result = frame.copy()
    columns = []
    for col, unit in METRICS.values():
        columns.append(col)
    for col, unit, lower_is_better in PROFILE.values():
        if col not in columns:
            columns.append(col)
    for col in columns:
        if col in result:
            result[f"tier_{col}"] = tier_values(result[col])
    if 'general_crime_count' in result:
        # Crime uses fixed count ranges rather than the mean. Zero records gets tier 7.
        result['tier_general_crime_count'] = safety_tiers(result.general_crime_count)
    return result


def safety_tiers(counts):
    """Tier the 180-day record counts. Unavailable data stay missing, not zero or tier 7."""
    values = pd.to_numeric(counts, errors='coerce').astype('float64')
    result = pd.Series(pd.NA, index=counts.index, dtype='Int64')
    for index, value in values.items():
        if pd.isna(value) or value < 0:
            continue
        if value == 0:
            grade = 7
        elif value <= 5:
            grade = 6
        elif value <= 10:
            grade = 5
        elif value <= 25:
            grade = 4
        elif value <= 50:
            grade = 3
        elif value <= 100:
            grade = 2
        else:
            grade = 1
        result.loc[index] = grade
    return result


def radar_tiers(row, tiers=7):
    """Make larger radar values follow the preferred direction on every axis."""
    result = []
    for column, unit, lower_is_better in PROFILE.values():
        grade = row.get(f"tier_{column}", pd.NA)
        # Crime direction is already handled by safety_tiers. Reverse only rent and distance here.
        # Map tier 1 to 7 and tier 7 to 1, keeping tier 4 and missing values unchanged.
        if lower_is_better and unit != "count" and pd.notna(grade):
            grade = tiers + 1 - int(grade)
        # Zero is only a plotting position for missing values. Keep source and analysis values missing.
        result.append(int(grade) if pd.notna(grade) else 0)
    return result


def radar_svg(row, tiers=7):
    """Draw the details-panel radar as SVG without an external chart library."""
    cx, cy, radius = 150, 116, 70
    angles = [math.radians(-90 + i * 360 / len(SHORT_LABELS)) for i in range(len(SHORT_LABELS))]

    def point(angle, distance):
        return cx + math.cos(angle) * distance, cy + math.sin(angle) * distance

    def points(distances):
        coordinates = []
        for angle, distance in zip(angles, distances):
            x, y = point(angle, distance)
            coordinates.append(f"{x:.1f},{y:.1f}")
        return " ".join(coordinates)

    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="300" height="235" viewBox="0 0 300 235" role="img" aria-label="Relative value tiers">']
    for level in range(1, tiers + 1):
        svg.append(f'<polygon points="{points([radius * level / tiers] * len(angles))}" fill="none" stroke="#dbe4e1"/>')
    grades = radar_tiers(row, tiers)
    # Connect all seven axes, drawing missing axes at the center with orange-brown N/A labels.
    coordinates = points([radius * grade / tiers for grade in grades])
    svg.append(f'<polygon points="{coordinates}" fill="#24786c" fill-opacity="0.18" stroke="#24786c" stroke-width="2"/>')
    for angle, label, grade in zip(angles, SHORT_LABELS, grades):
        x, y = point(angle, radius)
        svg.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#dbe4e1"/>')
        color = '#b57238' if grade == 0 else '#263f38'
        x, y = point(angle, radius * grade / tiers)
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}"/>')
        x, y = point(angle, radius + 36)
        number = 'N/A' if grade == 0 else str(grade)
        # Wrap long axis labels to keep them from overlapping.
        lines = {'Adults BA+':['Adults','BA+'], 'MSU proximity':['MSU','proximity'],
                 'School proximity':['School','proximity'], 'General crime':['General','crime'],
                 'School score':['School','score'], 'Household with under 18':['Household with','under 18']}.get(label,[label]) + [number]
        if math.sin(angle) > .6:
            y = y - 20
        y = max(16, y)
        text = ''
        for i, line in enumerate(lines):
            if i == 0:
                spacing = 0
            else:
                spacing = 15
            text += f'<tspan x="{x:.1f}" dy="{spacing}">{line}</tspan>'
        weight = 700 if grade == 0 else 400
        svg.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-family="Arial,sans-serif" font-size="12.3" font-weight="{weight}" fill="{color}">{text}</text>')
    svg.append('</svg>')
    return "".join(svg)
