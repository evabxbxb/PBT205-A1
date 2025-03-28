import pika
import json
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Query a person's contact history")
    parser.add_argument("person_id", help="Name of the person to query")
    parser.add_argument("--host", default="localhost", help="RabbitMQ host")
    return parser.parse_args()

def main():
    args = parse_args()
    person_id = args.person_id

    connection = pika.BlockingConnection(pika.ConnectionParameters(args.host))
    channel = connection.channel()

    # Declare exchanges
    channel.exchange_declare(exchange="query", exchange_type="fanout")
    channel.exchange_declare(exchange="query-response", exchange_type="fanout")

    # Set up a queue to receive responses
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange="query-response", queue=queue_name)

    # Send the query
    channel.basic_publish(exchange="query", routing_key="", body=person_id.encode())
    print(f"📨 Sent query for {person_id}. Waiting for response...")

    # Wait for the response (once)
    def callback(ch, method, properties, body):
        response = json.loads(body.decode())
        print(f"\n📋 Contact list for {response['person']}:")
        if response["contacts"]:
            for name in response["contacts"]:
                print(f" - {name}")
        else:
            print("No contacts found.")
        connection.close()

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

if __name__ == "__main__":
    main()
