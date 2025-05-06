import pika
import json
from collections import defaultdict

# Track positions and contacts
current_positions = {}  # { person_id: (x, y) }
contacts = defaultdict(list)  # { person_id: [other_id, ...] }

def handle_position_update(data):
    person = data["id"]
    x, y = data["x"], data["y"]

    # Check for contact
    for other_person, (ox, oy) in current_positions.items():
        if other_person != person and (ox, oy) == (x, y):
            if other_person not in contacts[person]:
                contacts[person].append(other_person)
                contacts[other_person].append(person)
                print(f"👥 {person} met {other_person} at ({x}, {y})")

    current_positions[person] = (x, y)

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()

    # Declare exchanges
    channel.exchange_declare(exchange="position", exchange_type="fanout")
    channel.exchange_declare(exchange="query", exchange_type="fanout")
    channel.exchange_declare(exchange="query-response", exchange_type="fanout")

    # POSITION listener
    pos_result = channel.queue_declare(queue='', exclusive=True)
    pos_queue = pos_result.method.queue
    channel.queue_bind(exchange="position", queue=pos_queue)

    def on_position(ch, method, properties, body):
        data = json.loads(body.decode())
        handle_position_update(data)

    channel.basic_consume(queue=pos_queue, on_message_callback=on_position, auto_ack=True)

    # QUERY listener
    query_result = channel.queue_declare(queue='', exclusive=True)
    query_queue = query_result.method.queue
    channel.queue_bind(exchange="query", queue=query_queue)

    def on_query(ch, method, properties, body):
        person_id = body.decode()
        print(f"🔍 Query for {person_id}")
        contact_list = contacts.get(person_id, [])
        response = {
            "person": person_id,
            "contacts": contact_list
        }
        channel.basic_publish(
            exchange="query-response",
            routing_key="",
            body=json.dumps(response).encode()
        )

    channel.basic_consume(queue=query_queue, on_message_callback=on_query, auto_ack=True)

    print("📡 Tracker is running...")
    channel.start_consuming()

if __name__ == "__main__":
    main()
