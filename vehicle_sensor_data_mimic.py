#from confluent_kafka import Producer
from kafka import KafkaConsumer, KafkaProducer
import json
import time
import random

def delivery_report(err, msg):
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

def simulate_iot_data():
    vehicle_types = ["2-wheelers", "4-wheelers"]
    slot_statuses = ["occupied", "vacant"]

    # Kafka producer configuration
    bootstrap_servers = 'localhost:9092' 
    producer_topic = 'iot_sensor_data'

    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        api_version=(0, 10, 1)
    )

    while True:
        # Generate random data
        vehicle_type = random.choice(vehicle_types)
        slot_status = random.choice(slot_statuses)

        # Create JSON data
        data = {
            "vehicle_type": vehicle_type,
            "slot_status": slot_status
        }

        print(f"Vehicle Type: {vehicle_type}, Slot Status: {slot_status}")

        # Convert data to JSON string
        json_data = json.dumps(data)

        # Produce data to Kafka topic
        # producer.produce(producer_topic, json_data.encode('utf-8'), callback=delivery_report)
        producer.send(producer_topic, value=json_data.encode('utf-8'))
        # Wait for 6 seconds
        time.sleep(6)

        # Poll for message delivery report
        # producer.poll(0)

if __name__ == "__main__":
    simulate_iot_data()