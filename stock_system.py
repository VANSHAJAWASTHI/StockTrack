import json
import os
import csv
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import sqlite3
import hashlib
from datetime import datetime, timedelta

# Constants
DB_FILE = "stock_maintenance.db"

# Utility functions for password hashing
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Database Setup and Access Layer ---
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.create_tables()

    def create_tables(self):
        c = self.conn.cursor()
        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'staff'))
        )''')
        # Stock table
        c.execute('''CREATE TABLE IF NOT EXISTS stock (
            item_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            location TEXT NOT NULL,
            expiry_date TEXT
        )''')
        # Suppliers table
        c.execute('''CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT
        )''')
        # Purchase orders table
        c.execute('''CREATE TABLE IF NOT EXISTS purchase_orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id TEXT NOT NULL,
            supplier_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'received')),
            FOREIGN KEY(item_id) REFERENCES stock(item_id),
            FOREIGN KEY(supplier_id) REFERENCES suppliers(supplier_id)
        )''')
        # Audit log table
        c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            timestamp TEXT NOT NULL
        )''')
        self.conn.commit()

    # User methods
    def add_user(self, username, password, role):
        c = self.conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                      (username, hash_password(password), role))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def verify_user(self, username, password):
        c = self.conn.cursor()
        c.execute("SELECT password, role FROM users WHERE username=?", (username,))
        row = c.fetchone()
        if row and hash_password(password) == row[0]:
            return row[1]  # return role
        return None

    # Stock methods
    def add_stock(self, item_id, name, quantity, price, location, expiry_date=None):
        c = self.conn.cursor()
        try:
            c.execute('''INSERT INTO stock (item_id, name, quantity, price, location, expiry_date)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (item_id, name, quantity, price, location, expiry_date))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_stock_quantity(self, item_id, quantity):
        c = self.conn.cursor()
        c.execute("UPDATE stock SET quantity=? WHERE item_id=?", (quantity, item_id))
        self.conn.commit()

    def update_stock(self, item_id, name=None, quantity=None, price=None, location=None, expiry_date=None):
        c = self.conn.cursor()
        # Build dynamic query
        fields = []
        params = []
        if name is not None:
            fields.append("name=?")
            params.append(name)
        if quantity is not None:
            fields.append("quantity=?")
            params.append(quantity)
        if price is not None:
            fields.append("price=?")
            params.append(price)
        if location is not None:
            fields.append("location=?")
            params.append(location)
        if expiry_date is not None:
            fields.append("expiry_date=?")
            params.append(expiry_date)
        if not fields:
            return
        params.append(item_id)
        query = "UPDATE stock SET " + ", ".join(fields) + " WHERE item_id=?"
        c.execute(query, params)
        self.conn.commit()

    def delete_stock(self, item_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM stock WHERE item_id=?", (item_id,))
        self.conn.commit()

    def get_stock(self, item_id=None, name=None):
        c = self.conn.cursor()
        if item_id:
            c.execute("SELECT * FROM stock WHERE item_id=?", (item_id,))
            return c.fetchone()
        elif name:
            c.execute("SELECT * FROM stock WHERE LOWER(name)=?", (name.lower(),))
            return c.fetchall()
        else:
            c.execute("SELECT * FROM stock")
            return c.fetchall()

    def get_low_stock(self, threshold=5):
        c = self.conn.cursor()
        c.execute("SELECT * FROM stock WHERE quantity < ?", (threshold,))
        return c.fetchall()

    def total_inventory_value(self):
        c = self.conn.cursor()
        c.execute("SELECT SUM(quantity * price) FROM stock")
        result = c.fetchone()
        return result[0] if result and result[0] else 0.0

    # Supplier methods
    def add_supplier(self, name, contact):
        c = self.conn.cursor()
        c.execute("INSERT INTO suppliers (name, contact) VALUES (?, ?)", (name, contact))
        self.conn.commit()

    def get_suppliers(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM suppliers")
        return c.fetchall()

    def delete_supplier(self, supplier_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM suppliers WHERE supplier_id=?", (supplier_id,))
        self.conn.commit()

    # Purchase order methods
    def add_purchase_order(self, item_id, supplier_id, quantity):
        c = self.conn.cursor()
        order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''INSERT INTO purchase_orders (item_id, supplier_id, quantity, order_date, status)
                     VALUES (?, ?, ?, ?, ?)''',
                  (item_id, supplier_id, quantity, order_date, 'pending'))
        self.conn.commit()

    def get_purchase_orders(self, status=None):
        c = self.conn.cursor()
        if status:
            c.execute("SELECT * FROM purchase_orders WHERE status=?", (status,))
        else:
            c.execute("SELECT * FROM purchase_orders")
        return c.fetchall()

    def update_purchase_order_status(self, order_id, status):
        c = self.conn.cursor()
        c.execute("UPDATE purchase_orders SET status=? WHERE order_id=?", (status, order_id))
        self.conn.commit()

    # Audit log
    def log_action(self, username, action):
        c = self.conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO audit_log (username, action, timestamp) VALUES (?, ?, ?)",
                  (username, action, timestamp))
        self.conn.commit()

    def close(self):
        self.conn.close()

# --- Main Stock Maintenance System ---
class StockMaintenanceSystem:
    def __init__(self, username, role):
        self.db = Database()
        self.username = username
        self.role = role

    def log(self, action):
        self.db.log_action(self.username, action)

    # Stock management
    def add_item(self):
        print("\n--- Add New Stock Item ---")
        item_id = input("Enter item ID: ").strip()
        if not item_id:
            print("Item ID cannot be empty.")
            return
        if self.db.get_stock(item_id=item_id):
            print("Item ID already exists.")
            return
        name = input("Enter item name: ").strip()
        if not name:
            print("Item name cannot be empty.")
            return
        try:
            quantity = int(input("Enter quantity: "))
            price = float(input("Enter price per unit: "))
        except ValueError:
            print("Invalid quantity or price. Must be numbers.")
            return
        location = input("Enter location (warehouse/store): ").strip()
        expiry_date = input("Enter expiry date (YYYY-MM-DD) or leave blank: ").strip()
        if expiry_date:
            try:
                datetime.strptime(expiry_date, "%Y-%m-%d")
            except ValueError:
                print("Invalid date format. Skipping expiry date.")
                expiry_date = None
        else:
            expiry_date = None
        if self.db.add_stock(item_id, name, quantity, price, location, expiry_date):
            print(f"Item '{name}' added successfully.")
            self.log(f"Added item {item_id} - {name}")
        else:
            print("Failed to add item. Item ID may already exist.")

    def update_quantity(self):
        print("\n--- Update Stock Quantity ---")
        item_id = input("Enter item ID to update: ").strip()
        stock_item = self.db.get_stock(item_id=item_id)
        if not stock_item:
            print("Item not found.")
            return
        try:
            quantity = int(input("Enter new quantity: "))
        except ValueError:
            print("Invalid quantity. Must be an integer.")
            return
        self.db.update_stock_quantity(item_id, quantity)
        print("Quantity updated.")
        self.log(f"Updated quantity for item {item_id} to {quantity}")

    def search_item(self):
        print("\n--- Search Stock Item ---")
        query = input("Enter item ID or name to search: ").strip().lower()
        results = []
        stock_item = self.db.get_stock(item_id=query)
        if stock_item:
            results.append(stock_item)
        else:
            results = self.db.get_stock(name=query)
        if results:
            for item in results:
                print(f"ID: {item[0]}, Name: {item[1]}, Quantity: {item[2]}, Price: {item[3]}, Location: {item[4]}, Expiry: {item[5]}")
        else:
            print("No matching item found.")

    def view_stock(self):
        print("\n--- Current Stock ---")
        stock_items = self.db.get_stock()
        if not stock_items:
            print("Stock is empty.")
            return
        print(f"{'ID':<10} {'Name':<20} {'Qty':<6} {'Price':<10} {'Location':<15} {'Expiry Date':<12}")
        print("-" * 75)
        for item in stock_items:
            expiry = item[5] if item[5] else "-"
            print(f"{item[0]:<10} {item[1]:<20} {item[2]:<6} {item[3]:<10.2f} {item[4]:<15} {expiry:<12}")

    def delete_item(self):
        print("\n--- Delete Stock Item ---")
        item_id = input("Enter item ID to delete: ").strip()
        if self.db.get_stock(item_id=item_id):
            self.db.delete_stock(item_id)
            print("Item deleted.")
            self.log(f"Deleted item {item_id}")
        else:
            print("Item not found.")

    def low_stock_report(self):
        print("\n--- Low Stock Report ---")
        try:
            threshold = int(input("Enter low stock threshold (default 5): ") or "5")
        except ValueError:
            threshold = 5
        low_stock_items = self.db.get_low_stock(threshold)
        if not low_stock_items:
            print("No low stock items.")
            return
        print(f"{'ID':<10} {'Name':<20} {'Qty':<6} {'Location':<15}")
        print("-" * 55)
        for item in low_stock_items:
            print(f"{item[0]:<10} {item[1]:<20} {item[2]:<6} {item[4]:<15}")

    def total_inventory_value(self):
        print("\n--- Total Inventory Value ---")
        total_value = self.db.total_inventory_value()
        print(f"Total inventory value: ${total_value:.2f}")

    def export_to_csv(self, filename="stock_report.csv"):
        stock_items = self.db.get_stock()
        if not stock_items:
            print("No stock data to export.")
            return
        try:
            with open(filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Item ID", "Name", "Quantity", "Price", "Location", "Expiry Date"])
                for item in stock_items:
                    writer.writerow(item)
            print(f"Stock data exported successfully to {filename}")
            self.log(f"Exported stock data to CSV {filename}")
        except Exception as e:
            print(f"Failed to export CSV: {e}")

    # Supplier management
    def add_supplier(self):
        print("\n--- Add Supplier ---")
        name = input("Enter supplier name: ").strip()
        if not name:
            print("Supplier name cannot be empty.")
            return
        contact = input("Enter contact info (optional): ").strip()
        self.db.add_supplier(name, contact)
        print(f"Supplier '{name}' added.")
        self.log(f"Added supplier {name}")

    def view_suppliers(self):
        print("\n--- Suppliers List ---")
        suppliers = self.db.get_suppliers()
        if not suppliers:
            print("No suppliers found.")
            return
        print(f"{'ID':<5} {'Name':<25} {'Contact':<30}")
        print("-" * 60)
        for sup in suppliers:
            print(f"{sup[0]:<5} {sup[1]:<25} {sup[2]:<30}")

    def delete_supplier(self):
        print("\n--- Delete Supplier ---")
        try:
            supplier_id = int(input("Enter supplier ID to delete: "))
        except ValueError:
            print("Invalid supplier ID.")
            return
        self.db.delete_supplier(supplier_id)
        print("Supplier deleted.")
        self.log(f"Deleted supplier ID {supplier_id}")

    # Purchase order management
    def create_purchase_order(self):
        print("\n--- Create Purchase Order ---")
        item_id = input("Enter item ID to order: ").strip()
        stock_item = self.db.get_stock(item_id=item_id)
        if not stock_item:
            print("Item not found.")
            return
        self.view_suppliers()
        try:
            supplier_id = int(input("Enter supplier ID: "))
        except ValueError:
            print("Invalid supplier ID.")
            return
        try:
            quantity = int(input("Enter order quantity: "))
        except ValueError:
            print("Invalid quantity.")
            return
        self.db.add_purchase_order(item_id, supplier_id, quantity)
        print("Purchase order created.")
        self.log(f"Created purchase order for item {item_id}, supplier {supplier_id}, quantity {quantity}")

    def view_purchase_orders(self):
        print("\n--- Purchase Orders ---")
        orders = self.db.get_purchase_orders()
        if not orders:
            print("No purchase orders found.")
            return
        print(f"{'Order ID':<8} {'Item ID':<10} {'Supplier ID':<12} {'Qty':<6} {'Order Date':<20} {'Status':<10}")
        print("-" * 70)
        for order in orders:
            print(f"{order[0]:<8} {order[1]:<10} {order[2]:<12} {order[3]:<6} {order[4]:<20} {order[5]:<10}")

    def receive_purchase_order(self):
        print("\n--- Receive Purchase Order ---")
        try:
            order_id = int(input("Enter purchase order ID to mark as received: "))
        except ValueError:
            print("Invalid order ID.")
            return
        orders = self.db.get_purchase_orders(status='pending')
        if not any(o[0] == order_id for o in orders):
            print("Purchase order not found or already received.")
            return
        self.db.update_purchase_order_status(order_id, 'received')
        # Update stock quantity
        c = self.db.conn.cursor()
        c.execute("SELECT item_id, quantity FROM purchase_orders WHERE order_id=?", (order_id,))
        item_id, qty = c.fetchone()
        stock_item = self.db.get_stock(item_id=item_id)
        if stock_item:
            new_qty = stock_item[2] + qty
            self.db.update_stock_quantity(item_id, new_qty)
        print("Purchase order marked as received and stock updated.")
        self.log(f"Received purchase order {order_id}")

    # Barcode scanning simulation
    def barcode_scan(self):
        print("\n--- Barcode Scan (Simulated) ---")
        barcode = input("Enter barcode (item ID): ").strip()
        stock_item = self.db.get_stock(item_id=barcode)
        if not stock_item:
            print("Item not found.")
            return
        print(f"Scanned Item: {stock_item[1]}, Quantity: {stock_item[2]}, Price: {stock_item[3]}")
        try:
            change = int(input("Enter quantity change (+ for add, - for remove): "))
        except ValueError:
            print("Invalid quantity change.")
            return
        new_qty = stock_item[2] + change
        if new_qty < 0:
            print("Quantity cannot be negative.")
            return
        self.db.update_stock_quantity(barcode, new_qty)
        print(f"Updated quantity to {new_qty}.")
        self.log(f"Barcode scan updated item {barcode} quantity by {change}")

    # Dashboard summary
    def dashboard(self):
        print("\n--- Dashboard Summary ---")
        total_items = len(self.db.get_stock())
        low_stock = len(self.db.get_low_stock())
        total_value = self.db.total_inventory_value()
        pending_orders = len(self.db.get_purchase_orders(status='pending'))
        print(f"Total unique items: {total_items}")
        print(f"Low stock items: {low_stock}")
        print(f"Total inventory value: ${total_value:.2f}")
        print(f"Pending purchase orders: {pending_orders}")

    # CLI menu with role-based access
    def menu(self):
        while True:
            print("\n--- Stock Maintenance System ---")
            print("1. Add item" if self.role == 'admin' else "1. View stock")
            print("2. Update quantity" if self.role == 'admin' else "2. Search item")
            if self.role == 'admin':
                print("3. Search item")
                print("4. View stock")
                print("5. Delete item")
                print("6. Low stock report")
                print("7. Total inventory value")
                print("8. Export stock report to CSV")
                print("9. Supplier management")
                print("10. Purchase order management")
                print("11. Barcode scan (simulate)")
                print("12. Dashboard summary")
                print("13. Exit")
            else:
                print("3. Exit")

            choice = input("Enter your choice: ").strip()
            if self.role == 'admin':
                if choice == '1':
                    self.add_item()
                elif choice == '2':
                    self.update_quantity()
                elif choice == '3':
                    self.search_item()
                elif choice == '4':
                    self.view_stock()
                elif choice == '5':
                    self.delete_item()
                elif choice == '6':
                    self.low_stock_report()
                elif choice == '7':
                    self.total_inventory_value()
                elif choice == '8':
                    self.export_to_csv()
                elif choice == '9':
                    self.supplier_menu()
                elif choice == '10':
                    self.purchase_order_menu()
                elif choice == '11':
                    self.barcode_scan()
                elif choice == '12':
                    self.dashboard()
                elif choice == '13':
                    print("Exiting system. Goodbye!")
                    self.db.close()
                    break
                else:
                    print("Invalid choice. Please try again.")
            else:
                if choice == '1':
                    self.view_stock()
                elif choice == '2':
                    self.search_item()
                elif choice == '3':
                    print("Exiting system. Goodbye!")
                    self.db.close()
                    break
                else:
                    print("Invalid choice. Please try again.")

    # Supplier menu
    def supplier_menu(self):
        while True:
            print("\n--- Supplier Management ---")
            print("1. Add supplier")
            print("2. View suppliers")
            print("3. Delete supplier")
            print("4. Back to main menu")
            choice = input("Enter your choice: ").strip()
            if choice == '1':
                self.add_supplier()
            elif choice == '2':
                self.view_suppliers()
            elif choice == '3':
                self.delete_supplier()
            elif choice == '4':
                break
            else:
                print("Invalid choice.")

    # Purchase order menu
    def purchase_order_menu(self):
        while True:
            print("\n--- Purchase Order Management ---")
            print("1. Create purchase order")
            print("2. View all purchase orders")
            print("3. View pending purchase orders")
            print("4. Receive purchase order")
            print("5. Back to main menu")
            choice = input("Enter your choice: ").strip()
            if choice == '1':
                self.create_purchase_order()
            elif choice == '2':
                self.view_purchase_orders()
            elif choice == '3':
                orders = self.db.get_purchase_orders(status='pending')
                if not orders:
                    print("No pending purchase orders.")
                else:
                    print(f"{'Order ID':<8} {'Item ID':<10} {'Supplier ID':<12} {'Qty':<6} {'Order Date':<20} {'Status':<10}")
                    print("-" * 70)
                    for order in orders:
                        print(f"{order[0]:<8} {order[1]:<10} {order[2]:<12} {order[3]:<6} {order[4]:<20} {order[5]:<10}")
            elif choice == '4':
                self.receive_purchase_order()
            elif choice == '5':
                break
            else:
                print("Invalid choice.")

    # --- GUI Methods ---
    def launch_gui(self):
        self.root = tk.Tk()
        self.root.title("Stock Maintenance System")
        self.root.geometry("900x600")

        tab_control = ttk.Notebook(self.root)

        # Tabs
        self.tab_stock = ttk.Frame(tab_control)
        self.tab_suppliers = ttk.Frame(tab_control)
        self.tab_orders = ttk.Frame(tab_control)
        self.tab_dashboard = ttk.Frame(tab_control)

        tab_control.add(self.tab_stock, text="Stock")
        tab_control.add(self.tab_suppliers, text="Suppliers")
        tab_control.add(self.tab_orders, text="Purchase Orders")
        tab_control.add(self.tab_dashboard, text="Dashboard")
        tab_control.pack(expand=1, fill="both")

        self.build_stock_tab()
        self.build_suppliers_tab()
        self.build_orders_tab()
        self.build_dashboard_tab()

        self.root.mainloop()

    # Stock tab GUI
    def build_stock_tab(self):
        frame = self.tab_stock

        # Treeview for stock
        columns = ("ID", "Name", "Quantity", "Price", "Location", "Expiry Date")
        self.stock_tree = ttk.Treeview(frame, columns=columns, show='headings')
        for col in columns:
            self.stock_tree.heading(col, text=col)
            self.stock_tree.column(col, width=100)
        self.stock_tree.pack(fill=tk.BOTH, expand=True)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="Add Item", command=self.gui_add_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Update Quantity", command=self.gui_update_quantity).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Item", command=self.gui_delete_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Export CSV", command=self.export_to_csv_gui).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_stock_tree).pack(side=tk.LEFT, padx=5)

        self.refresh_stock_tree()

    def refresh_stock_tree(self):
        for i in self.stock_tree.get_children():
            self.stock_tree.delete(i)
        stock_items = self.db.get_stock()
        for item in stock_items:
            self.stock_tree.insert("", tk.END, values=item)

    def gui_add_item(self):
        popup = tk.Toplevel(self.root)
        popup.title("Add New Item")

        labels = ["Item ID", "Name", "Quantity", "Price", "Location", "Expiry Date (YYYY-MM-DD)"]
        entries = {}

        for i, label in enumerate(labels):
            ttk.Label(popup, text=label).grid(row=i, column=0, padx=5, pady=5)
            entry = ttk.Entry(popup)
            entry.grid(row=i, column=1, padx=5, pady=5)
            entries[label] = entry

        def submit():
            item_id = entries["Item ID"].get().strip()
            name = entries["Name"].get().strip()
            try:
                quantity = int(entries["Quantity"].get())
                price = float(entries["Price"].get())
            except ValueError:
                messagebox.showerror("Error", "Quantity must be integer and Price must be number.")
                return
            location = entries["Location"].get().strip()
            expiry_date = entries["Expiry Date (YYYY-MM-DD)"].get().strip()
            if expiry_date:
                try:
                    datetime.strptime(expiry_date, "%Y-%m-%d")
                except ValueError:
                    messagebox.showerror("Error", "Invalid expiry date format.")
                    return
            else:
                expiry_date = None
            if not item_id or not name or not location:
                messagebox.showerror("Error", "Item ID, Name and Location are required.")
                return
            if self.db.add_stock(item_id, name, quantity, price, location, expiry_date):
                messagebox.showinfo("Success", f"Item '{name}' added.")
                self.log(f"GUI added item {item_id}")
                self.refresh_stock_tree()
                popup.destroy()
            else:
                messagebox.showerror("Error", "Item ID already exists.")

        ttk.Button(popup, text="Add", command=submit).grid(row=len(labels), column=0, columnspan=2, pady=10)

    def gui_update_quantity(self):
        selected = self.stock_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select an item to update.")
            return
        item = self.stock_tree.item(selected[0])['values']
        item_id = item[0]

        qty = simpledialog.askinteger("Update Quantity", f"Enter new quantity for item {item_id}:")
        if qty is None:
            return
        if qty < 0:
            messagebox.showerror("Error", "Quantity cannot be negative.")
            return
        self.db.update_stock_quantity(item_id, qty)
        messagebox.showinfo("Success", "Quantity updated.")
        self.log(f"GUI updated quantity for item {item_id} to {qty}")
        self.refresh_stock_tree()

    def gui_delete_item(self):
        selected = self.stock_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select an item to delete.")
            return
        item = self.stock_tree.item(selected[0])['values']
        item_id = item[0]
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete item {item_id}?")
        if confirm:
            self.db.delete_stock(item_id)
            messagebox.showinfo("Success", "Item deleted.")
            self.log(f"GUI deleted item {item_id}")
            self.refresh_stock_tree()

    def export_to_csv_gui(self):
        self.export_to_csv()
        messagebox.showinfo("Export CSV", "Stock data exported to stock_report.csv")

    # Suppliers tab GUI
    def build_suppliers_tab(self):
        frame = self.tab_suppliers

        # Treeview for suppliers
        columns = ("ID", "Name", "Contact")
        self.supplier_tree = ttk.Treeview(frame, columns=columns, show='headings')
        for col in columns:
            self.supplier_tree.heading(col, text=col)
            self.supplier_tree.column(col, width=150)
        self.supplier_tree.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="Add Supplier", command=self.gui_add_supplier).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Supplier", command=self.gui_delete_supplier).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_supplier_tree).pack(side=tk.LEFT, padx=5)

        self.refresh_supplier_tree()

    def refresh_supplier_tree(self):
        for i in self.supplier_tree.get_children():
            self.supplier_tree.delete(i)
        suppliers = self.db.get_suppliers()
        for sup in suppliers:
            self.supplier_tree.insert("", tk.END, values=sup)

    def gui_add_supplier(self):
        popup = tk.Toplevel(self.root)
        popup.title("Add Supplier")

        ttk.Label(popup, text="Name").grid(row=0, column=0, padx=5, pady=5)
        name_entry = ttk.Entry(popup)
        name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(popup, text="Contact").grid(row=1, column=0, padx=5, pady=5)
        contact_entry = ttk.Entry(popup)
        contact_entry.grid(row=1, column=1, padx=5, pady=5)

        def submit():
            name = name_entry.get().strip()
            contact = contact_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Supplier name required.")
                return
            self.db.add_supplier(name, contact)
            messagebox.showinfo("Success", f"Supplier '{name}' added.")
            self.log(f"GUI added supplier {name}")
            self.refresh_supplier_tree()
            popup.destroy()

        ttk.Button(popup, text="Add", command=submit).grid(row=2, column=0, columnspan=2, pady=10)

    def gui_delete_supplier(self):
        selected = self.supplier_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a supplier to delete.")
            return
        sup = self.supplier_tree.item(selected[0])['values']
        sup_id = sup[0]
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete supplier {sup[1]}?")
        if confirm:
            self.db.delete_supplier(sup_id)
            messagebox.showinfo("Success", "Supplier deleted.")
            self.log(f"GUI deleted supplier {sup_id}")
            self.refresh_supplier_tree()

    # Purchase orders tab GUI
    def build_orders_tab(self):
        frame = self.tab_orders

        columns = ("Order ID", "Item ID", "Supplier ID", "Quantity", "Order Date", "Status")
        self.orders_tree = ttk.Treeview(frame, columns=columns, show='headings')
        for col in columns:
            self.orders_tree.heading(col, text=col)
            self.orders_tree.column(col, width=100)
        self.orders_tree.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="Create Order", command=self.gui_create_order).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Receive Order", command=self.gui_receive_order).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_orders_tree).pack(side=tk.LEFT, padx=5)

        self.refresh_orders_tree()

    def refresh_orders_tree(self):
        for i in self.orders_tree.get_children():
            self.orders_tree.delete(i)
        orders = self.db.get_purchase_orders()
        for order in orders:
            self.orders_tree.insert("", tk.END, values=order)

    def gui_create_order(self):
        popup = tk.Toplevel(self.root)
        popup.title("Create Purchase Order")

        ttk.Label(popup, text="Item ID").grid(row=0, column=0, padx=5, pady=5)
        item_entry = ttk.Entry(popup)
        item_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(popup, text="Supplier ID").grid(row=1, column=0, padx=5, pady=5)
        supplier_entry = ttk.Entry(popup)
        supplier_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(popup, text="Quantity").grid(row=2, column=0, padx=5, pady=5)
        qty_entry = ttk.Entry(popup)
        qty_entry.grid(row=2, column=1, padx=5, pady=5)

        def submit():
            item_id = item_entry.get().strip()
            supplier_id = supplier_entry.get().strip()
            qty = qty_entry.get().strip()
            if not item_id or not supplier_id or not qty:
                messagebox.showerror("Error", "All fields are required.")
                return
            try:
                supplier_id = int(supplier_id)
                qty = int(qty)
            except ValueError:
                messagebox.showerror("Error", "Supplier ID and Quantity must be integers.")
                return
            if not self.db.get_stock(item_id=item_id):
                messagebox.showerror("Error", "Item ID does not exist.")
                return
            suppliers = [s[0] for s in self.db.get_suppliers()]
            if supplier_id not in suppliers:
                messagebox.showerror("Error", "Supplier ID does not exist.")
                return
            self.db.add_purchase_order(item_id, supplier_id, qty)
            messagebox.showinfo("Success", "Purchase order created.")
            self.log(f"GUI created purchase order for item {item_id}")
            self.refresh_orders_tree()
            popup.destroy()

        ttk.Button(popup, text="Create", command=submit).grid(row=3, column=0, columnspan=2, pady=10)

    def gui_receive_order(self):
        selected = self.orders_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select an order to receive.")
            return
        order = self.orders_tree.item(selected[0])['values']
        order_id, item_id, supplier_id, qty, order_date, status = order
        if status == 'received':
            messagebox.showinfo("Info", "Order already received.")
            return
        confirm = messagebox.askyesno("Confirm Receive", f"Mark order {order_id} as received?")
        if confirm:
            self.db.update_purchase_order_status(order_id, 'received')
            stock_item = self.db.get_stock(item_id=item_id)
            if stock_item:
                new_qty = stock_item[2] + qty
                self.db.update_stock_quantity(item_id, new_qty)
            messagebox.showinfo("Success", "Order received and stock updated.")
            self.log(f"GUI received purchase order {order_id}")
            self.refresh_orders_tree()
            self.refresh_stock_tree()

    # Dashboard tab GUI
    def build_dashboard_tab(self):
        frame = self.tab_dashboard

        self.dashboard_text = tk.Text(frame, height=20, width=80, state=tk.DISABLED)
        self.dashboard_text.pack(padx=10, pady=10)

        ttk.Button(frame, text="Refresh Dashboard", command=self.refresh_dashboard).pack(pady=5)
        self.refresh_dashboard()

    def refresh_dashboard(self):
        total_items = len(self.db.get_stock())
        low_stock = len(self.db.get_low_stock())
        total_value = self.db.total_inventory_value()
        pending_orders = len(self.db.get_purchase_orders(status='pending'))

        text = (
            f"Dashboard Summary\n"
            f"-----------------\n"
            f"Total unique items: {total_items}\n"
            f"Low stock items: {low_stock}\n"
            f"Total inventory value: ${total_value:.2f}\n"
            f"Pending purchase orders: {pending_orders}\n"
        )

        self.dashboard_text.config(state=tk.NORMAL)
        self.dashboard_text.delete(1.0, tk.END)
        self.dashboard_text.insert(tk.END, text)
        self.dashboard_text.config(state=tk.DISABLED)

# --- Login System ---
def login_system():
    db = Database()
    print("Welcome to Stock Maintenance System")
    print("Please login to continue.")
    for attempt in range(3):
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        role = db.verify_user(username, password)
        if role:
            print(f"Login successful! Role: {role}")
            db.close()
            return username, role
        else:
            print(f"Invalid credentials. {2 - attempt} attempts left.")
    print("Too many failed attempts. Exiting.")
    db.close()
    return None, None

def initialize_default_admin():
    db = Database()
    c = db.conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    if count == 0:
        print("No users found. Creating default admin user.")
        while True:
            username = input("Enter admin username (default: admin): ").strip() or "admin"
            password = input("Enter admin password (default: admin123): ").strip() or "admin123"
            if db.add_user(username, password, 'admin'):
                print(f"Admin user '{username}' created.")
                break
            else:
                print("Failed to create admin user. Try again.")
    db.close()

# --- Main ---
if __name__ == "__main__":
    initialize_default_admin()
    username, role = login_system()
    if username:
        system = StockMaintenanceSystem(username, role)
        mode = input("Enter 'gui' to launch GUI or press Enter for CLI: ").strip().lower()
        if mode == 'gui':
            system.launch_gui()
        else:
            system.menu()
