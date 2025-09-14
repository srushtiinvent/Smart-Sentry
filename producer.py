import pandas as pd
from kafka import KafkaProducer
import json
import time
import os

# --- Configuration ---
PROJECT_PATH = 'BakerHughesHackathon/' # Assuming you run this from your project root
TEST_DATA_PATH = os.path.join(PROJECT_PATH, 'data/test_FD001.txt')
KAFKA_TOPIC = 'engine_data'
KAFKA_SERVER = 'localhost:9092'

# Define column names
column_names = [ # As defined before
    'engine_id', 'time_in_cycles', 'op_setting_1', 'op_setting_2', 'op_setting_3',
    'sensor_1', 'sensor_2', 'sensor_3', 'sensor_4', 'sensor_5', 'sensor_6',
    'sensor_7', 'sensor_8', 'sensor_9', 'sensor_10', 'sensor_11', 'sensor_12',
    'sensor_13', 'sensor_14', 'sensor_15', 'sensor_16', 'sensor_17', 'sensor_18',
    'sensor_19', 'sensor_20', 'sensor_21'
]

# --- Initialize Kafka Producer ---
producer = KafkaProducer(
    bootstrap_servers=KAFKA_SERVER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# --- Load data and send to Kafka ---
test_df = pd.read_csv(TEST_DATA_PATH, sep=' ', header=None, names=column_names + ['ignore1', 'ignore2'])
test_df.drop(columns=['ignore1', 'ignore2'], inplace=True)

print(f"--- Streaming data to Kafka topic: {KAFKA_TOPIC} ---")

for index, row in test_df.iterrows():
    message = row.to_dict()
    producer.send(KAFKA_TOPIC, value=message)
    print(f"Sent message for engine {int(message['engine_id'])}, cycle {int(message['time_in_cycles'])}")
    time.sleep(0.05) # Simulate a real-time feed

producer.flush()
print("--- Data streaming complete. ---")