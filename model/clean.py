import pandas as pd


def normalize_neighborhood(name):
    if pd.isna(name):
        return name

    name = name.strip().lower()

    # Known spelling/casing variants -> canonical name
    mapping = {
        "cantonments": "Cantonments",
        "cantonment": "Cantonments",
        "cantoment": "Cantonments",
        "cantoments": "Cantonments",
        "east cantonments": "Cantonments",
        "east legon": "East Legon",
        "eastlegon": "East Legon",
        "east legon 69": "East Legon",
        "airport residential area": "Airport Residential Area",
        "airport residential": "Airport Residential Area",
        "airport residential area, grand mirage": "Airport Residential Area",
        "airport city": "Airport City",
        "airport area": "Airport Area",
        "north ridge": "North Ridge",
        "abelenkpe": "Abelenkpe",
        "abelemkpe": "Abelenkpe",
        "shiashie": "Shiashie",
        "dzorwulu": "Dzorwulu",
        "dzorwulu north": "Dzorwulu North",
    }

    return mapping.get(name, name.title())


def clean_area(area_m2, beds, per_bed_cap=160):
    if pd.isna(area_m2):
        return area_m2
    if area_m2 == 987:
        return None
    if pd.notna(beds) and area_m2 > beds * per_bed_cap:
        return None
    return area_m2


def load_and_clean(path="data/listings.csv", output_path="data/listings_clean.csv"):
    df = pd.read_csv(path)

    before = len(df)
    df = df[df["price_period"] == "month"].copy()
    after = len(df)
    print(f"Dropped {before - after} non-monthly listings ({before} -> {after})")

    df["neighborhood"] = df["neighborhood"].apply(normalize_neighborhood)
    df["area_m2"] = df.apply(lambda row: clean_area(row["area_m2"], row["beds"]), axis=1)

    df["garages"] = df["garages"].fillna(0)

    before_dropna = len(df)
    df = df.dropna(subset=["beds", "baths"])
    print(f"Dropped {before_dropna - len(df)} rows missing beds/baths")

    df.to_csv(output_path, index=False)
    print(f"Saved cleaned dataset to {output_path} ({len(df)} rows)")

    return df


if __name__ == "__main__":
    df = load_and_clean()
    print(df["price_ghs_month"].describe())
    print(f"\nUnique neighborhoods after cleaning: {df['neighborhood'].nunique()}")
