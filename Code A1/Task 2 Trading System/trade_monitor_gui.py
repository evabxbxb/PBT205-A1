import tkinter as tk
import pika
import threading
import json

class TradeMonitor:
    def __init__(self, root, host="localhost", port=5672):
        self.root = root
        self.root.title("📊 Stock Trade Monitor")
        self.labels = {}

        # Header
        header = tk.Label(root, text="📊 Latest Prices", font=("Helvetica", 16, "bold"))
        header.pack(pady=10)

        # Frame to hold stock labels
        self.stock_frame = tk.Frame(root)
        self.stock_frame.pack(padx=20, pady=10)

        # RabbitMQ setup
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port))
        self.channel = self.connection.channel()

        self.channel.exchange_declare(exchange="trades", exchange_type="fanout")

        result = self.channel.queue_declare(queue='', exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(exchange="trades", queue=queue_name)

        # Start listener thread
        threading.Thread(target=self.start_consuming, args=(queue_name,), daemon=True).start()

    def start_consuming(self, queue_name):
        def callback(ch, method, properties, body):
            trade = json.loads(body.decode())
            print(f"📥 Received trade: {trade}")
            symbol = trade["symbol"]
            price = trade["price"]
            self.update_price(symbol, price)

        self.channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
        self.channel.start_consuming()

    def update_price(self, symbol, price):
        if symbol not in self.labels:
            # Create a new label for the stock
            label = tk.Label(self.stock_frame, text=f"{symbol}: ${price:.2f}", font=("Helvetica", 14))
            label.pack(anchor='w')
            self.labels[symbol] = label
        else:
            # Update the label
            self.labels[symbol].config(text=f"{symbol}: ${price:.2f}")

def launch_gui():
    root = tk.Tk()
    app = TradeMonitor(root)
    root.mainloop()

if __name__ == "__main__":
    launch_gui()
