import pandas as pd
import numpy as np
import joblib
import json
import os
import time
from datetime import datetime, timezone
from kafka import KafkaConsumer
import psycopg2
from psycopg2 import OperationalError
import redis

# --- 1. CONFIGURATION AND ASSET LOADING ---
PROJECT_PATH = 'BakerHughesHackathon/'
MODEL_PATH = os.path.join(PROJECT_PATH, 'models/final_rf_model.pkl')
KAFKA_TOPIC = 'engine_data'
KAFKA_SERVER = 'localhost:9092'

DB_NAME = "smartsentry"
DB_USER = "user"
DB_PASSWORD = "password"
DB_HOST = "localhost"
DB_PORT = "5432"

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_CHANNEL = 'sentry_predictions'

final_model = joblib.load(MODEL_PATH)
features = [f'sensor_{i}' for i in range(1, 22)] + ['op_setting_1', 'op_setting_2', 'op_setting_3']

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping() # Check the connection
    print("✅ Redis connection successful.")
except redis.exceptions.ConnectionError as e:
    print(f"❌ Could not connect to Redis: {e}")
    redis_client = None

# --- 2. DATABASE FUNCTIONS ---

def create_db_connection():
    """Create a persistent connection to the PostgreSQL database."""
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        print("✅ Database connection successful.")
    except OperationalError as e:
        print(f"❌ Could not connect to the database: {e}")
    return conn

def create_tables(conn):
    """Create the necessary tables if they don't exist."""
    try:
        cur = conn.cursor()
        # Table for prediction results
        cur.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id SERIAL PRIMARY KEY, timestamp TIMESTAMPTZ NOT NULL, engine_id INTEGER,
                time_in_cycles INTEGER, current_phase VARCHAR(50), status VARCHAR(50),
                anomaly_score REAL, alert_message TEXT
            );
        """)
        # Table for throughput logs
        cur.execute("""
            CREATE TABLE IF NOT EXISTS throughput_logs (
                id SERIAL PRIMARY KEY, timestamp TIMESTAMPTZ NOT NULL, throughput_msg_per_sec REAL
            );
        """)
        conn.commit()
        print("✅ Database tables are ready.")
        cur.close()
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

def log_prediction_to_db(conn, data):
    """Log a prediction record to the 'predictions' table."""
    sql = """INSERT INTO predictions(timestamp, engine_id, time_in_cycles, current_phase, status, anomaly_score, alert_message)
             VALUES(%s, %s, %s, %s, %s, %s, %s);"""
    try:
        cur = conn.cursor()
        cur.execute(sql, (
            data['timestamp'], data.get('engine_id', -1), data.get('time_in_cycles', -1),
            data['current_phase'], data['status'], data['anomaly_score'], data['alert_message']
        ))
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"❌ Error logging prediction: {e}")
        conn.rollback()

def log_throughput_to_db(conn, throughput):
    """Log a throughput measurement to the 'throughput_logs' table."""
    sql = """INSERT INTO throughput_logs(timestamp, throughput_msg_per_sec) VALUES(%s, %s);"""
    try:
        cur = conn.cursor()
        cur.execute(sql, (datetime.now(timezone.utc), throughput))
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"❌ Error logging throughput: {e}")
        conn.rollback()

# --- 3. CORE LOGIC FUNCTIONS ---
# (The classify_phases_robust and predict_anomaly_and_phase functions remain the same as the last version)
def classify_phases_robust(engine_df):
    # ... (paste your full function here) ...
    engine_df=engine_df.copy();volatility=engine_df['op_setting_1'].rolling(window=15).std();stability_threshold=0.0019;engine_df['phase_label']='TRANSIENT';engine_df.loc[volatility<stability_threshold,'phase_label']='STEADY-STATE';rpm_sensor='sensor_7';smoothed_rpm=engine_df[rpm_sensor].rolling(window=30,min_periods=1).mean();rpm_trend=smoothed_rpm.diff();is_transient=engine_df['phase_label']!='STEADY-STATE';is_accelerating=rpm_trend>0;is_decelerating=rpm_trend<=0;engine_df.loc[is_transient&is_accelerating,'phase_label']='STARTUP';engine_df.loc[is_transient&is_decelerating,'phase_label']='SHUTDOWN';engine_df['phase_label']=engine_df['phase_label'].bfill();return engine_df

def predict_anomaly_and_phase(data_window_df):
    # ... (paste your full function here that returns the data contract) ...
    classified_window=classify_phases_robust(data_window_df);latest_data_point=classified_window.iloc[-1:];current_phase=latest_data_point['phase_label'].iloc[0];X_latest=latest_data_point[features];prediction=final_model.predict(X_latest)[0];probability=final_model.predict_proba(X_latest)[0];anomaly_status="ANOMALY" if prediction==1 else "NORMAL";confidence_score=float(probability[prediction]);result={"timestamp":datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),"current_phase":current_phase,"status":anomaly_status,"anomaly_score":round(confidence_score,4),"sensor_readings":{"temperature":round(latest_data_point['sensor_4'].iloc[0],2),"pressure":round(latest_data_point['sensor_11'].iloc[0],2),"rpm":round(latest_data_point['sensor_12'].iloc[0],2)},"alert_message":f"Anomaly detected during {current_phase} phase." if anomaly_status=="ANOMALY" else "System operating normally.","engine_id":int(latest_data_point['engine_id'].iloc[0]),"time_in_cycles":int(latest_data_point['time_in_cycles'].iloc[0])};return result

# --- 4. MAIN CONSUMER LOOP (with confirmation prompt) ---
if __name__ == '__main__':
    # Perform all setup first
    db_conn = create_db_connection()
    if db_conn:
        create_tables(db_conn)

    consumer = KafkaConsumer(KAFKA_TOPIC, bootstrap_servers=KAFKA_SERVER, auto_offset_reset='earliest', value_deserializer=lambda x: json.loads(x.decode('utf-8')))
    
    # --- NEW: Add a confirmation prompt before processing ---
    user_input = input("\nSetup complete. Ready to start processing data? (yes/no): ")
    
    if user_input.lower() not in ['yes', 'y']:
        print("Processing aborted by user. Exiting.")
        if db_conn:
            db_conn.close()
    else:
        print("--- Consumer is listening for messages... ---")
        engine_history = {}
        window_size = 50
        message_count = 0
        start_time = time.perf_counter()

        try:
            for message in consumer:
                message_count += 1
                data = message.value
                engine_id = data['engine_id']
                
                if engine_id not in engine_history: engine_history[engine_id] = []
                engine_history[engine_id].append(data)
                
                if len(engine_history[engine_id]) > window_size: engine_history[engine_id].pop(0)
                    
                if len(engine_history[engine_id]) == window_size:
                    window_df = pd.DataFrame(engine_history[engine_id])
                    prediction_result = predict_anomaly_and_phase(window_df)
                    if redis_client:
                        # Publish the JSON string to the Redis channel
                        redis_client.publish(REDIS_CHANNEL, json.dumps(prediction_result))
                        
                    print(json.dumps(prediction_result, indent=2))
                    if db_conn:
                        log_prediction_to_db(db_conn, prediction_result)

                if message_count % 200 == 0:
                    elapsed_time = time.perf_counter() - start_time
                    if elapsed_time > 0:
                        throughput = message_count / elapsed_time
                        print(f"\n--- STATUS: Throughput: {throughput:.2f} messages/sec ---\n")
                        if db_conn:
                            log_throughput_to_db(db_conn, throughput)
        except KeyboardInterrupt:
            print("\nShutting down consumer.")
        finally:
            if db_conn:
                db_conn.close()
                print("Database connection closed.")