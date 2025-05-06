import tkinter as tk
from tkinter import scrolledtext, messagebox
import pika
import threading
import json

class ChatClientGUI:
    def __init__(self, root, username, room, host="localhost", port=5672):
        self.root = root
        self.root.title(f"Chat - {username} in {room}")
        self.username = username
        self.room = room
        self.other_users = {}  # store others' positions
        
        # GUI elements
        # Visual Grid Canvas for Contact Tracing (Right Side)
        self.grid_size = 10
        self.canvas = tk.Canvas(self.root, width=self.grid_size*40, height=self.grid_size*40, bg="white", bd=2, relief="groove", highlightthickness=1)
        self.canvas.grid(row=0, column=2, rowspan=6, padx=10, pady=10)
        self.current_position = (0, 0)
        self.draw_grid()

        

        
        # Trading section        
        self.trade_frame = tk.Frame(root)
        self.trade_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        

        self.side_var = tk.StringVar(value="BUY")
        tk.OptionMenu(self.trade_frame, self.side_var, "BUY", "SELL").grid(row=0, column=0)

        self.symbol_entry = tk.Entry(self.trade_frame, width=8)
        self.symbol_entry.insert(0, "XYZ")
        self.symbol_entry.grid(row=0, column=1, padx=5)

        self.price_entry = tk.Entry(self.trade_frame, width=10)
        self.price_entry.grid(row=0, column=2, padx=5)
        self.price_entry.insert(0, "10.00")

        self.trade_button = tk.Button(self.trade_frame, text="Submit Trade", command=self.send_trade)
        self.trade_button.grid(row=0, column=3, padx=5)

        self.trade_log = scrolledtext.ScrolledText(root, state='disabled', wrap=tk.WORD, width=60, height=8, bd=2, relief="sunken")
        self.trade_log.grid(row=3, column=0, columnspan=2, padx=10, pady=5)
    
    
        #Chat
        self.chat_log = scrolledtext.ScrolledText(root, state='disabled', wrap=tk.WORD, width=60, height=20, bd=2, relief="sunken")
        self.chat_log.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        self.message_entry = tk.Entry(root, width=50)
        self.message_entry.grid(row=1, column=0, padx=10, pady=10)
        self.message_entry.bind("<Return>", self.send_message)

        self.send_button = tk.Button(root, text="Send", width=10, command=self.send_message)
        self.send_button.grid(row=1, column=1, padx=10, pady=10)
        
        
        
        # Connect to RabbitMQ
        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port))
            self.channel = self.connection.channel()

            # Setup exchange/queue
            self.exchange_name = f"room_{self.room}"
            self.channel.exchange_declare(exchange=self.exchange_name, exchange_type="fanout")
            result = self.channel.queue_declare(queue='', exclusive=True)
            self.queue_name = result.method.queue
            self.channel.queue_bind(exchange=self.exchange_name, queue=self.queue_name)

            # Start receiving messages-?
            #for response_channel
            self.response_connection = pika.BlockingConnection(pika.ConnectionParameters(host, port))
            self.response_channel = self.response_connection.channel()
            self.response_channel.exchange_declare(exchange="query-response", exchange_type="fanout")
            result = self.response_channel.queue_declare(queue='', exclusive=True)
            self.response_queue = result.method.queue
            self.response_channel.queue_bind(exchange="query-response", queue=self.response_queue)
            
            #for query_channel
            self.query_connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port))
            self.query_channel = self.query_connection.channel()
            self.query_channel.exchange_declare(exchange="query", exchange_type="fanout")

            # Setup position exchange for contact tracing
            self.grid_size = 10
            self.position_channel = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port)).channel()
            self.position_channel.exchange_declare(exchange="position", exchange_type="fanout")
            self.start_position_updates()
            
        

            # Set up trade exchange/queue
            self.trade_channel = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port)).channel()
            self.trade_channel.exchange_declare(exchange="orders", exchange_type="fanout")
            self.trade_channel.exchange_declare(exchange="trades", exchange_type="fanout")
            result = self.trade_channel.queue_declare(queue='', exclusive=True)
            self.trade_queue = result.method.queue
            self.trade_channel.queue_bind(exchange="trades", queue=self.trade_queue)
            self.start_trade_listener()
            
            self.start_listening()

        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to RabbitMQ:\n{e}")
            root.destroy()
            

            
        # Contact Query Button at the bottom
        self.query_button = tk.Button(self.root, text="Show Contacts", command=self.send_contact_query)
        self.query_button.grid(row=6, column=0, columnspan=2, pady=10)
        
        #moved 
        self.listen_for_query_response()
        
        
        self.listen_for_positions()

    def display_message(self, message):
        self.chat_log.config(state='normal')
        self.chat_log.insert(tk.END, message + '\n')
        self.chat_log.config(state='disabled')
        self.chat_log.see(tk.END)

    def send_message(self, event=None):
        message = self.message_entry.get().strip()
        if message:
            full_message = f"[{self.username}]: {message}"
            self.channel.basic_publish(exchange=self.exchange_name, routing_key="", body=full_message.encode())
            self.message_entry.delete(0, tk.END)

    def start_listening(self):
        def callback(ch, method, properties, body):
            self.display_message(body.decode())

        def listen():
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=callback,
                auto_ack=True
            )
            try:
                self.channel.start_consuming()
            except Exception as e:
                print("Error in listener:", e)

        threading.Thread(target=listen, daemon=True).start()


# ---------- Login Window ----------

    def send_trade(self):
        try:
            order = {
                "username": self.username,
                "side": self.side_var.get(),
                "symbol": self.symbol_entry.get().strip().upper(),
                "price": float(self.price_entry.get()),
                "quantity": 100
            }
            self.trade_channel.basic_publish(
                exchange="orders",
                routing_key="",
                body=json.dumps(order).encode()
            )
            self.display_trade(f"[ORDER SENT] {order['side']} {order['symbol']} at ${order['price']}")
        except Exception as e:
            messagebox.showerror("Trade Error", str(e))

    def display_trade(self, trade_msg):
        self.trade_log.config(state='normal')
        self.trade_log.insert(tk.END, trade_msg + '\n')
        self.trade_log.config(state='disabled')
        self.trade_log.see(tk.END)

    def start_trade_listener(self):
        def callback(ch, method, properties, body):
            trade = json.loads(body.decode())
            msg = f"[TRADE] {trade['buyer']} bought from {trade['seller']} {trade['symbol']} at ${trade['price']}"
            self.display_trade(msg)

        def listen():
            self.trade_channel.basic_consume(
                queue=self.trade_queue,
                on_message_callback=callback,
                auto_ack=True
            )
            try:
                self.trade_channel.start_consuming()
            except Exception as e:
                print("Trade listener error:", e)

        threading.Thread(target=listen, daemon=True).start()



    def start_position_updates(self):
        import random, time

        def clamp(val, min_val, max_val):
            return max(min_val, min(val, max_val))

        def move_loop():
            x = random.randint(0, self.grid_size - 1)
            y = random.randint(0, self.grid_size - 1)
            print(f"🚶 {self.username} starts at ({x}, {y})")

            while True:
                msg = {
                    "id": self.username,
                    "x": x,
                    "y": y
                }
                self.position_channel.basic_publish(
                    exchange="position",
                    routing_key="",
                    body=json.dumps(msg).encode()
                )
                print(f"📍 {self.username} moved to ({x}, {y})")
                self.current_position = (x, y)
                self.update_canvas_position(x, y)
                
                time.sleep(1)

                dx = random.choice([-1, 0, 1])
                dy = random.choice([-1, 0, 1])
                x = clamp(x + dx, 0, self.grid_size - 1)
                y = clamp(y + dy, 0, self.grid_size - 1)

        threading.Thread(target=move_loop, daemon=True).start()
                
    def send_contact_query(self):
        self.query_channel.basic_publish(
            exchange="query",
            routing_key="",
            body=self.username.encode()
        )
        print(f"[QUERY SENT] {self.username}")

    def display_contacts(self, person, contacts):
        if contacts:
            message = f"{person} has been in contact with:\n" + "\n".join(f"• {name}" for name in contacts)
        else:
            message = f"{person} has not been in contact with anyone."
        messagebox.showinfo("Contact List", message)

    def listen_for_query_response(self):
        def callback(ch, method, properties, body):
            data = json.loads(body.decode())
            person = data.get("person")
            contacts = data.get("contacts", [])
            self.root.after(0, lambda: self.display_contacts(person, contacts))

        self.response_channel.basic_consume(
            queue=self.response_queue,
            on_message_callback=callback,
            auto_ack=True
        )
        threading.Thread(target=self.response_channel.start_consuming, daemon=True).start()
        
    def listen_for_positions(self):
        def callback(ch, method, properties, body):
            data = json.loads(body.decode())
            if data["id"] != self.username:
                self.other_users[data["id"]] = (data["x"], data["y"])
                self.root.after(0, self.draw_grid)

        def start_listening():
            result = self.position_channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            self.position_channel.queue_bind(exchange="position", queue=queue_name)
            self.position_channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
            self.position_channel.start_consuming()

        threading.Thread(target=start_listening, daemon=True).start()


    def draw_grid(self):
        self.canvas.delete("all")
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                self.canvas.create_rectangle(i * 40, j * 40, (i + 1) * 40, (j + 1) * 40, outline="gray")
        
        
        # Draw others
        for user, (x, y) in self.other_users.items():
            self.canvas.create_oval(
                x * 40 + 10, y * 40 + 10,
                (x + 1) * 40 - 10, (y + 1) * 40 - 10,
                fill="red", tags="others"
            )
            self.canvas.create_text(
            x * 40 + 20, y * 40 + 35,
            text=user, font=("Arial", 8), fill="black", tags="others"
        )
        
        
        self.update_canvas_position(*self.current_position)

    def update_canvas_position(self, x, y):
        self.canvas.delete("me")
        self.canvas.create_oval(
            x * 40 + 5, y * 40 + 5,
            (x + 1) * 40 - 5, (y + 1) * 40 - 5,
            fill="blue", tags="me"
        )


def show_login():
    login_win = tk.Tk()
    login_win.title("Login to Chat")

    tk.Label(login_win, text="Username:").grid(row=0, column=0, padx=10, pady=10)
    username_entry = tk.Entry(login_win)
    username_entry.grid(row=0, column=1, padx=10, pady=10)

    tk.Label(login_win, text="Room:").grid(row=1, column=0, padx=10, pady=10)
    room_entry = tk.Entry(login_win)
    room_entry.grid(row=1, column=1, padx=10, pady=10)

    def start_chat():
        username = username_entry.get().strip()
        room = room_entry.get().strip() or "general"

        if not username:
            messagebox.showwarning("Missing Info", "Please enter a username.")
            return

        login_win.destroy()

        chat_root = tk.Tk()
        ChatClientGUI(chat_root, username, room)
        chat_root.mainloop()

    join_button = tk.Button(login_win, text="Join Chat", command=start_chat)
    join_button.grid(row=2, column=0, columnspan=2, pady=10)

    login_win.mainloop()


if __name__ == "__main__":
    show_login()
