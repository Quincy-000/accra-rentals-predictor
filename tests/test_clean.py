import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "model"))

import pandas as pd
from clean import load_and_clean


def test_only_monthly_listings_remain(tmp_path):
    raw = pd.DataFrame({
        "id": [1, 2, 3],
        "price_period": ["month", "day", "week"],
        "price_ghs_month": [10000, 30000, 25000],
        "beds": [2, 2, 2],
        "baths": [1, 1, 1],
        "garages": [0, 0, 0],
        "area_m2": [None, None, None],
        "neighborhood": ["East Legon", "East Legon", "East Legon"],
        "furnished": [True, True, True],
        "is_featured": [False, False, False],
    })

    input_csv = tmp_path / "raw.csv"
    output_csv = tmp_path / "clean.csv"
    raw.to_csv(input_csv, index=False)

    result = load_and_clean(path=str(input_csv), output_path=str(output_csv))

    assert len(result) == 1
    assert result.iloc[0]["price_period"] == "month"

def test_extreme_baths_value_is_dropped(tmp_path):
    raw = pd.DataFrame({
        "id": [1, 2],
        "price_period": ["month", "month"],
        "price_ghs_month": [10000, 9000],
        "beds": [2, 2],
        "baths": [1, 9000],
        "garages": [0, 0],
        "area_m2": [None, None],
        "neighborhood": ["East Legon", "Kwabenya"],
        "furnished": [True, True],
        "is_featured": [False, False],
    })

    input_csv = tmp_path / "raw.csv"
    output_csv = tmp_path / "clean.csv"
    raw.to_csv(input_csv, index=False)

    result = load_and_clean(path=str(input_csv), output_path=str(output_csv))

    assert len(result) == 1
    assert result.iloc[0]["id"] == 1
def test_neighborhood_spelling_variants_merge(tmp_path):
    raw = pd.DataFrame({
        "id": [1, 2, 3],
        "price_period": ["month", "month", "month"],
        "price_ghs_month": [10000, 10000, 10000],
        "beds": [2, 2, 2],
        "baths": [1, 1, 1],
        "garages": [0, 0, 0],
        "area_m2": [None, None, None],
        "neighborhood": ["Cantonments", "Cantoment", "Cantoments"],
        "furnished": [True, True, True],
        "is_featured": [False, False, False],
    })

    input_csv = tmp_path / "raw.csv"
    output_csv = tmp_path / "clean.csv"
    raw.to_csv(input_csv, index=False)

    result = load_and_clean(path=str(input_csv), output_path=str(output_csv))

    assert result["neighborhood"].nunique() == 1

    assert result.iloc[0]["neighborhood"] == "Cantonments"


def test_rare_neighborhoods_grouped_as_other(tmp_path):
    raw = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "price_period": ["month"] * 5,
        "price_ghs_month": [10000] * 5,
        "beds": [2] * 5,
        "baths": [1] * 5,
        "garages": [0] * 5,
        "area_m2": [None] * 5,
        "neighborhood": ["East Legon", "East Legon", "East Legon", "TinyPlaceA", "TinyPlaceB"],
        "furnished": [True] * 5,
        "is_featured": [False] * 5,
    })

    input_csv = tmp_path / "raw.csv"
    output_csv = tmp_path / "clean.csv"
    raw.to_csv(input_csv, index=False)

    result = load_and_clean(path=str(input_csv), output_path=str(output_csv))

    other_rows = result[result["neighborhood"] == "Other"]
    assert len(other_rows) == 2
    assert set(other_rows["id"]) == {4, 5}

def test_area_outliers_are_nulled(tmp_path):
    raw = pd.DataFrame({
        "id": [1, 2, 3],
        "price_period": ["month", "month", "month"],
        "price_ghs_month": [10000, 10000, 10000],
        "beds": [1, 1, 3],
        "baths": [1, 1, 2],
        "garages": [0, 0, 0],
        "area_m2": [987, 800, 300],
        "neighborhood": ["East Legon", "East Legon", "East Legon"],
        "furnished": [True, True, True],
        "is_featured": [False, False, False],
    })

    input_csv = tmp_path / "raw.csv"
    output_csv = tmp_path / "clean.csv"
    raw.to_csv(input_csv, index=False)

    result = load_and_clean(path=str(input_csv), output_path=str(output_csv))

    row1 = result[result["id"] == 1].iloc[0]
    row2 = result[result["id"] == 2].iloc[0]
    row3 = result[result["id"] == 3].iloc[0]

    assert pd.isna(row1["area_m2"])
    assert pd.isna(row2["area_m2"])
    assert row3["area_m2"] == 300    
