import pika
import json

order_books = {}  # e.g., { "XYZ": { "BUY": [...], "SELL": [...] } }

buy_orders = []
sell_orders = []

def match_order(order):
    symbol = order["symbol"]
    if symbol not in order_books:
        order_books[symbol] = {"BUY": [], "SELL": []}

    book = order_books[symbol]
    side = order["side"]

    trades = []

    if side == "BUY":
        book["SELL"].sort(key=lambda o: o["price"])
        for i, sell in enumerate(book["SELL"]):
            if order["price"] >= sell["price"]:
                matched_trade = {
                    "symbol": symbol,
                    "price": sell["price"],
                    "buyer": order["username"],
                    "seller": sell["username"],
                    "quantity": 100
                }
                del book["SELL"][i]
                trades.append(matched_trade)
                break
        if not trades:
            book["BUY"].append(order)

    else:  # SELL
        book["BUY"].sort(key=lambda o: o["price"], reverse=True)
        for i, buy in enumerate(book["BUY"]):
            if buy["price"] >= order["price"]:
                matched_trade = {
                    "symbol": symbol,
                    "price": order["price"],
                    "buyer": buy["username"],
                    "seller": order["username"],
                    "quantity": 100
                }
                del book["BUY"][i]
                trades.append(matched_trade)
                break
        if not trades:
            book["SELL"].append(order)

    return trades  # Always return a list


def callback(ch, method, properties, body):
    order = json.loads(body.decode())
    print(f"📥 Received order: {order}")

    trades = match_order(order)
    
    for trade in trades:
        print(f"✅ Trade executed: {trade}")
        ch.basic_publish(
            exchange="trades",
            routing_key="",
            body=json.dumps(trade).encode()
        )

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()

    # Set up orders exchange to receive
    channel.exchange_declare(exchange="orders", exchange_type="fanout")

    # Set up trades exchange to publish
    channel.exchange_declare(exchange="trades", exchange_type="fanout")

    # Declare a temporary queue for this exchange to listen
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange="orders", queue=queue_name)

    print("📡 Exchange is running. Waiting for orders...")
    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

if __name__ == "__main__":
    main()
