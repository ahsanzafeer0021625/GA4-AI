# app.py

import streamlit as st
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    FilterExpression,
    Filter,
    StringFilter,
    RunReportRequest,
)
from google.oauth2 import service_account
import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="Advanced GA4 Report Builder",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Advanced GA4 Report Builder")
st.caption("Build a custom Google Analytics report using the selectors below.")

# --- Pre-defined GA4 Dimensions and Metrics for Dropdowns ---
GA4_DIMENSIONS = [
    "pagePath", "landingPage", "firstUserDefaultChannelGroup", "sessionDefaultChannelGroup",
    "country", "city", "deviceCategory", "browser", "operatingSystem", "fullPageUrl",
    "pageTitle", "source", "medium"
]
GA4_METRICS = [
    "sessions", "activeUsers", "newUsers", "screenPageViews", "engagementRate",
    "averageSessionDuration", "conversions", "totalRevenue"
]

# --- Authentication ---
try:
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    analytics_client = BetaAnalyticsDataClient(credentials=credentials)
    GA4_PROPERTY_ID = st.secrets["ga4"]["property_id"]
except Exception as e:
    st.error(f"🚨 Authentication Error: Could not configure Google clients. Please check your Streamlit secrets. Error: {e}")
    st.stop()

# --- User Input Form ---
st.header("1. Select Dimensions, Metrics, and Date Range")

col1, col2 = st.columns(2)
with col1:
    selected_dimensions = st.multiselect(
        "Select Dimensions",
        options=sorted(GA4_DIMENSIONS),
        default=["pagePath", "firstUserDefaultChannelGroup"]
    )
    selected_metrics = st.multiselect(
        "Select Metrics",
        options=sorted(GA4_METRICS),
        default=["sessions", "activeUsers"]
    )

with col2:
    today = datetime.date.today()
    seven_days_ago = today - datetime.timedelta(days=7)
    date_range = st.date_input(
        "Select a date range (max 90 days)",
        value=(seven_days_ago, today)
    )

st.header("2. (Optional) Filter by Landing Page")
landing_page_input = st.text_input(
    "Enter a specific landing page path to filter results (e.g., /blog/my-post)",
    help="Leave blank to get data for all landing pages."
)

# --- Report Generation ---
if st.button("Generate Report", type="primary"):
    if not selected_dimensions or not selected_metrics or len(date_range) != 2:
        st.warning("Please select at least one dimension, one metric, and a valid date range.")
    else:
        with st.spinner("Fetching data from Google Analytics..."):
            try:
                # 1. Build the base request
                request = RunReportRequest(
                    property=f"properties/{GA4_PROPERTY_ID}",
                    dimensions=[Dimension(name=dim) for dim in selected_dimensions],
                    metrics=[Metric(name=metric) for metric in selected_metrics],
                    date_ranges=[DateRange(
                        start_date=date_range[0].strftime("%Y-%m-%d"),
                        end_date=date_range[1].strftime("%Y-%m-%d")
                    )],
                )

                # 2. Add the landing page filter if provided by the user
                if landing_page_input:
                    request.dimension_filter = FilterExpression(
                        filter=Filter(
                            field_name="landingPage",
                            string_filter=StringFilter(
                                match_type=StringFilter.MatchType.CONTAINS,
                                value=landing_page_input
                            ),
                        )
                    )

                # 3. Run the report
                response = analytics_client.run_report(request, timeout=120)

                # 4. Process and display the results
                headers = [h.name for h in response.dimension_headers] + [h.name for h in response.metric_headers]
                rows = [[item.value for item in row.dimension_values] + [item.value for item in row.metric_values] for row in response.rows]
                
                if not rows:
                    st.info("No data found for the selected criteria.")
                else:
                    df = pd.DataFrame(rows, columns=headers)
                    st.success("Report Generated!")
                    st.dataframe(df)

            except Exception as e:
                st.error(f"An error occurred while running the report: {e}")
