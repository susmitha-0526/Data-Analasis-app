"""
Python Data Analysis Application
================================
Module 4 project: Python Data & APIs

Pipeline:
    1. Load      - read a CSV dataset (or generate a sample one)
    2. Clean     - fix missing values, duplicates, bad text, wrong types
    3. Analyse   - NumPy / Pandas statistics and group-by summaries
    4. Visualise - Matplotlib / Seaborn charts
    5. API       - consume a REST API (Open-Meteo) and process the JSON payload
    6. Report    - write a Markdown report that embeds the charts

Usage:
    python data_analysis_app.py                  # uses/creates data/sales_data.csv
    python data_analysis_app.py --csv my.csv     # use your own dataset (see README)
    python data_analysis_app.py --skip-api       # run without internet
"""
import argparse
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                      # save charts to files, no window needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns

DATA_DIR = Path("data")
OUTPUT_DIR = Path("outputs")
sns.set_theme(style="whitegrid")


# --------------------------------------------------------------------------- #
# 1. LOAD
# --------------------------------------------------------------------------- #
def generate_sample_dataset(path: Path, rows: int = 500, seed: int = 42) -> None:
    """Create a deliberately messy sales dataset so the cleaning step has work to do."""
    rng = np.random.default_rng(seed)
    regions = ["North", "South", "East", "West"]
    categories = ["Electronics", "Clothing", "Groceries", "Furniture"]
    base_price = {"Electronics": 300, "Clothing": 40, "Groceries": 15, "Furniture": 220}

    category = rng.choice(categories, rows)
    quantity = rng.integers(1, 10, rows).astype(float)
    unit_price = np.array([base_price[c] for c in category]) * rng.uniform(0.8, 1.3, rows)
    df = pd.DataFrame({
        "order_id": np.arange(1001, 1001 + rows),
        "order_date": pd.date_range("2025-01-01", periods=rows, freq="14h").strftime("%Y-%m-%d"),
        "region": rng.choice(regions, rows),
        "category": category,
        "quantity": quantity,
        "unit_price": unit_price.round(2),
        "customer_rating": rng.integers(1, 6, rows).astype(float),
    })

    # --- inject typical real-world problems ---
    df.loc[rng.choice(rows, 25, replace=False), "quantity"] = np.nan
    df.loc[rng.choice(rows, 20, replace=False), "customer_rating"] = np.nan
    df.loc[rng.choice(rows, 15, replace=False), "region"] = np.nan
    df.loc[rng.choice(rows, 30, replace=False), "category"] = (
        df.loc[rng.choice(rows, 30, replace=False), "category"].str.upper() + "  "
    ).values
    df.loc[rng.choice(rows, 5, replace=False), "unit_price"] = -1          # impossible values
    df = pd.concat([df, df.sample(12, random_state=seed)], ignore_index=True)  # duplicates

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def load_data(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        print(f"[load] {csv_path} not found -> generating a sample dataset.")
        generate_sample_dataset(csv_path)
    df = pd.read_csv(csv_path)
    print(f"[load] {len(df)} rows x {df.shape[1]} columns loaded from {csv_path}")
    return df


# --------------------------------------------------------------------------- #
# 2. CLEAN
# --------------------------------------------------------------------------- #
def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return (clean_df, log). `log` records what was fixed, for the report."""
    log = {"rows_before": len(df)}
    df = df.copy()

    log["missing_before"] = df.isna().sum()[lambda s: s > 0].to_dict()

    # remove exact duplicate orders
    log["duplicates_removed"] = int(df.duplicated().sum())
    df = df.drop_duplicates()

    # fix text: strip spaces + consistent capitalisation
    for col in ("region", "category"):
        df[col] = df[col].str.strip().str.title()

    # fix types
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    # impossible prices (<= 0) -> treat as missing
    log["invalid_prices"] = int((df["unit_price"] <= 0).sum())
    df.loc[df["unit_price"] <= 0, "unit_price"] = np.nan

    # fill missing values: numbers with the median, text with a label
    df["quantity"] = df["quantity"].fillna(df["quantity"].median())
    df["customer_rating"] = df["customer_rating"].fillna(df["customer_rating"].median())
    df["unit_price"] = df["unit_price"].fillna(df.groupby("category")["unit_price"].transform("median"))
    df["region"] = df["region"].fillna("Unknown")
    df = df.dropna(subset=["order_date"])

    df["quantity"] = df["quantity"].astype(int)
    df["revenue"] = (df["quantity"] * df["unit_price"]).round(2)
    df["month"] = df["order_date"].dt.to_period("M").astype(str)

    log["rows_after"] = len(df)
    print(f"[clean] {log['rows_before']} -> {log['rows_after']} rows "
          f"({log['duplicates_removed']} duplicates, {log['invalid_prices']} invalid prices fixed)")
    return df.reset_index(drop=True), log


# --------------------------------------------------------------------------- #
# 3. ANALYSE
# --------------------------------------------------------------------------- #
def analyse_data(df: pd.DataFrame) -> dict:
    results = {
        "total_revenue": df["revenue"].sum(),
        "avg_order_value": df["revenue"].mean(),
        "median_order_value": float(np.median(df["revenue"])),
        "std_order_value": float(np.std(df["revenue"])),
        "avg_rating": df["customer_rating"].mean(),
        "revenue_by_category": df.groupby("category")["revenue"].sum().sort_values(ascending=False),
        "revenue_by_region": df.groupby("region")["revenue"].sum().sort_values(ascending=False),
        "monthly_revenue": df.groupby("month")["revenue"].sum(),
        "correlation": df[["quantity", "unit_price", "revenue", "customer_rating"]].corr().round(2),
    }
    results["best_category"] = results["revenue_by_category"].idxmax()
    results["best_region"] = results["revenue_by_region"].idxmax()
    print(f"[analyse] total revenue = {results['total_revenue']:,.2f}, "
          f"top category = {results['best_category']}, top region = {results['best_region']}")
    return results


# --------------------------------------------------------------------------- #
# 4. VISUALISE
# --------------------------------------------------------------------------- #
def make_charts(df: pd.DataFrame, results: dict, out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(out_dir / name, dpi=120)
        plt.close(fig)
        files.append(name)

    fig, ax = plt.subplots(figsize=(7, 4))
    sns.barplot(x=results["revenue_by_category"].index, y=results["revenue_by_category"].values,
                hue=results["revenue_by_category"].index, legend=False, ax=ax)
    ax.set(title="Revenue by Category", xlabel="Category", ylabel="Revenue")
    save(fig, "revenue_by_category.png")

    fig, ax = plt.subplots(figsize=(8, 4))
    sns.lineplot(x=results["monthly_revenue"].index, y=results["monthly_revenue"].values,
                 marker="o", ax=ax)
    ax.set(title="Monthly Revenue Trend", xlabel="Month", ylabel="Revenue")
    ax.tick_params(axis="x", rotation=45)
    save(fig, "monthly_revenue.png")

    fig, ax = plt.subplots(figsize=(7, 4))
    sns.boxplot(data=df, x="region", y="revenue", hue="region", legend=False, ax=ax)
    ax.set(title="Order Value Distribution by Region", xlabel="Region", ylabel="Revenue")
    save(fig, "revenue_by_region_box.png")

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    sns.heatmap(results["correlation"], annot=True, cmap="coolwarm", vmin=-1, vmax=1, ax=ax)
    ax.set_title("Correlation Heatmap")
    save(fig, "correlation_heatmap.png")

    print(f"[visualise] saved {len(files)} charts to {out_dir}/")
    return files


# --------------------------------------------------------------------------- #
# 5. REST API  (Open-Meteo: free, no API key)
# --------------------------------------------------------------------------- #
CITIES = {                                   # name: (latitude, longitude)
    "Hyderabad": (17.385, 78.4867),
    "Bengaluru": (12.9716, 77.5946),
    "Chennai": (13.0827, 80.2707),
    "Delhi": (28.6139, 77.2090),
}


def fetch_weather(city: str = "Hyderabad", days: int = 7, timeout: int = 10) -> pd.DataFrame | None:
    """Call the Open-Meteo REST API and turn its JSON payload into a DataFrame.
    Returns None if the request fails, so the rest of the app keeps working."""
    lat, lon = CITIES.get(city, CITIES["Hyderabad"])
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto",
        "forecast_days": days,
    }
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()                    # raises on 4xx / 5xx
        return parse_weather_json(response.json())
    except (requests.RequestException, KeyError, ValueError) as err:
        print(f"[api] request failed: {err}")
        return None


def parse_weather_json(payload: dict) -> pd.DataFrame:
    """Convert Open-Meteo's JSON ({'daily': {...lists...}}) into a tidy DataFrame."""
    daily = payload["daily"]
    df = pd.DataFrame({
        "date": pd.to_datetime(daily["time"]),
        "temp_max_c": daily["temperature_2m_max"],
        "temp_min_c": daily["temperature_2m_min"],
        "rain_mm": daily["precipitation_sum"],
    })
    df["temp_avg_c"] = ((df["temp_max_c"] + df["temp_min_c"]) / 2).round(1)
    return df


def weather_chart(weather: pd.DataFrame, city: str, out_dir: Path) -> str:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(weather["date"], weather["temp_max_c"], marker="o", label="Max °C")
    ax.plot(weather["date"], weather["temp_min_c"], marker="o", label="Min °C")
    ax.set(title=f"{len(weather)}-Day Temperature Forecast: {city}", ylabel="°C")
    ax.legend()
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    name = "weather_forecast.png"
    fig.savefig(out_dir / name, dpi=120)
    plt.close(fig)
    return name


# --------------------------------------------------------------------------- #
# 6. REPORT
# --------------------------------------------------------------------------- #
def generate_report(df, log, results, charts, weather, city, out_dir: Path) -> Path:
    r = results
    lines = [
        "# Data Analysis Report",
        f"_Generated on {datetime.now():%Y-%m-%d %H:%M}_\n",
        "## 1. Data Cleaning Summary",
        f"- Rows before cleaning: **{log['rows_before']}**",
        f"- Duplicate rows removed: **{log['duplicates_removed']}**",
        f"- Invalid prices fixed: **{log['invalid_prices']}**",
        f"- Missing values found: `{log['missing_before']}`",
        f"- Rows after cleaning: **{log['rows_after']}**\n",
        "## 2. Key Metrics",
        f"- Total revenue: **{r['total_revenue']:,.2f}**",
        f"- Average order value: **{r['avg_order_value']:,.2f}** "
        f"(median {r['median_order_value']:,.2f}, std {r['std_order_value']:,.2f})",
        f"- Average customer rating: **{r['avg_rating']:.2f} / 5**",
        f"- Best category: **{r['best_category']}**",
        f"- Best region: **{r['best_region']}**\n",
        "## 3. Revenue by Category",
        r["revenue_by_category"].round(2).to_frame("revenue").to_markdown(),
        "\n## 4. Revenue by Region",
        r["revenue_by_region"].round(2).to_frame("revenue").to_markdown(),
        "\n## 5. Charts",
    ]
    lines += [f"![{c}]({c})" for c in charts if not c.startswith("weather")]

    lines.append("\n## 6. API Data: Weather Forecast")
    if weather is not None:
        lines += [
            f"Fetched live from the Open-Meteo REST API for **{city}**.\n",
            weather.round(1).to_markdown(index=False),
            "\n![weather_forecast.png](weather_forecast.png)",
        ]
    else:
        lines.append("_API data unavailable (offline or request failed)._")

    lines.append("\n## 7. Insights")
    lines.append(f"- **{r['best_category']}** drives the most revenue; focus stock and promotion here.")
    lines.append(f"- The **{r['best_region']}** region leads in sales; study what works there.")
    strongest = (r["correlation"].loc["revenue"].drop("revenue").abs().idxmax())
    lines.append(f"- Revenue is most strongly related to **{strongest}** among the numeric columns.")

    path = out_dir / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] written to {path}")
    return path


# --------------------------------------------------------------------------- #
# MAIN
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description="Python Data Analysis Application")
    parser.add_argument("--csv", type=Path, default=DATA_DIR / "sales_data.csv",
                        help="path to the dataset (created automatically if missing)")
    parser.add_argument("--city", default="Hyderabad", choices=CITIES, help="city for the weather API")
    parser.add_argument("--skip-api", action="store_true", help="do not call the REST API")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)

    raw = load_data(args.csv)
    clean, log = clean_data(raw)
    clean.to_csv(OUTPUT_DIR / "cleaned_data.csv", index=False)
    results = analyse_data(clean)
    charts = make_charts(clean, results, OUTPUT_DIR)

    weather = None
    if not args.skip_api:
        weather = fetch_weather(args.city)
        if weather is not None:
            print(f"[api] received {len(weather)} days of forecast for {args.city}")
            charts.append(weather_chart(weather, args.city, OUTPUT_DIR))

    generate_report(clean, log, results, charts, weather, args.city, OUTPUT_DIR)
    print("\nDone! Open outputs/report.md to see the full report.")


if __name__ == "__main__":
    main()
