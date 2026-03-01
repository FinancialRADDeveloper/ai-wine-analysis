import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.dash_table import DataTable
import plotly.express as px
import pandas as pd
from scrapers.wine_society.csv_importer import (
    load_wine_data,
    clean_wine_data,
    get_data_summary,
)

# Load and prepare the data
print("Loading wine data for dashboard...")
df_raw = load_wine_data()
df: pd.DataFrame = clean_wine_data(df_raw)
summary = get_data_summary(df)

# Initialize the Dash app
app = dash.Dash(__name__, title="Wine Society Purchase Analysis")

# Define the layout
app.layout = html.Div(
    [
        # Header
        html.H1(
            "🍷 Wine Society Purchase Analysis Dashboard",
            style={"textAlign": "center", "color": "#2c3e50", "marginBottom": 30},
        ),
        # Summary cards
        html.Div(
            [
                html.Div(
                    [
                        html.H3(
                            f"{summary['total_purchases']:,}",
                            style={"color": "#e74c3c", "margin": 0},
                        ),
                        html.P(
                            "Total Purchases", style={"margin": 0, "color": "#7f8c8d"}
                        ),
                    ],
                    className="summary-card",
                ),
                html.Div(
                    [
                        html.H3(
                            f"£{summary['total_spent']:,.0f}",
                            style={"color": "#27ae60", "margin": 0},
                        ),
                        html.P("Total Spent", style={"margin": 0, "color": "#7f8c8d"}),
                    ],
                    className="summary-card",
                ),
                html.Div(
                    [
                        html.H3(
                            f"£{summary['avg_price']:.1f}",
                            style={"color": "#f39c12", "margin": 0},
                        ),
                        html.P(
                            "Average Price", style={"margin": 0, "color": "#7f8c8d"}
                        ),
                    ],
                    className="summary-card",
                ),
                html.Div(
                    [
                        html.H3(
                            f"{summary['date_range'][0].strftime('%Y')} - {summary['date_range'][1].strftime('%Y')}",
                            style={"color": "#8e44ad", "margin": 0},
                        ),
                        html.P(
                            "Purchase Period", style={"margin": 0, "color": "#7f8c8d"}
                        ),
                    ],
                    className="summary-card",
                ),
            ],
            style={
                "display": "flex",
                "justifyContent": "space-around",
                "marginBottom": 30,
            },
        ),
        # Filters
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Wine Type:"),
                        dcc.Dropdown(
                            id="wine-type-filter",
                            options=[
                                {"label": t, "value": t}
                                for t in sorted(df["Wine_Type"].unique())
                            ],
                            value="All",
                            clearable=False,
                            style={"width": "100%"},
                        ),
                    ],
                    style={
                        "width": "30%",
                        "display": "inline-block",
                        "marginRight": "2%",
                    },
                ),
                html.Div(
                    [
                        html.Label("Price Range:"),
                        dcc.Dropdown(
                            id="price-filter",
                            options=[
                                {"label": p, "value": p}
                                for p in sorted(df["Price_Category"].dropna().unique())
                            ],
                            value="All",
                            clearable=False,
                            style={"width": "100%"},
                        ),
                    ],
                    style={
                        "width": "30%",
                        "display": "inline-block",
                        "marginRight": "2%",
                    },
                ),
                html.Div(
                    [
                        html.Label("Year Range:"),
                        dcc.RangeSlider(
                            id="year-slider",
                            min=df["Purchase_Year"].min(),
                            max=df["Purchase_Year"].max(),
                            step=1,
                            marks={
                                year: str(year)
                                for year in range(
                                    int(df["Purchase_Year"].min()),
                                    int(df["Purchase_Year"].max()) + 1,
                                    2,
                                )
                            },
                            value=[
                                df["Purchase_Year"].min(),
                                df["Purchase_Year"].max(),
                            ],
                            tooltip={"placement": "bottom", "always_visible": True},
                        ),
                    ],
                    style={"width": "35%", "display": "inline-block"},
                ),
            ],
            style={
                "marginBottom": 30,
                "padding": "20px",
                "backgroundColor": "#f8f9fa",
                "borderRadius": "10px",
            },
        ),
        # Charts row 1
        html.Div(
            [
                # Purchase timeline
                html.Div(
                    [dcc.Graph(id="purchase-timeline")],
                    style={"width": "50%", "display": "inline-block"},
                ),
                # Wine type distribution
                html.Div(
                    [dcc.Graph(id="wine-type-pie")],
                    style={"width": "50%", "display": "inline-block"},
                ),
            ]
        ),
        # Charts row 2
        html.Div(
            [
                # Price distribution
                html.Div(
                    [dcc.Graph(id="price-distribution")],
                    style={"width": "50%", "display": "inline-block"},
                ),
                # Regional analysis
                html.Div(
                    [dcc.Graph(id="regional-analysis")],
                    style={"width": "50%", "display": "inline-block"},
                ),
            ]
        ),
        # Charts row 3
        html.Div(
            [
                # Vintage analysis
                html.Div(
                    [dcc.Graph(id="vintage-analysis")],
                    style={"width": "50%", "display": "inline-block"},
                ),
                # Monthly spending pattern
                html.Div(
                    [dcc.Graph(id="monthly-pattern")],
                    style={"width": "50%", "display": "inline-block"},
                ),
            ]
        ),
        # Data table
        html.Div(
            [
                html.H3(
                    "Detailed Purchase Data",
                    style={"textAlign": "center", "marginTop": 30},
                ),
                DataTable(
                    id="wine-table",
                    columns=[{"name": i, "id": i} for i in df.columns],
                    data=df.to_dict("records"),
                    page_size=10,
                    style_table={"overflowX": "auto"},
                    style_cell={"textAlign": "left", "padding": "10px"},
                    style_header={
                        "backgroundColor": "#2c3e50",
                        "color": "white",
                        "fontWeight": "bold",
                    },
                ),
            ],
            style={"marginTop": 30},
        ),
        # Footer
        html.Div(
            [
                html.P(
                    "Data source: The Wine Society purchase history",
                    style={"textAlign": "center", "color": "#7f8c8d", "marginTop": 30},
                )
            ]
        ),
    ]
)


# Callback to filter data
@app.callback(
    [
        Output("purchase-timeline", "figure"),
        Output("wine-type-pie", "figure"),
        Output("price-distribution", "figure"),
        Output("regional-analysis", "figure"),
        Output("vintage-analysis", "figure"),
        Output("monthly-pattern", "figure"),
        Output("wine-table", "data"),
    ],
    [
        Input("wine-type-filter", "value"),
        Input("price-filter", "value"),
        Input("year-slider", "value"),
    ],
)
def update_charts(wine_type: str, price_range: str, year_range: tuple) -> tuple:
    try:
        # Filter the dataframe
        filtered_df: pd.DataFrame = df.copy()

        if wine_type != "All":
            filtered_df = pd.DataFrame(
                filtered_df[filtered_df["Wine_Type"] == wine_type]
            )

        if price_range != "All":
            filtered_df = pd.DataFrame(
                filtered_df[filtered_df["Price_Category"] == price_range]
            )

        filtered_df = pd.DataFrame(
            filtered_df[
                (filtered_df["Purchase_Year"] >= year_range[0])
                & (filtered_df["Purchase_Year"] <= year_range[1])
            ]
        )

        # Check if filtered data is empty
        if filtered_df.empty:
            # Return empty figures
            empty_fig = px.scatter(title="No data available for selected filters")
            empty_pie = px.pie(values=[1], names=["No Data"], title="No data available")
            empty_hist = px.histogram(title="No data available")
            empty_bar = px.bar(title="No data available")
            empty_scatter = px.scatter(title="No data available")
            empty_monthly = px.bar(title="No data available")

            return (
                empty_fig,
                empty_pie,
                empty_hist,
                empty_bar,
                empty_scatter,
                empty_monthly,
                [],
            )

        # 1. Purchase Timeline
        timeline_data = (
            filtered_df.groupby("Purchase date")["Purchase price"].sum().reset_index()
        )
        timeline_fig = px.line(
            timeline_data,
            x="Purchase date",
            y="Purchase price",
            title="Cumulative Spending Over Time",
            labels={"Purchase price": "Total Spent (£)", "Purchase date": "Date"},
        )
        timeline_fig.update_layout(showlegend=False)

        # 2. Wine Type Distribution
        wine_type_counts = filtered_df["Wine_Type"].value_counts()
        if len(wine_type_counts) > 0:
            pie_fig = px.pie(
                values=wine_type_counts.values,
                names=wine_type_counts.index,
                title="Distribution by Wine Type",
            )
        else:
            pie_fig = px.pie(
                values=[1], names=["No Data"], title="No Wine Types Available"
            )

        # 3. Price Distribution
        price_fig = px.histogram(
            filtered_df,
            x="Purchase price",
            nbins=20,
            title="Price Distribution",
            labels={"Purchase price": "Price (£)", "count": "Number of Purchases"},
        )
        price_fig.update_layout(showlegend=False)

        # 4. Regional Analysis
        region_data = filtered_df["Region_Code"].value_counts().head(10)
        if len(region_data) > 0:
            region_fig = px.bar(
                x=region_data.index,
                y=region_data.values,
                title="Top 10 Wine Regions",
                labels={"x": "Region Code", "y": "Number of Purchases"},
            )
        else:
            region_fig = px.bar(title="No Regional Data Available")
        region_fig.update_layout(showlegend=False)

        # 5. Vintage Analysis
        vintage_filtered = filtered_df[filtered_df["Vintage"].notna()]
        if len(vintage_filtered) > 0:
            vintage_data = vintage_filtered.groupby("Vintage")["Purchase price"].mean()
            vintage_fig = px.scatter(
                x=vintage_data.index,
                y=vintage_data.values,
                title="Average Price by Vintage",
                labels={"x": "Vintage", "y": "Average Price (£)"},
            )
        else:
            vintage_fig = px.scatter(title="No Vintage Data Available")
        vintage_fig.update_layout(showlegend=False)

        # 6. Monthly Pattern
        monthly_data = filtered_df.groupby("Purchase_Month")["Purchase price"].sum()
        if len(monthly_data) > 0:
            monthly_fig = px.bar(
                x=monthly_data.index,
                y=monthly_data.values,
                title="Total Spending by Month",
                labels={"x": "Month", "y": "Total Spent (£)"},
            )
        else:
            monthly_fig = px.bar(title="No Monthly Data Available")
        monthly_fig.update_layout(showlegend=False)

        # 7. Table data
        table_data = pd.DataFrame(
            filtered_df[
                [
                    "Product name",
                    "Product code",
                    "Purchase date",
                    "Purchase price",
                    "Wine_Type",
                    "Vintage",
                    "Region_Code",
                ]
            ]
        ).to_dict("records")

        return (
            timeline_fig,
            pie_fig,
            price_fig,
            region_fig,
            vintage_fig,
            monthly_fig,
            table_data,
        )

    except Exception as e:
        print(f"Error in update_charts: {e}")
        # Return empty figures on error
        empty_fig = px.scatter(title="Error occurred")
        empty_pie = px.pie(values=[1], names=["Error"], title="Error occurred")
        empty_hist = px.histogram(title="Error occurred")
        empty_bar = px.bar(title="Error occurred")
        empty_scatter = px.scatter(title="Error occurred")
        empty_monthly = px.bar(title="Error occurred")

        return (
            empty_fig,
            empty_pie,
            empty_hist,
            empty_bar,
            empty_scatter,
            empty_monthly,
            [],
        )


# Add custom CSS
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        <title>Wine Society Dashboard</title>
        <style>
            .summary-card {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
                min-width: 150px;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #ecf0f1;
                margin: 0;
                padding: 20px;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

if __name__ == "__main__":
    print("Starting Wine Society Dashboard...")
    print("Open your browser and go to: http://127.0.0.1:8050")
    app.run(debug=True, host="127.0.0.1", port=8050)
