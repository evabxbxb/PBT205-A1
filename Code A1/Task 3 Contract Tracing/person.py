import pika
import json
import argparse
import random
import time

def parse_args():
    parser = argparse.ArgumentParser(description="Simulated person that moves around a grid")
    parser.add_argument("id", help="Unique person ID (e.g., alice)")
    parser.add_argument("--host", default="localhost", help="RabbitMQ host")
    parser.add_argument("--speed", type=float, default=1.0, help="Moves per second (default: 1)")
    parser.add_argument("--grid", type=int, default=10, help="Grid size (default: 10x10)")
    return parser.parse_args()

def clamp(val, min_val, max_val):
    return max(min_val, min(val, max_val))

def main():
    args = parse_args()
    person_id = args.id
    delay = 1.0 / args.speed
    grid_size = args.grid

    # Start at random position
    x = random.randint(0, grid_size - 1)
    y = random.randint(0, grid_size - 1)

    connection = pika.BlockingConnection(pika.ConnectionParameters(args.host))
    channel = connection.channel()

    channel.exchange_declare(exchange="position", exchange_type="fanout")

    print(f"🚶 {person_id} starting at ({x}, {y}) on {grid_size}x{grid_size} grid...")

    while True:
        # Publish position
        message = {
            "id": person_id,
            "x": x,
            "y": y
        }

        channel.basic_publish(exchange="position", routing_key="", body=json.dumps(message).encode())
        print(f"📍 {person_id} moved to ({x}, {y})")

        time.sleep(delay)

        # Choose random direction (like a King in chess)
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        x = clamp(x + dx, 0, grid_size - 1)
        y = clamp(y + dy, 0, grid_size - 1)

if __name__ == "__main__":
    main()
