import json
import psycopg2
from kafka import KafkaConsumer, KafkaProducer
from psycopg2 import sql
import datetime

def main():
    print("Started Parking Monitoring System")
main()

# Initialize slots count
global occupied_slots_2_wheelers
occupied_slots_2_wheelers = 0
global occupied_slots_4_wheelers
occupied_slots_4_wheelers = 0 

# Constants
TOTAL_SLOTS_2_WHEELERS = 50
TOTAL_SLOTS_4_WHEELERS = 100

# Processed iot sensor data
processed_data = {}

# Define processing logic
def process_sensor_data(sensor_data, cursor):
        
    global occupied_slots_2_wheelers
    global occupied_slots_4_wheelers

    # Process sensor data
    vehicle_type = sensor_data["vehicle_type"]
    slot_status = sensor_data["slot_status"]

    if vehicle_type == "2-wheelers":
        if occupied_slots_2_wheelers < TOTAL_SLOTS_2_WHEELERS and slot_status == "occupied":
            occupied_slots_2_wheelers += 1
        elif occupied_slots_2_wheelers > 0 and slot_status == "vacant":
            occupied_slots_2_wheelers -= 1
    if vehicle_type == "4-wheelers":
        if occupied_slots_4_wheelers < TOTAL_SLOTS_4_WHEELERS and slot_status == "occupied":
            occupied_slots_4_wheelers += 1
        elif occupied_slots_4_wheelers > 0 and slot_status == "vacant":
            occupied_slots_4_wheelers -= 1
    
    # Calculate available slots
    available_slots_2_wheelers = TOTAL_SLOTS_2_WHEELERS - occupied_slots_2_wheelers
    available_slots_4_wheelers = TOTAL_SLOTS_4_WHEELERS - occupied_slots_4_wheelers
    
    # Update the state table in PostgreSQL
    cursor.execute("""
        INSERT INTO state_table (vehicle_type, occupied_slots, available_slots)
        VALUES ('2-wheelers', %s, %s)
        ON CONFLICT (vehicle_type)
        DO UPDATE SET occupied_slots = %s, available_slots = %s;
        """, (occupied_slots_2_wheelers, available_slots_2_wheelers, occupied_slots_2_wheelers, available_slots_2_wheelers))
    
    cursor.execute("""
        INSERT INTO state_table (vehicle_type, occupied_slots, available_slots)
        VALUES ('4-wheelers', %s, %s)
        ON CONFLICT (vehicle_type)
        DO UPDATE SET occupied_slots = %s, available_slots = %s;
        """, (occupied_slots_4_wheelers, available_slots_4_wheelers, occupied_slots_4_wheelers, available_slots_4_wheelers))
    
# Kafka configuration
bootstrap_servers = 'kafka:9093'  # This is the service name defined in docker-compose.yml
consumer_topic = 'iot_sensor_data'

# Initialize Kafka consumer
consumer = KafkaConsumer(consumer_topic, bootstrap_servers=bootstrap_servers,
                         auto_offset_reset='earliest',
                         value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                         api_version=(0, 10, 1))

producer_topic = 'parking_processed_data'
# Initialize Kafka producer
producer = KafkaProducer(bootstrap_servers=bootstrap_servers,
                         api_version=(0, 10, 1),
                         value_serializer=lambda x: json.dumps(x).encode('utf-8'))

# PostgreSQL configuration
db_connection = psycopg2.connect(
    host="pms_postgres",
    database="sensor_data_db",
    user="monitoring_service_user",
    password="S3cret"
)
db_cursor = db_connection.cursor()

# Create the state table if not exists
db_cursor.execute("""
    CREATE TABLE IF NOT EXISTS state_table (
        vehicle_type VARCHAR(50) PRIMARY KEY,
        occupied_slots INTEGER,
        available_slots INTEGER
    )
""")

# Continuously check for new messages in Kafka topic
for message in consumer:
    sensor_data = message.value
    print(f'Sensor data in iterator: {sensor_data}')
    process_sensor_data(sensor_data, db_cursor)
    
    # Commit changes to the state table
    db_connection.commit()
    
    # Output state data from PostgreSQL
    db_cursor.execute("SELECT * FROM state_table")
    state_data = db_cursor.fetchall()
    for row in state_data:
        print(f"Vehicle Type: {row[0]}, Occupied Slots: {row[1]}, Available Slots: {row[2]}")
        
        # create JSON payload for consumer topic
        payload = {
            "vehicle_type" : row[0],
            "occupied_slots" : row[1],
            "available_slots" : row[2]
        }
        # Produce new data to Kafka
        producer.send(producer_topic, value=payload)
        
# Close database connection
db_cursor.close()
db_connection.close()
