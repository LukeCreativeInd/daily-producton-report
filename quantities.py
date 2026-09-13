"""Validate quantities at upload, after editing, and before PDF rendering."""
import math
import pandas as pd
from meal_catalog import ACTIVE_BRANDS, SUMMARY_MEAL_ORDER


def quantity(value, label, *, allow_negative=False):
    if value is None or (isinstance(value, str) and not value.strip()) or pd.isna(value):
        return 0
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{label}: enter a whole number (or 0).') from None
    if not math.isfinite(number) or not number.is_integer() or (number < 0 and not allow_negative):
        raise ValueError(f'{label}: enter a {"" if allow_negative else "non-negative "}whole number.')
    if abs(number) > 2**53 - 1:
        raise ValueError(f'{label}: quantity is too large.')
    return int(number)


def normalize_columns(frame, columns, *, signed=()):
    frame = frame.copy()
    for column in columns:
        if column not in frame:
            frame[column] = 0
        frame[column] = [quantity(value, f'{name} / {column}', allow_negative=column in signed)
                         for name, value in zip(frame['Product name'], frame[column])]
    return frame


def active_rows(frame):
    if 'Product name' not in frame:
        raise ValueError("Missing 'Product name' column.")
    frame = frame.copy()
    frame['Product name'] = frame['Product name'].astype('string').str.strip()
    return frame[frame['Product name'].isin(SUMMARY_MEAL_ORDER)].copy()


def sorted_meals(frame):
    frame = active_rows(frame)
    if frame['Product name'].duplicated().any():
        raise ValueError('Each meal must appear only once in the editable summary.')
    order = {name: i for i, name in enumerate(SUMMARY_MEAL_ORDER)}
    return frame.assign(_order=frame['Product name'].map(order)).sort_values('_order').drop(columns='_order')


def normalize_upload(frame):
    frame = frame.copy()
    frame.columns = frame.columns.astype(str).str.strip()
    if not {'Product name', 'Quantity'}.issubset(frame.columns):
        raise ValueError("File must have 'Product name' and 'Quantity' columns.")
    frame = active_rows(frame[['Product name', 'Quantity']])
    frame = normalize_columns(frame, ['Quantity'])
    return frame.groupby('Product name', as_index=False)['Quantity'].sum()


def brand_planned(frame, brand):
    """Manufacturing demand from validated columns; stock belongs to Clean Eats."""
    if brand == 'Clean Eats':
        return (frame[brand] - frame['Already Made']).clip(lower=0)
    return frame[brand]


def daily_summary(frame, brands):
    if not brands or any(b not in ACTIVE_BRANDS for b in brands):
        raise ValueError('Select a supported production brand.')
    frame = sorted_meals(frame)
    frame = normalize_columns(frame, [*brands, 'Already Made'])
    frame['Total'] = sum(brand_planned(frame, brand) for brand in brands)
    return normalize_columns(frame, ['Total'])


def weekly_summary(frame):
    frame = sorted_meals(frame)
    frame = normalize_columns(frame, ['Total', 'Already Made', 'Adjustments'], signed=('Adjustments',))
    frame['Final Total'] = (frame['Total'] + frame['Adjustments']).clip(lower=0)
    return normalize_columns(frame, ['Final Total'])


def historical_summary(frame):
    """Recalculate using supported brand columns; never use a retired brand's totals."""
    frame = active_rows(frame)
    brands = [b for b in ACTIVE_BRANDS if b in frame]
    if not brands:
        raise ValueError('This saved report has no supported brand breakdown; use the original Clean Eats or Made Active upload.')
    return daily_summary(frame, brands)[['Product name', 'Already Made', 'Total']]


def normalize_meal_totals(totals):
    return {str(name).upper(): quantity(value, str(name)) for name, value in totals.items()}
