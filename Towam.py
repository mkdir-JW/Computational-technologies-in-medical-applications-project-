import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import cv2
from pyzbar.pyzbar import decode
import qrcode
from PIL import Image, ImageTk
import os
from cryptography.fernet import Fernet

# Inicjalizacja bazy danych
def init_db():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS items
                      (id INTEGER PRIMARY KEY, name TEXT, category TEXT, quantity INTEGER, location TEXT)''')
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

# Dodanie przedmiotu do bazy
def add_item(name, category, quantity, location):
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO items (name, category, quantity, location) VALUES (?, ?, ?, ?)",
                   (name, category, quantity, location))
    cursor.execute("SELECT id FROM items WHERE name = ? LIMIT 1", (name,))
    item_id = cursor.fetchone()[0]
    generate_qr(item_id)
    conn.commit()
    conn.close()

# Pobranie listy przedmiotów
def get_items():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items")
    items = cursor.fetchall()
    conn.close()
    return items

# Generowanie kodu QR
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

# Funkcja do skanowania QR i wyświetlania szczegółowych informacji o przedmiocie
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
                cursor.execute("SELECT id, name, category, quantity, location FROM items WHERE id = ?", (item_id,))
                item_data = cursor.fetchone()
                conn.close()

                if item_data:
                    show_item_details(item_data)  
                else:
                    messagebox.showerror("Błąd", "Nie znaleziono przedmiotu o podanym ID!")
            else:
                messagebox.showerror("QR Weryfikacja", "Klucz z QR nie pasuje do klucza w bazie lub pliku!")
            cap.release()
            return
        cv2.imshow("Scan QR Code", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

# Funkcja do wyświetlania szczegółowych informacji o przedmiocie w nowym oknie
def show_item_details(item_data):
    item_id, name, category, quantity, location = item_data

    details_window = tk.Toplevel()
    details_window.title(f"Szczegóły przedmiotu {name}")
    details_window.geometry("300x200")

    tk.Label(details_window, text=f"ID: {item_id}").pack(pady=5)
    tk.Label(details_window, text=f"Nazwa: {name}").pack(pady=5)
    tk.Label(details_window, text=f"Kategoria: {category}").pack(pady=5)
    tk.Label(details_window, text=f"Ilość: {quantity}").pack(pady=5)
    tk.Label(details_window, text=f"Lokalizacja: {location}").pack(pady=5)

    tk.Button(details_window, text="Zamknij", command=details_window.destroy).pack(pady=10)

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

        tk.Label(frame, text="Kategoria:").grid(row=1, column=0, sticky="w")
        self.category_entry = tk.Entry(frame)
        self.category_entry.grid(row=1, column=1)

        tk.Label(frame, text="Ilość:").grid(row=2, column=0, sticky="w")
        self.quantity_entry = tk.Entry(frame)
        self.quantity_entry.grid(row=2, column=1)

        tk.Label(frame, text="Lokalizacja:").grid(row=3, column=0, sticky="w")
        self.location_entry = tk.Entry(frame)
        self.location_entry.grid(row=3, column=1)

        tk.Button(frame, text="Dodaj przedmiot", command=self.add_item).grid(row=4, column=0, columnspan=2, pady=10)

        self.tree = ttk.Treeview(self.root, columns=("ID", "Nazwa", "Kategoria", "Ilość", "Lokalizacja"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Nazwa", text="Nazwa")
        self.tree.heading("Kategoria", text="Kategoria")
        self.tree.heading("Ilość", text="Ilość")
        self.tree.heading("Lokalizacja", text="Lokalizacja")
        self.tree.pack(pady=10)
        tk.Button(self.root, text="Skanuj QR", command=scan_qr).pack(pady=5)
        tk.Button(self.root, text="Odśwież listę", command=self.refresh_items).pack(pady=5)

        self.refresh_items()

    def add_item(self):
        name = self.name_entry.get()
        category = self.category_entry.get()
        quantity = self.quantity_entry.get()
        location = self.location_entry.get()
        if not (name and category and quantity and location):
            messagebox.showwarning("Uwaga", "Wszystkie pola są wymagane!")
            return
        try:
            quantity = int(quantity)
        except ValueError:
            messagebox.showwarning("Uwaga", "Ilość musi być liczbą!")
            return

        add_item(name, category, quantity, location)
        self.refresh_items()
        messagebox.showinfo("Sukces", "Przedmiot dodany pomyślnie!")

    def refresh_items(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in get_items():
            self.tree.insert("", "end", values=item)

# Inicjalizacja aplikacji
if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = InventoryApp(root)
    root.mainloop()