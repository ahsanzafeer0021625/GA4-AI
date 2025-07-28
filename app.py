# app.py

import streamlit as st
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from google.oauth2 import service_account
import google.generativeai as genai
import json

# --- Page Configuration ---
st.set_page_config(
    page_title="GA4 AI Analyst",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 GA4 AI Analyst")
st.caption("Ask any question about your Google Analytics 4 data and get an expert answer.")

# --- Authentication and Client Setup ---
try:
    # Construct credentials from Streamlit secrets
    creds_json = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"].replace('\\n', '\n'),
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
    }

    credentials = service_account.Credentials.from_service_account_info(creds_json)
    analytics_client = BetaAnalyticsDataClient(credentials=credentials)
    GA4_PROPERTY_ID = st.secrets["ga4"]["property_id"]

    # Configure Gemini
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

except (KeyError, FileNotFoundError):
    st.error("🚨 Configuration Error: Please set up your secrets in the `.streamlit/secrets.toml` file.")
    st.stop()


# --- Tool Definition ---
@st.cache_data
def get_analytics_report(metrics: list[str], dimensions: list[str], start_date: str, end_date: str):
    """Runs a report on the GA4 Data API. This is the tool the AI will use."""
    print(f"Running GA4 Report: Dimensions={dimensions}, Metrics={metrics}")
    try:
        request = RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            dimensions=[Dimension(name=dim) for dim in dimensions],
            metrics=[Metric(name=metric) for metric in metrics],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )
        response = analytics_client.run_report(request)
        headers = [header.name for header in response.dimension_headers] + [header.name for header in response.metric_headers]
        rows = [[item.value for item in row.dimension_values] + [item.value for item in row.metric_values] for row in response.rows]
        return pd.DataFrame(rows, columns=headers).to_string()
    except Exception as e:
        return f"Tool execution failed with error: {e}"


# --- Agent Setup ---
system_instruction = """
You are a helpful and precise Google Analytics expert. Your only job is to answer questions using the data you can fetch with the get_analytics_report tool.
DIMENSION GUIDE:
- For a 'landing page' or where sessions 'started', use the `landingPage` dimension.
- For general page traffic, use `pagePath`.
- For traffic sources, use `firstUserDefaultChannelGroup`.
"""

model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    tools=[get_analytics_report],
    system_instruction=system_instruction
)

# --- Chat Interface Logic ---
if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(history=[])

for message in st.session_state.chat.history:
    role = "user" if message.role == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

if prompt := st.chat_input("Ask a question about your GA4 data..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Thinking..."):
        response = st.session_state.chat.send_message(prompt)

    with st.chat_message("assistant"):
        st.markdown(response.text)