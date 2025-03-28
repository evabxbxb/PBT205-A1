import pika
import json
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Send a trading order")
    parser.add_argument("username", help="Trader name")
    parser.add_argument("side", choices=["BUY", "SELL"], help="Order side")
    parser.add_argument("price", type=float, help="Price per share")
    parser.add_argument("--host", default="localhost", help="RabbitMQ host")
    parser.add_argument("--port", type=int, default=5672, help="RabbitMQ port")
    parser.add_argument("--symbol", default="XYZ", help="Stock symbol (e.g., XYZ, ABC)")
    return parser.parse_args()

def main():
    args = parse_args()

    # Connect to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=args.host, port=args.port))
    channel = connection.channel()

    # Declare exchange (fanout)
    channel.exchange_declare(exchange="orders", exchange_type="fanout")

    # Build the order message
    order = {
        "username": args.username,
        "side": args.side.upper(),
        "price": args.price,
        "quantity": 100,
        "symbol": args.symbol.upper()
    }


    # Send the message
    channel.basic_publish(
        exchange="orders",
        routing_key="",
        body=json.dumps(order).encode()
    )

    print(f"✅ Sent {order['side']} order at ${order['price']} by {order['username']}")
    connection.close()

if __name__ == "__main__":
    main()
