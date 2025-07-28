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
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    scoped_credentials = credentials.with_scopes(
        ["https://www.googleapis.com/auth/analytics.readonly"]
    )
    analytics = build("analyticsdata", "v1beta", credentials=scoped_credentials)
    GA4_PROPERTY_ID = st.secrets["ga4"]["property_id"]
except Exception as e:
    st.error(f"🚨 Authentication Error: Please check your secrets. Error: {e}")
    st.stop()

# --- User Input Form ---
st.header("1. Select Dimensions and Metrics")
col1, col2 = st.columns(2)
with col1:
    selected_dimensions = st.multiselect(
        "Select Dimensions",
        options=sorted(GA4_DIMENSIONS),
        default=["sessionDefaultChannelGroup"]
    )
with col2:
    selected_metrics = st.multiselect(
        "Select Metrics",
        options=sorted(GA4_METRICS),
        default=["sessions"]
    )

st.header("2. Select Date Range and Filters (Optional)")
col_date, col_filter1, col_filter2 = st.columns(3)
with col_date:
    today = datetime.date.today()
    start_default = today - datetime.timedelta(days=8)
    end_default = today - datetime.timedelta(days=2)
    date_range = st.date_input(
        "Select a date range",
        value=(start_default, end_default)
    )
with col_filter1:
    channel_filter = st.text_input(
        "Filter by Channel Group",
        placeholder="e.g., Organic Search"
    )
with col_filter2:
    device_filter = st.selectbox(
        "Filter by Device",
        options=["All", "Desktop", "Mobile", "Tablet"]
    )

# --- Report Generation ---
if st.button("Generate Report", type="primary"):
    if not selected_dimensions or not selected_metrics or len(date_range) != 2:
        st.warning("Please select at least one dimension, one metric, and a valid date range.")
    else:
        with st.spinner("Fetching data from Google Analytics..."):
            try:
                # Build the request body
                request_body = {
                    "dimensions": [{"name": dim} for dim in selected_dimensions],
                    "metrics": [{"name": metric} for metric in selected_metrics],
                    "dateRanges": [{
                        "startDate": date_range[0].strftime("%Y-%m-%d"),
                        "endDate": date_range[1].strftime("%Y-%m-%d")
                    }]
                }

                all_filters = []
                if device_filter and device_filter != "All":
                    all_filters.append({
                        "filter": {
                            "fieldName": "deviceCategory",
                            "stringFilter": {"value": device_filter}
                        }
                    })
                
                if channel_filter:
                    all_filters.append({
                        "filter": {
                            "fieldName": "sessionDefaultChannelGroup",
                            "stringFilter": {"value": channel_filter}
                        }
                    })

                if all_filters:
                    request_body["dimensionFilter"] = {"andGroup": {"expressions": all_filters}}

                # Execute the request
                response = analytics.properties().runReport(
                    property=f"properties/{GA4_PROPERTY_ID}",
                    body=request_body
                ).execute()
                
                # --- NEW: CHECK FOR SAMPLING ---
                if response.get('samplingMetadatas'):
                    st.warning("⚠️ Data is sampled, which may cause minor discrepancies with the GA4 interface.", icon="⚠️")

                # Process the response
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
