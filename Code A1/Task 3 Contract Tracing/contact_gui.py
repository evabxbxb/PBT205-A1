import tkinter as tk
from tkinter import messagebox
import pika
import threading
import json

DEFAULT_GRID_SIZE = 10
DEFAULT_CELL_SIZE = 50

class ContactTracerGUI:
    def __init__(self, root, host="localhost", grid_size=DEFAULT_GRID_SIZE):
        self.root = root
        self.grid_size = grid_size
        self.cell_size = DEFAULT_CELL_SIZE if grid_size <= 20 else 30  # shrink if too large
        width = grid_size * self.cell_size
        height = grid_size * self.cell_size

        self.root.title(f"Contact Tracing Grid ({grid_size}x{grid_size})")
        self.canvas = tk.Canvas(root, width=width, height=height)
        self.canvas.pack()
        
        self.person_icons = {}
        self.positions = {}
        self.icon_ids = {}

        self.draw_grid()

        # Setup RabbitMQ connections
        self.conn_pos = pika.BlockingConnection(pika.ConnectionParameters(host))
        self.channel_pos = self.conn_pos.channel()

        self.conn_resp = pika.BlockingConnection(pika.ConnectionParameters(host))
        self.channel_resp = self.conn_resp.channel()

        self.conn_query = pika.BlockingConnection(pika.ConnectionParameters(host))
        self.channel_query = self.conn_query.channel()

        self.channel_pos.exchange_declare(exchange="position", exchange_type="fanout")
        self.channel_query.exchange_declare(exchange="query", exchange_type="fanout")
        self.channel_resp.exchange_declare(exchange="query-response", exchange_type="fanout")

        pos_result = self.channel_pos.queue_declare(queue='', exclusive=True)
        self.queue_pos = pos_result.method.queue
        self.channel_pos.queue_bind(exchange="position", queue=self.queue_pos)

        resp_result = self.channel_resp.queue_declare(queue='', exclusive=True)
        self.queue_resp = resp_result.method.queue
        self.channel_resp.queue_bind(exchange="query-response", queue=self.queue_resp)

        self.canvas.bind("<Button-1>", self.on_click)

        threading.Thread(target=self.listen_positions, daemon=True).start()
        threading.Thread(target=self.listen_responses, daemon=True).start()

    def draw_grid(self):
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                self.canvas.create_rectangle(
                    i * self.cell_size, j * self.cell_size,
                    (i + 1) * self.cell_size, (j + 1) * self.cell_size,
                    outline="gray"
                )

    def listen_positions(self):
        def callback(ch, method, properties, body):
            data = json.loads(body.decode())
            self.update_person(data["id"], data["x"], data["y"])
        self.channel_pos.basic_consume(queue=self.queue_pos, on_message_callback=callback, auto_ack=True)
        self.channel_pos.start_consuming()

    def listen_responses(self):
        def callback(ch, method, properties, body):
            data = json.loads(body.decode())
            self.show_contacts(data["person"], data["contacts"])
        self.channel_resp.basic_consume(queue=self.queue_resp, on_message_callback=callback, auto_ack=True)
        self.channel_resp.start_consuming()

    def update_person(self, person_id, x, y):
        # Delete previous icons
        if person_id in self.person_icons:
            icon, label = self.person_icons[person_id]
            self.canvas.delete(icon)
            self.canvas.delete(label)

        self.positions[person_id] = (x, y)
        fill = "red" if self.has_contact(x, y, person_id) else "blue"

        # Person circle
        icon = self.canvas.create_oval(
            x * self.cell_size + 5, y * self.cell_size + 5,
            (x + 1) * self.cell_size - 5, (y + 1) * self.cell_size - 20,
            fill=fill
        )

        # Label below icon
        label = self.canvas.create_text(
            x * self.cell_size + self.cell_size // 2,
            y * self.cell_size + self.cell_size - 8,
            text=person_id,
            font=("Helvetica", 9)
        )

        self.person_icons[person_id] = (icon, label)
        self.icon_ids[icon] = person_id
        self.icon_ids[label] = person_id

    def has_contact(self, x, y, current_id):
        for pid, (px, py) in self.positions.items():
            if pid != current_id and (px, py) == (x, y):
                return True
        return False

    def on_click(self, event):
        x, y = event.x, event.y
        clicked_item = self.canvas.find_closest(x, y)[0]
        person_id = self.icon_ids.get(clicked_item)
        if person_id:
            print(f"🖱️ Clicked on: {person_id}")
            self.send_query(person_id)

    def send_query(self, person_id):
        self.channel_query.basic_publish(
            exchange="query",
            routing_key="",
            body=person_id.encode()
        )

    def show_contacts(self, person, contacts):
        if contacts:
            msg = f"{person} has been in contact with:\n\n" + "\n".join(f"• {c}" for c in contacts)
        else:
            msg = f"{person} has not been in contact with anyone."
        messagebox.showinfo("Contact List", msg)

def launch_gui(grid_size=DEFAULT_GRID_SIZE):
    root = tk.Tk()
    app = ContactTracerGUI(root, grid_size=grid_size)
    root.mainloop()

if __name__ == "__main__":
    # 👇 You can change the grid size here!
    launch_gui(grid_size=20)
