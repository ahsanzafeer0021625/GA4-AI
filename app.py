# app.py

import streamlit as st
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from google.oauth2 import service_account
import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="GA4 Report Builder",
    page_icon="📊",
    layout="wide"
)

st.title("📊 GA4 Report Builder")
st.caption("Select your dimensions, metrics, and date range to build a GA4 report directly.")

# --- Authentication ---
try:
    # Use the same secrets structure
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    analytics_client = BetaAnalyticsDataClient(credentials=credentials)
    GA4_PROPERTY_ID = st.secrets["ga4"]["property_id"]
except Exception as e:
    st.error(f"🚨 Authentication Error: Could not configure Google clients. Please check your Streamlit secrets. Error: {e}")
    st.stop()

# --- User Input Form ---
st.header("Build Your Report")

# Create two columns for a cleaner layout
col1, col2 = st.columns(2)

with col1:
    # Use text_input for dimensions and metrics
    dimensions_input = st.text_input(
        "Enter Dimensions (comma-separated)", 
        "pagePath,firstUserDefaultChannelGroup"
    )
    metrics_input = st.text_input(
        "Enter Metrics (comma-separated)", 
        "sessions,activeUsers,screenPageViews"
    )

with col2:
    # Use date_input for a calendar picker
    today = datetime.date.today()
    last_week = today - datetime.timedelta(days=7)
    date_range = st.date_input(
        "Select a date range",
        (last_week, today) # Default to the last 7 days
    )

# --- Report Generation ---
if st.button("Generate Report"):
    # Validate that we have a date range and inputs
    if not dimensions_input or not metrics_input or len(date_range) != 2:
        st.warning("Please fill out all fields and select a valid date range.")
    else:
        # Parse the user's comma-separated input
        dimensions = [Dimension(name=dim.strip()) for dim in dimensions_input.split(',')]
        metrics = [Metric(name=metric.strip()) for metric in metrics_input.split(',')]

        # Run the report
        with st.spinner("Fetching data from Google Analytics..."):
            try:
                request = RunReportRequest(
                    property=f"properties/{GA4_PROPERTY_ID}",
                    dimensions=dimensions,
                    metrics=metrics,
                    date_ranges=[DateRange(
                        start_date=date_range[0].strftime("%Y-%m-%d"),
                        end_date=date_range[1].strftime("%Y-%m-%d")
                    )],
                )
                response = analytics_client.run_report(request, timeout=90)

                # Process the response into a DataFrame
                headers = [header.name for header in response.dimension_headers] + [header.name for header in response.metric_headers]
                rows = [[item.value for item in row.dimension_values] + [item.value for item in row.metric_values] for row in response.rows]
                
                if not rows:
                    st.info("No data found for the selected criteria.")
                else:
                    df = pd.DataFrame(rows, columns=headers)
                    st.success("Report Generated!")
                    st.dataframe(df)

            except Exception as e:
                st.error(f"An error occurred while running the report: {e}")
