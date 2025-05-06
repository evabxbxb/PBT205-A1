import tkinter as tk
from tkinter import scrolledtext, messagebox
import pika
import threading

""" tkinter: GUI toolkit.
scrolledtext: Widget with a scrollable text box.
messagebox: To show popup alerts.
pika: Python client to interact with RabbitMQ.
threading: Runs message listening in the background so the GUI stays responsive."""

class ChatClientGUI:
# Initializes a Chat Window
    
    def __init__(self, root, username, room, host="localhost", port=5672):
    # Constructor: init 
    # Takes in Tk root, username, room, and optional RabbitMQ connection info.
        self.root = root
        self.root.title(f"Chat - {username} in {room}")
            # f: formatted string literal
            # It's cleaner and easier than using "Chat - " + username + " in " + room
            # sets title
        self.username = username
            #stores username (standard pattern)
        self.room = room
            #stores room name

        # GUI elements
        self.chat_log = scrolledtext.ScrolledText(root, state='disabled', wrap=tk.WORD, width=60, height=20)
        self.chat_log.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
            # Read-only chat display area
        
        self.message_entry = tk.Entry(root, width=50)
        self.message_entry.grid(row=1, column=0, padx=10, pady=10)
        self.message_entry.bind("<Return>", self.send_message)
            # Message entry box. Pressing enter sends message.

        self.send_button = tk.Button(root, text="Send", width=10, command=self.send_message)
        self.send_button.grid(row=1, column=1, padx=10, pady=10)
            # Send Button
        

        # Connect to RabbitMQ
        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port))
            self.channel = self.connection.channel()

            # Setup exchange/queue EXCHANGE DECLARATION
            self.exchange_name = f"room_{self.room}"
            self.channel.exchange_declare(exchange=self.exchange_name, exchange_type="fanout")
            
            result = self.channel.queue_declare(queue='', exclusive=True)
            self.queue_name = result.method.queue
            # Queue Declaration: An exclusive, auto-deleted queue is created for the client.
            self.channel.queue_bind(exchange=self.exchange_name, queue=self.queue_name)
            # Queue Binding: The queue is bound to the room's exchange, enabling message reception.

            # Start receiving messages
            self.start_listening()

        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to RabbitMQ:\n{e}")
            root.destroy()

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
