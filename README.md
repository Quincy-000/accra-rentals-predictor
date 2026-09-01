# Accra Rentals — Price Predictor

Predict monthly rent for apartments in Accra from listing features (beds, baths, garages, neighborhood, furnished status).

**Pipeline:** live scraper → cleaning → baseline models. Currently at **Milestone 2 (modelling)**.

## Dataset

- **226 listings** crawled live from a Ghana real-estate site (Selenium + fixture-tested parser)
- **202 rows** after cleaning (monthly listings only, missing values dropped, outliers capped)
- Features: `beds`, `baths`, `garages`, `neighborhood` (17 categories after grouping rare ones into "Other"), `furnished`
- Target: `price_ghs_month` (GH₵ / month)

Cleaning is reproducible: `model/clean.py` writes `data/listings_clean.csv` as a build artifact.

## Models compared

All models trained on the same 80/20 split (161 train / 41 test rows), one-hot encoding via `ColumnTransformer` + `Pipeline`. Cross-validation: 5-fold R².

| Model | 80/20 R² | CV mean R² | CV std |
|---|---|---|---|
| Linear Regression | **0.666** | **0.557** | ±0.148 |
| GradientBoosting | 0.652 | 0.322 | ±0.429 |
| RandomForest | 0.525 | 0.360 | ±0.329 |

Linear regression wins outright — best test R² and the lowest variance across folds.

## What this project taught me

### Simple beat complex

RandomForest and GradientBoosting underperformed plain linear regression here, most likely because the dataset is small (161–202 training rows) — tree ensembles need more data to avoid overfitting. Worth stating explicitly as a counter to "fancier model = better."

### Cross-validation caught a real data bug that a single train/test split missed

The 80/20 split alone looked fine (R² = 0.522 originally); it took 5-fold CV producing an impossible R² (Linear Regression R² = −55,176 on one fold) to surface the corruption: a Kwabenya listing with `baths = 9000` — identical to its `price_ghs_month` of 9000, so the price almost certainly got typed into the bathroom field at the source. That single row exploded the linear model's coefficients when isolated in a fold. `clean_baths()` now caps baths at 10 and treats anything above as invalid. A legitimate example of validation rigor paying off, not just a formality.

## Run it

```bash
python model/train.py          # cleans data + trains + cross-validates
python model/clean.py          # just regenerate the clean dataset
```

Requires `pandas`, `scikit-learn`, `numpy` (use `./venv/bin/python` if the repo venv exists).

## Roadmap

- [x] Milestone 1: live scraper, fixture tests, 226-row dataset
- [x] Milestone 2: cleaning pipeline + baseline models (LR wins)
- [ ] Milestone 3: feature work / hyperparameter tuning / price bands
