# app.py

import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="GA4 Report Builder (Stable)",
    page_icon="✅",
    layout="wide",
)

st.title("✅ GA4 Report Builder (Stable Version)")
st.caption("A reliable app to build Google Analytics reports.")

# --- Pre-defined GA4 Dimensions and Metrics ---
GA4_DIMENSIONS = [
    "pagePath", "landingPage", "firstUserDefaultChannelGroup", "sessionDefaultChannelGroup",
    "country", "city", "deviceCategory", "browser", "operatingSystem", "fullPageUrl",
    "pageTitle", "source", "medium"
]
GA4_METRICS = [
    "sessions", "activeUsers", "newUsers", "screenPageViews", "engagementRate",
    "averageSessionDuration", "conversions"
]

# --- Authentication ---
try:
    # Use the same secrets structure
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    scoped_credentials = credentials.with_scopes(
        ["https://www.googleapis.com/auth/analytics.readonly"]
    )
    # Build the service object
    analytics = build("analyticsdata", "v1beta", credentials=scoped_credentials)
    GA4_PROPERTY_ID = st.secrets["ga4"]["property_id"]
except Exception as e:
    st.error(f"🚨 Authentication Error: Could not configure Google clients. Please check your Streamlit secrets. Error: {e}")
    st.stop()

# --- User Input Form ---
st.header("Build Your Report")

col1, col2 = st.columns(2)
with col1:
    selected_dimensions = st.multiselect(
        "Select Dimensions",
        options=sorted(GA4_DIMENSIONS),
        default=["pagePath", "firstUserDefaultChannelGroup"]
    )
with col2:
    selected_metrics = st.multiselect(
        "Select Metrics",
        options=sorted(GA4_METRICS),
        default=["sessions", "activeUsers"]
    )

today = datetime.date.today()
seven_days_ago = today - datetime.timedelta(days=7)
date_range = st.date_input(
    "Select a date range",
    value=(seven_days_ago, today)
)

# --- Report Generation ---
if st.button("Generate Report", type="primary"):
    if not selected_dimensions or not selected_metrics or len(date_range) != 2:
        st.warning("Please select at least one dimension, one metric, and a valid date range.")
    else:
        with st.spinner("Fetching data from Google Analytics..."):
            try:
                # Build the request body dictionary
                request_body = {
                    "dimensions": [{"name": dim} for dim in selected_dimensions],
                    "metrics": [{"name": metric} for metric in selected_metrics],
                    "dateRanges": [{
                        "startDate": date_range[0].strftime("%Y-%m-%d"),
                        "endDate": date_range[1].strftime("%Y-%m-%d")
                    }]
                }

                # Execute the request
                response = analytics.properties().runReport(
                    property=f"properties/{GA4_PROPERTY_ID}",
                    body=request_body
                ).execute()

                # Process the response into a DataFrame
                headers = [h['name'] for h in response.get('dimensionHeaders', [])] + \
                          [h['name'] for h in response.get('metricHeaders', [])]
                
                rows = []
                for row in response.get('rows', []):
                    row_values = [dv['value'] for dv in row.get('dimensionValues', [])] + \
                                 [mv['value'] for mv in row.get('metricValues', [])]
                    rows.append(row_values)

                if not rows:
                    st.info("No data found for the selected criteria.")
                else:
                    df = pd.DataFrame(rows, columns=headers)
                    st.success("Report Generated!")
                    st.dataframe(df)

            except Exception as e:
                st.error(f"An error occurred while running the report: {e}")
