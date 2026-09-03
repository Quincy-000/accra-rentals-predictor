import sys
sys.path.append("model")
from clean import load_and_clean
from sklearn.model_selection import train_test_split, KFold, cross_val_score
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np


def build_preprocessor():
    categorical_features = ["neighborhood", "furnished"]
    return ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ],
        remainder="passthrough"
    )


def main():
    df = load_and_clean()

    features = ["beds", "baths", "garages", "neighborhood", "furnished"]
    target = "price_ghs_month"

    X = df[features]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("Training set size:", len(X_train))
    print("Test set size:", len(X_test))

    preprocessor = build_preprocessor()

    model = Pipeline(steps=[
        ("preprocess", preprocessor),
        ("regressor", LinearRegression())
    ])

    model.fit(X_train, y_train)

    print("Model trained.")

    y_pred = model.predict(X_test)

    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print(f"\nBaseline Linear Regression:")
    print(f"RMSE: {rmse:.2f} GHS")
    print(f"R²: {r2:.3f}")

    models_to_try = {
        "RandomForest": RandomForestRegressor(random_state=42),
        "GradientBoosting": GradientBoostingRegressor(random_state=42),
    }

    for name, regressor in models_to_try.items():
        pipeline = Pipeline(steps=[
            ("preprocess", preprocessor),
            ("regressor", regressor)
        ])

        pipeline.fit(X_train, y_train)
        preds = pipeline.predict(X_test)

        rmse = np.sqrt(mean_squared_error(y_test, preds))
        r2 = r2_score(y_test, preds)

        print(f"\n{name}:")
        print(f"RMSE: {rmse:.2f} GHS")
        print(f"R²: {r2:.3f}")

    print("\n--- Cross-validation (5-fold) ---")

    cv_models = {
        "LinearRegression": Pipeline(steps=[("preprocess", preprocessor), ("regressor", LinearRegression())]),
        "RandomForest": Pipeline(steps=[("preprocess", preprocessor), ("regressor", RandomForestRegressor(random_state=42))]),
        "GradientBoosting": Pipeline(steps=[("preprocess", preprocessor), ("regressor", GradientBoostingRegressor(random_state=42))]),
    }

    for name, pipeline in cv_models.items():
        scores = cross_val_score(pipeline, X, y, cv=5, scoring="r2")
        print(f"{name}: R² per fold = {[round(s, 3) for s in scores]}")
        print(f"{name}: mean R² = {scores.mean():.3f} (+/- {scores.std():.3f})")


if __name__ == "__main__":
    main()
