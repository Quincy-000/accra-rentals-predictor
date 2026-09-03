import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "model"))

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from train import build_preprocessor


def build_test_dataframe():
    return pd.DataFrame({
        "beds": [1, 2, 3, 2, 1, 3, 2, 1],
        "baths": [1, 1, 2, 2, 1, 3, 2, 1],
        "garages": [0, 0, 1, 1, 0, 2, 1, 0],
        "neighborhood": ["East Legon", "Cantonments", "Osu", "East Legon", "Other", "Cantonments", "Osu", "Other"],
        "furnished": [True, False, True, False, True, False, True, False],
        "price_ghs_month": [5000, 8000, 15000, 9000, 4000, 20000, 10000, 3500],
    })


def test_pipeline_trains_and_predicts_reasonable_values():
    df = build_test_dataframe()
    features = ["beds", "baths", "garages", "neighborhood", "furnished"]
    target = "price_ghs_month"

    X = df[features]
    y = df[target]

    preprocessor = build_preprocessor()

    model = Pipeline(steps=[
        ("preprocess", preprocessor),
        ("regressor", LinearRegression())
    ])

    model.fit(X, y)
    predictions = model.predict(X)

    assert len(predictions) == len(X)
    assert all(p > 0 for p in predictions)
