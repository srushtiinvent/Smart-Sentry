import streamlit as st
import redis
import json
import pandas as pd
from datetime import datetime
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="Smart Sentry | Real-Time Monitoring",
    layout="wide"
)

# --- Redis Connection ---
@st.cache_resource
def get_redis_connection():
    return redis.Redis(host='localhost', port=6379, decode_responses=True)

redis_client = get_redis_connection()
pubsub = redis_client.pubsub()
REDIS_CHANNEL = 'sentry_predictions'
pubsub.subscribe(REDIS_CHANNEL)

# --- Initialize Session State ---
if 'history_df' not in st.session_state:
    st.session_state.history_df = pd.DataFrame(columns=[
        'time', 'engine_id', 'cycle', 'phase', 'status', 'score'
    ])
if 'latest_data' not in st.session_state:
    st.session_state.latest_data = {}
# --- NEW: Initialize the anomaly counter ---
if 'anomaly_count' not in st.session_state:
    st.session_state.anomaly_count = 0


# --- Sidebar for Controls ---
st.sidebar.header("Dashboard Controls")
refresh_rate = st.sidebar.slider(
    label="Refresh Rate (seconds)",
    min_value=0.1, max_value=5.0, value=1.0, step=0.1,
    help="Set the delay between data updates on the dashboard."
)


# --- Dashboard Layout with Placeholders ---
st.title("🚀 Smart Sentry: Real-Time Asset Monitoring")
header_placeholder = st.empty()
# --- NEW: Added a fourth column for the anomaly count ---
col1, col2, col3, col4 = st.columns(4)
phase_indicator = col1.empty()
status_indicator = col2.empty()
score_indicator = col3.empty()
anomaly_count_indicator = col4.empty() # Placeholder for the new widget

st.markdown("---")
# ... (rest of the layout placeholders are the same)
st.header("Sensor Readings")
sensor_col1, sensor_col2, sensor_col3 = st.columns(3)
temp_indicator = sensor_col1.empty()
pressure_indicator = sensor_col2.empty()
rpm_indicator = sensor_col3.empty()
st.markdown("---")
st.subheader("Alerts and System Details")
alert_placeholder = st.empty()
details_placeholder = st.empty()
st.markdown("---")
st.header("Anomaly Score History")
chart_placeholder = st.empty()

# --- Main Update Function ---
def update_dashboard(data):
    """Function to update all UI elements."""
    # ... (history_df and session_state.latest_data updates are the same)
    st.session_state.latest_data = data
    new_row = pd.DataFrame([{'time': datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')), 'engine_id': data['engine_id'], 'cycle': data['time_in_cycles'], 'phase': data['current_phase'], 'status': data['status'], 'score': data['anomaly_score']}])
    st.session_state.history_df = pd.concat([st.session_state.history_df, new_row], ignore_index=True).tail(100)

    # Update UI elements
    header_placeholder.caption(f"Last updated: {data['timestamp']} | Monitoring Engine #{data['engine_id']}")
    phase_indicator.metric(label="Current Phase", value=data['current_phase'])
    status_indicator.metric(label="System Status", value=f"{'🟢' if data['status'] == 'NORMAL' else '🔴'} {data['status']}")
    score_indicator.metric(label="Anomaly Score", value=f"{data['anomaly_score']:.4f}")
    
    # --- NEW: Update the anomaly count widget ---
    anomaly_count_indicator.metric(label="Total Anomalies Detected", value=st.session_state.anomaly_count)

    # ... (rest of the UI updates are the same)
    temp_indicator.metric(label="Temperature (°C)", value=f"{data['sensor_readings']['temperature']} °C")
    pressure_indicator.metric(label="Pressure (psi)", value=f"{data['sensor_readings']['pressure']} psi")
    rpm_indicator.metric(label="Engine RPM", value=f"{data['sensor_readings']['rpm']}")
    if data['status'] == "NORMAL": alert_placeholder.success(f"**Alert:** {data['alert_message']}")
    else: alert_placeholder.error(f"**Alert:** {data['alert_message']}")
    details_placeholder.text(f"Time in Cycles: {data['time_in_cycles']}")
    df_to_plot = st.session_state.history_df[st.session_state.history_df['engine_id'] == data['engine_id']]
    chart_placeholder.line_chart(df_to_plot.set_index('cycle')['score'])


# --- Optimized Real-Time Update Loop ---
if st.session_state.latest_data:
    update_dashboard(st.session_state.latest_data)

while True:
    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
    if message:
        data = json.loads(message['data'])
        
        # --- NEW: Increment the counter if an anomaly is detected ---
        if data['status'] == 'ANOMALY':
            st.session_state.anomaly_count += 1
            
        update_dashboard(data)
    
    time.sleep(refresh_rate)