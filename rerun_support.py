"""Saved run settings and revision grouping, independent of the Streamlit UI."""
import json
import re
from datetime import datetime
from uuid import uuid4
import pandas as pd
from meal_catalog import ACTIVE_BRANDS, SUMMARY_MEAL_ORDER
from quantities import daily_summary, normalize_columns

BULK_RECIPES = ['Spaghetti Bolognese', 'Beef Chow Mein', 'Beef Burrito Bowl', "Shepherd's Pie"]
SETTINGS_COLUMN = '_Report settings'
NAME_PATTERN = re.compile(r'^daily_production_report_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})(?:_([0-9a-f]{12}))?\.pdf$')

def parse_run_name(name):
    match = NAME_PATTERN.fullmatch(name)
    if not match:
        raise ValueError('This report filename does not contain a recognised production date.')
    datetime.strptime(match[1], '%Y-%m-%d')
    datetime.strptime(match[2], '%H-%M-%S')
    return match[1], match[2]

def read_settings(frame):
    if SETTINGS_COLUMN not in frame:
        return None
    values = frame[SETTINGS_COLUMN].drop_duplicates().tolist()
    if len(values) != 1 or not isinstance(values[0], str):
        raise ValueError('The saved report settings are incomplete or inconsistent.')
    try:
        data = json.loads(values[0])
        if data['schema'] != 1:
            raise ValueError('Unsupported saved report settings version.')
        parse_run_name(data['root'])
        datetime.fromisoformat(data['created_at'])
        if set(data['bulk_prepared']) != set(BULK_RECIPES):
            raise ValueError('Incomplete preparation settings.')
        if any(type(v) is not bool for v in data['bulk_prepared'].values()):
            raise ValueError('Invalid preparation setting.')
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f'Cannot restore the saved report settings: {error}') from None
    return data

def restore_run(frame, filename):
    parse_run_name(filename)
    if frame.empty or 'Product name' not in frame or 'Already Made' not in frame:
        raise ValueError('This report does not have the saved meal and Already Made details needed for a rerun.')
    brands = [b for b in ACTIVE_BRANDS if b in frame]
    if not brands:
        raise ValueError('This report has no saved Clean Eats or Made Active quantities.')
    settings = read_settings(frame)
    data = normalize_columns(frame, [*brands, 'Already Made'])
    data['Product name'] = data['Product name'].astype('string').str.strip()
    if data['Product name'].isna().any() or data['Product name'].duplicated().any():
        raise ValueError('The saved data has missing or duplicate meal names. Review the original report.')
    excluded = data.loc[~data['Product name'].isin(SUMMARY_MEAL_ORDER), ['Product name', *brands, 'Already Made']]
    # Old Elite Meals columns are not silently carried into a current report.
    issues = []
    if not excluded.empty:
        issues.append('Meals outside the current menu will be omitted: ' + ', '.join(excluded['Product name']))
    if 'Elite Meals' in data and pd.to_numeric(data['Elite Meals'], errors='coerce').fillna(0).ne(0).any():
        issues.append('This report includes Elite Meals quantities. They will not be included in the rerun.')
    current = daily_summary(data[['Product name', *brands, 'Already Made']], brands)
    current = current.set_index('Product name').reindex(SUMMARY_MEAL_ORDER, fill_value=0).reset_index()
    return current[['Product name', *brands, 'Already Made']], brands, settings, issues

def saved_run(frame, brands, production_date, toggles, now, root=None):
    name = f'daily_production_report_{production_date:%Y-%m-%d}_{now:%H-%M-%S}_{uuid4().hex[:12]}.pdf'
    if root is not None:
        parse_run_name(root)
    if set(toggles) != set(BULK_RECIPES) or any(type(v) is not bool for v in toggles.values()):
        raise ValueError('Review all four preparation settings before saving.')
    data = daily_summary(frame, brands)[['Product name', *brands, 'Already Made', 'Total']]
    data[SETTINGS_COLUMN] = json.dumps({'schema': 1, 'root': root or name,
        'created_at': now.isoformat(), 'bulk_prepared': toggles}, sort_keys=True)
    return name, data

def latest_selected_runs(records):
    """Count at most one selected revision per production run, never per day."""
    chosen = {}
    for filename, frame in records:
        settings = read_settings(frame)
        root = settings['root'] if settings else filename
        # A newly tracked revision takes priority over its untracked original.
        rank = (settings is not None, settings['created_at'] if settings else '', filename)
        if root not in chosen or rank > chosen[root][0]:
            chosen[root] = (rank, filename, frame)
    kept = [(name, frame) for _, name, frame in chosen.values()]
    names = {name for name, _ in kept}
    return kept, [name for name, _ in records if name not in names]
