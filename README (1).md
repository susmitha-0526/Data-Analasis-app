# 📊 Python Data Analysis Application

An end-to-end data analysis project built with **NumPy, Pandas, Matplotlib, Seaborn** and the **Requests** library. It loads a dataset, cleans it, analyses it, draws charts, pulls live data from a **REST API**, and writes a Markdown report: all from one script.

## What it does

| Step | What happens | Tools |
|---|---|---|
| 1. Load | Reads a CSV dataset (creates a sample sales dataset if none is given) | Pandas |
| 2. Clean | Removes duplicates, fixes text casing/spaces, converts dates, handles missing and invalid values | Pandas, NumPy |
| 3. Analyse | Total/average revenue, group-by summaries, monthly trend, correlations | Pandas, NumPy |
| 4. Visualise | Bar chart, line chart, box plot, correlation heatmap | Matplotlib, Seaborn |
| 5. Consume API | Calls the Open-Meteo weather REST API and converts the JSON response into a DataFrame | Requests |
| 6. Report | Generates `outputs/report.md` with metrics, tables, charts and insights | Pandas |

## Project structure
```
data-analysis-app/
├── data_analysis_app.py   # the whole application
├── requirements.txt
├── data/
│   └── sales_data.csv     # sample dataset (auto-generated on first run)
├── outputs/               # created on run: report.md, cleaned_data.csv, charts (.png)
└── README.md
```

## Getting started

Requires Python 3.9+.

```bash
git clone https://github.com/<your-username>/data-analysis-app.git
cd data-analysis-app
pip install -r requirements.txt
python data_analysis_app.py
```

Options:
```bash
python data_analysis_app.py --csv path/to/your_data.csv   # use your own dataset
python data_analysis_app.py --city Bengaluru              # Hyderabad, Bengaluru, Chennai, Delhi
python data_analysis_app.py --skip-api                    # run without internet
```

> **Using your own CSV?** The cleaning/analysis functions expect these columns: `order_id, order_date, region, category, quantity, unit_price, customer_rating`. Edit `clean_data()` and `analyse_data()` to match a different dataset.

## Data cleaning in detail
The sample dataset is intentionally messy (500 orders + 12 duplicate rows):

- **Duplicates** → removed with `drop_duplicates()`
- **Inconsistent text** (`"ELECTRONICS  "`, `"electronics"`) → `str.strip().str.title()`
- **Missing numbers** (`quantity`, `customer_rating`) → filled with the median
- **Missing text** (`region`) → labelled `"Unknown"`
- **Invalid prices** (≤ 0) → set to missing, then filled with the median price of that category
- **Wrong types** → `order_date` converted to `datetime`, `quantity` to `int`
- **New columns** → `revenue = quantity × unit_price`, `month`

## Working with the REST API
`fetch_weather()` sends a `GET` request to `https://api.open-meteo.com/v1/forecast` (free, no API key) with query parameters for latitude, longitude and the daily variables. It then:

1. checks the status code with `raise_for_status()`
2. reads the JSON body with `response.json()`
3. `parse_weather_json()` turns the nested JSON into a clean DataFrame

If the request fails (no internet, timeout, bad response) the function returns `None` and the rest of the report still generates.

## Sample output
After running, open `outputs/report.md`. It contains:

- cleaning summary (rows before/after, duplicates removed, missing values)
- key metrics (total revenue, average order value, average rating)
- revenue by category and region
- charts: `revenue_by_category.png`, `monthly_revenue.png`, `revenue_by_region_box.png`, `correlation_heatmap.png`, `weather_forecast.png`
- written insights

<!-- Tip: after running, add 1–2 screenshots of your charts here:
![Monthly revenue](outputs/monthly_revenue.png) -->

## Key learnings
- Real data is messy; cleaning usually takes more effort than the analysis itself.
- Vectorised Pandas/NumPy operations replace slow Python loops.
- A good chart answers one question clearly.
- APIs return JSON, which has to be validated and reshaped before it can be analysed.
- Handling failures (timeouts, bad responses) is part of writing reliable code.

## Future improvements
- Add a Streamlit dashboard
- Export the report as PDF/HTML
- Cache API responses
- Add unit tests for the cleaning functions

## Author
**<Your Name>** · [LinkedIn](https://linkedin.com/in/<your-profile>) · [GitHub](https://github.com/<your-username>)
