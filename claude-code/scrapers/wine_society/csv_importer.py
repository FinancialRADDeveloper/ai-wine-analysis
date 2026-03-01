import pandas as pd
import re
import os

# File paths -- resolve relative to the monorepo root
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CSV_FILE = os.path.join(
    _REPO_ROOT,
    "data",
    "wine_society",
    "raw",
    "TWS_Members_Wines_CSV_638865531904137428.csv",
)


def load_wine_data() -> pd.DataFrame:
    """
    Load the Wine Society CSV data with headers on the second line
    """
    # Read the CSV file, skipping the first line (download date) and using the second line as headers
    df = pd.read_csv(CSV_FILE, skiprows=1)

    print(f"Loaded {len(df)} wine purchases")
    print(f"Columns: {list(df.columns)}")

    return df


def clean_wine_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and prepare the wine data for analysis
    """
    # Create a copy to avoid modifying the original
    df_clean: pd.DataFrame = df.copy()

    # Clean product names - remove empty entries
    df_clean = pd.DataFrame(
        df_clean[df_clean["Product name"].notna() & (df_clean["Product name"] != "")]
    )

    # Convert purchase date to datetime
    df_clean["Purchase date"] = pd.to_datetime(
        df_clean["Purchase date"], format="%m/%d/%Y", errors="coerce"
    )

    # Convert purchase price to numeric, removing any currency symbols
    df_clean["Purchase price"] = pd.to_numeric(
        df_clean["Purchase price"], errors="coerce"
    )

    # Extract year from product names for vintage analysis
    df_clean["Vintage"] = (
        df_clean["Product name"].astype(str).str.extract(r"(\d{4})").astype(float)
    )

    # Extract wine region/country from product codes
    df_clean["Region_Code"] = df_clean["Product code"].astype(str).str[:2]

    # Create wine type categories based on product codes
    wine_type_mapping = {
        "RH": "Rhône",
        "BU": "Burgundy",
        "BJ": "Beaujolais",
        "CS": "Côtes de Saint-Emilion",
        "CM": "Médoc",
        "CB": "Bordeaux",
        "FC": "France Country",
        "SP": "Spain",
        "IT": "Italy",
        "US": "USA",
        "AU": "Australia",
        "SA": "South Africa",
        "AR": "Argentina",
        "CE": "Chile",
        "PW": "Portugal",
        "GE": "Germany",
        "HU": "Hungary",
        "BG": "Bulgaria",
        "MD": "Moldova",
        "SL": "Slovenia",
        "TU": "Turkey",
        "LO": "Loire",
        "SG": "Sparkling",
        "SH": "Sherry",
        "PN": "Port",
        "BW": "Sweet Wine",
        "EN": "English",
        "NZ": "New Zealand",
        "AL": "Alsace",
        "AA": "Austria",
        "GR": "Greece",
        "OC": "Mixed Cases",
        "MX": "Mixed Cases",
        "XC": "Food Hamper",
        "WC": "Mixed Cases",
        "LC": "Mixed Cases",
    }

    df_clean["Wine_Type"] = (
        df_clean["Region_Code"].replace(wine_type_mapping).fillna("Other")
    )

    # Create price categories
    df_clean["Price_Category"] = pd.cut(
        df_clean["Purchase price"],
        bins=[0, 10, 20, 50, 100, float("inf")],
        labels=["Under £10", "£10-20", "£20-50", "£50-100", "Over £100"],
    )

    # Extract month and year for time series analysis
    df_clean["Purchase_Year"] = df_clean["Purchase date"].dt.year
    df_clean["Purchase_Month"] = df_clean["Purchase date"].dt.month
    df_clean["Purchase_Quarter"] = df_clean["Purchase date"].dt.quarter

    # Clean drink date - extract years if present
    def extract_drink_years(drink_date: str) -> int | None:
        if pd.isna(drink_date) or drink_date == "" or drink_date == "0 - 0":
            return None
        # Extract years from format like "2017 - 2021" or "2020 - 2023"
        years = re.findall(r"\d{4}", str(drink_date))
        if len(years) >= 2:
            return int(years[0])  # Return start year
        return None

    df_clean["Drink_Start_Year"] = df_clean["Drink date"].apply(extract_drink_years)

    # Calculate age of wine at purchase
    df_clean["Wine_Age_At_Purchase"] = df_clean["Purchase_Year"] - df_clean["Vintage"]

    print(f"Cleaned data shape: {df_clean.shape}")
    print(f"Data types:\n{df_clean.dtypes}")

    return df_clean


def get_data_summary(df: pd.DataFrame) -> dict:
    """
    Generate summary statistics for the wine data
    """
    summary = {
        "total_purchases": len(df),
        "total_spent": df["Purchase price"].sum(),
        "avg_price": df["Purchase price"].mean(),
        "price_range": (df["Purchase price"].min(), df["Purchase price"].max()),
        "date_range": (df["Purchase date"].min(), df["Purchase date"].max()),
        "wine_types": df["Wine_Type"].value_counts().to_dict(),
        "price_categories": df["Price_Category"].value_counts().to_dict(),
        "regions": df["Region_Code"].value_counts().head(10).to_dict(),
        "vintage_range": (df["Vintage"].min(), df["Vintage"].max()),
    }

    return summary


def main() -> pd.DataFrame:
    """
    Main function to load, clean, and prepare wine data
    """
    print("Loading Wine Society purchase data...")

    # Load the data
    df_raw = load_wine_data()

    # Clean and prepare the data
    df_clean = clean_wine_data(df_raw)

    # Generate summary
    summary = get_data_summary(df_clean)

    print("\n=== WINE PURCHASE SUMMARY ===")
    print(f"Total purchases: {summary['total_purchases']}")
    print(f"Total spent: £{summary['total_spent']:,.2f}")
    print(f"Average price: £{summary['avg_price']:.2f}")
    print(
        f"Price range: £{summary['price_range'][0]:.2f} - £{summary['price_range'][1]:.2f}"
    )
    print(
        f"Date range: {summary['date_range'][0].strftime('%Y-%m-%d')}"
        f"to {summary['date_range'][1].strftime('%Y-%m-%d')}"
    )
    print(
        f"Vintage range: {summary['vintage_range'][0]:.0f} - {summary['vintage_range'][1]:.0f}"
    )

    print("\n=== WINE TYPES ===")
    for wine_type, count in summary["wine_types"].items():
        print(f"{wine_type}: {count}")

    print("\n=== PRICE CATEGORIES ===")
    for price_cat, count in summary["price_categories"].items():
        print(f"{price_cat}: {count}")

    print("\n=== TOP REGIONS ===")
    for region, count in list(summary["regions"].items())[:10]:
        print(f"{region}: {count}")

    return df_clean


if __name__ == "__main__":
    df = main()
