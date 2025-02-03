import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import cv2
from pyzbar.pyzbar import decode
import qrcode
from PIL import Image, ImageTk
import os
from cryptography.fernet import Fernet
from datetime import datetime
def init_db():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS items
                      (id INTEGER PRIMARY KEY, name TEXT, description TEXT, quantity INTEGER, owner TEXT, status TEXT, date TEXT, borrower TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS encryption_key
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT)''')
    cursor.execute("SELECT key FROM encryption_key LIMIT 1")
    key_in_db = cursor.fetchone()
    if not key_in_db:
        key = Fernet.generate_key().decode()
        cursor.execute("INSERT INTO encryption_key (key) VALUES (?)", (key,))
        with open("key.txt", "w") as key_file:
            key_file.write(key)
        print("Klucz wygenerowano i zapisano.")
    conn.commit()
    conn.close()


def add_item(name, description, quantity, owner):
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO items (name, description, quantity, owner, status, date, borrower) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (name, description, quantity, owner, "Dostępny", None, None))
    cursor.execute("SELECT id FROM items WHERE name = ? LIMIT 1", (name,))
    item_id = cursor.fetchone()[0]
    generate_qr(item_id)
    conn.commit()
    conn.close()


def get_items():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items")
    items = cursor.fetchall()
    conn.close()
    return items

def generate_qr(item_id):
    with open("key.txt", "r") as key_file:
        key = key_file.read()

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"Item ID: {item_id}\nKey: {key}")
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    folder_path = os.path.join(os.getcwd(), 'qrcodes')
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, f'item_{item_id}.png')
    img.save(file_path)
    print(f"Kod QR zapisany w: {file_path}")


def scan_qr():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT key FROM encryption_key LIMIT 1")
    key_in_db = cursor.fetchone()[0]
    conn.close()

    with open("key.txt", "r") as key_file:
        key_in_file = key_file.read()

    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        for barcode in decode(frame):
            qr_data = barcode.data.decode('utf-8')
            qr_lines = qr_data.split("\n")
            qr_key = None
            item_id = None
            for line in qr_lines:
                if line.startswith("Key:"):
                    qr_key = line.split("Key: ")[1]
                if line.startswith("Item ID:"):
                    item_id = line.split("Item ID: ")[1]
            if qr_key == key_in_db == key_in_file:
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, description, quantity, owner, status, borrower FROM items WHERE id = ?", (item_id,))
                item_data = cursor.fetchone()

                if item_data:
                    item_id, name, description, quantity, owner, status, borrower = item_data

                    if status == "Dostępny":
                        borrower_name = ask_borrower_details()
                        if not borrower_name:
                            cap.release()
                            return
                        new_status = "Wypożyczono"
                        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute("UPDATE items SET status = ?, date = ?, borrower = ? WHERE id = ?", 
                                       (new_status, date, borrower_name, item_id))
                    else:
                        new_status = "Dostępny"
                        cursor.execute("UPDATE items SET status = ?, date = ?, borrower = NULL WHERE id = ?", 
                                       (new_status, None, item_id))

                    conn.commit()
                    messagebox.showinfo("Status", f"Przedmiot '{name}' zmienił status na: {new_status}")
                else:
                    messagebox.showerror("Błąd", "Nie znaleziono przedmiotu o podanym ID!")
                conn.close()
                cap.release()
                return
            else:
                messagebox.showerror("QR Weryfikacja", "Klucz z QR nie pasuje do klucza w bazie lub pliku!")
        cv2.imshow("Scan QR Code", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()


def ask_borrower_details():
    borrower_window = tk.Toplevel()
    borrower_window.title("Dane osoby wypożyczającej")
    borrower_window.geometry("300x150")

    tk.Label(borrower_window, text="Podaj dane osoby wypożyczającej:").pack(pady=10)
    borrower_entry = tk.Entry(borrower_window, width=30)
    borrower_entry.pack(pady=5)

    borrower_name = []

    def submit_borrower():
        name = borrower_entry.get()
        if name:
            borrower_name.append(name)
            borrower_window.destroy()
        else:
            messagebox.showwarning("Uwaga", "Pole nie może być puste!")

    tk.Button(borrower_window, text="Zatwierdź", command=submit_borrower).pack(pady=10)
    borrower_window.wait_window()
    return borrower_name[0] if borrower_name else None

class InventoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ewidencja Przedmiotów")
        self.setup_ui()

    def setup_ui(self):
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.pack(pady=10)

        tk.Label(frame, text="Nazwa:").grid(row=0, column=0, sticky="w")
        self.name_entry = tk.Entry(frame)
        self.name_entry.grid(row=0, column=1)

        tk.Label(frame, text="Opis:").grid(row=1, column=0, sticky="w")
        self.description_entry = tk.Entry(frame)
        self.description_entry.grid(row=1, column=1)

        tk.Label(frame, text="Ilość:").grid(row=2, column=0, sticky="w")
        self.quantity_entry = tk.Entry(frame)
        self.quantity_entry.grid(row=2, column=1)

        tk.Label(frame, text="Właściciel:").grid(row=3, column=0, sticky="w")
        self.owner_entry = tk.Entry(frame)
        self.owner_entry.grid(row=3, column=1)

        tk.Button(frame, text="Dodaj przedmiot", command=self.add_item).grid(row=4, column=0, columnspan=2, pady=10)

        self.tree = ttk.Treeview(self.root, columns=("ID", "Nazwa", "Opis", "Ilość", "Właściciel", "Status", "Data", "Wypożyczający"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Nazwa", text="Nazwa")
        self.tree.heading("Opis", text="Opis")
        self.tree.heading("Ilość", text="Ilość")
        self.tree.heading("Właściciel", text="Właściciel")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Data", text="Data")
        self.tree.heading("Wypożyczający", text="Wypożyczający")
        self.tree.pack(pady=10)

        tk.Button(self.root, text="Skanuj QR", command=scan_qr).pack(pady=5)
        tk.Button(self.root, text="Odśwież listę", command=self.refresh_items).pack(pady=5)

        self.refresh_items()

    def add_item(self):
        name = self.name_entry.get()
        description = self.description_entry.get()
        quantity = self.quantity_entry.get()
        owner = self.owner_entry.get()
        if not (name and description and quantity and owner):
            messagebox.showwarning("Uwaga", "Wszystkie pola są wymagane!")
            return
        try:
            quantity = int(quantity)
        except ValueError:
            messagebox.showwarning("Uwaga", "Ilość musi być liczbą!")
            return

        add_item(name, description, quantity, owner)
        self.refresh_items()
        messagebox.showinfo("Sukces", "Przedmiot dodany pomyślnie!")

    def refresh_items(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in get_items():
            self.tree.insert("", "end", values=item)

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = InventoryApp(root)
    root.mainloop() 