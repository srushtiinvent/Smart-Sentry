import pandas as pd
import numpy as np
import joblib
import json
import os
import time # Add this import at the top of your script


# --- 1. LOAD MODELS AND ASSETS (Done once at startup) ---

# Define paths to your project assets
# Ensure these paths are correct for your environment
PROJECT_PATH = "BakerHughesHackathon/"
MODEL_PATH = os.path.join(PROJECT_PATH, 'models/final_rf_model.pkl')

# Load the trained RandomForestClassifier model
try:
    final_model = joblib.load(MODEL_PATH)
    print("✅ Final RandomForestClassifier model loaded successfully.")
except FileNotFoundError:
    print(f"❌ ERROR: Model file not found at {MODEL_PATH}. Please run the training script first.")
    final_model = None

# Define the feature list the model was trained on
features = [f'sensor_{i}' for i in range(1, 22)] + ['op_setting_1', 'op_setting_2', 'op_setting_3']


# --- 2. INCLUDE THE PHASE CLASSIFICATION LOGIC ---

def classify_phases_robust(engine_df):
    """Classifies operational phases for a window of engine data."""
    engine_df = engine_df.copy()
    # Rule 1: Use volatility to find STEADY-STATE
    volatility = engine_df['op_setting_1'].rolling(window=15).std()
    stability_threshold = 0.0019 # The optimal threshold you found
    
    engine_df['phase_label'] = 'TRANSIENT'
    engine_df.loc[volatility < stability_threshold, 'phase_label'] = 'STEADY-STATE'

    # Rule 2: Use trend to differentiate STARTUP vs. SHUTDOWN
    rpm_sensor = 'sensor_7'
    smoothed_rpm = engine_df[rpm_sensor].rolling(window=30, min_periods=1).mean()
    rpm_trend = smoothed_rpm.diff()
    
    is_transient = engine_df['phase_label'] != 'STEADY-STATE'
    is_accelerating = rpm_trend > 0
    is_decelerating = rpm_trend <= 0

    engine_df.loc[is_transient & is_accelerating, 'phase_label'] = 'STARTUP'
    engine_df.loc[is_transient & is_decelerating, 'phase_label'] = 'SHUTDOWN'
    
    engine_df['phase_label'] = engine_df['phase_label'].bfill()
    return engine_df


# --- 3. THE MAIN PREDICTION FUNCTION ---

def predict_anomaly_and_phase(data_window_df):
    """
    Predicts the phase and anomaly status from a window of recent data.
    
    Args:
        data_window_df (pd.DataFrame): A DataFrame containing the last ~30-50 cycles of data for a SINGLE engine.
    
    Returns:
        dict: A dictionary containing the prediction results for the LATEST data point.
    """
    if final_model is None:
        return {"error": "Model not loaded."}

    # 1. Classify the phase for the entire window to get context
    classified_window = classify_phases_robust(data_window_df)
    
    # 2. Get the phase of the MOST RECENT data point
    latest_data_point = classified_window.iloc[-1:]
    current_phase = latest_data_point['phase_label'].iloc[0]
    
    # 3. Get the features of the MOST RECENT data point
    X_latest = latest_data_point[features]
    
    # 4. Predict the anomaly status and probability
    prediction = final_model.predict(X_latest)[0]
    probability = final_model.predict_proba(X_latest)[0]
    
    anomaly_status = "ANOMALY" if prediction == 1 else "NORMAL"
    confidence_score = float(probability[prediction])
    
    # 5. Assemble and return the result
    result = {
        "engine_id": int(latest_data_point['engine_id'].iloc[0]),
        "time_in_cycles": int(latest_data_point['time_in_cycles'].iloc[0]),
        "current_phase": current_phase,
        "status": anomaly_status,
        "confidence": round(confidence_score, 4)
    }
    return result

import time # Add this import at the top of your script
import json # This is used in the print statement

# --- EXAMPLE USAGE WITH THROUGHPUT MEASUREMENT ---
if __name__ == '__main__':
    # This block demonstrates how to use the function and measure its throughput
    
    # Load test data to simulate the stream
    column_names = [ # Define column names as before
        'engine_id', 'time_in_cycles', 'op_setting_1', 'op_setting_2', 'op_setting_3',
        'sensor_1', 'sensor_2', 'sensor_3', 'sensor_4', 'sensor_5', 'sensor_6',
        'sensor_7', 'sensor_8', 'sensor_9', 'sensor_10', 'sensor_11', 'sensor_12',
        'sensor_13', 'sensor_14', 'sensor_15', 'sensor_16', 'sensor_17', 'sensor_18',
        'sensor_19', 'sensor_20', 'sensor_21'
    ]
    TEST_DATA_PATH = os.path.join(PROJECT_PATH, 'data/test_FD001.txt')
    test_df = pd.read_csv(TEST_DATA_PATH, sep=' ', header=None, names=column_names + ['ignore1', 'ignore2'])
    test_df.drop(columns=['ignore1', 'ignore2'], inplace=True)

    window_size = 50 
    
    # Simulate for a single engine (e.g., engine #3)
    engine_data = test_df[test_df['engine_id'] == 3].reset_index(drop=True)
    
    # --- Throughput Measurement Setup ---
    predictions_count = 0
    simulation_start_time = time.perf_counter()
    
    print("--- Starting Real-Time Simulation with Throughput Measurement ---")
    
    # Loop through the data as if it's arriving in real-time
    for i in range(window_size, len(engine_data)):
        current_window = engine_data.iloc[i-window_size:i]
        
        # Get the prediction
        prediction_result = predict_anomaly_and_phase(current_window)
        
        # Increment our prediction counter
        predictions_count += 1
        
        # Print the JSON output
        print(json.dumps(prediction_result))
        
    # --- Calculate and Print Throughput Summary ---
    simulation_end_time = time.perf_counter()
    total_duration = simulation_end_time - simulation_start_time
    
    # Calculate average throughput if duration is not zero
    if total_duration > 0:
        average_throughput = predictions_count / total_duration
    else:
        average_throughput = float('inf') # Handle case of very fast execution
    
    print("\n--- Throughput Performance Summary ---")
    print(f"Total Predictions Made: {predictions_count}")
    print(f"Total Simulation Time: {total_duration:.2f} seconds")
    print(f"Average Throughput: {average_throughput:.2f} predictions per second")