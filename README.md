# 🧾 Stock Maintenance System

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![GUI](https://img.shields.io/badge/GUI-Tkinter-orange.svg)
![DB](https://img.shields.io/badge/Database-SQLite-lightgrey.svg)

A desktop application for managing stock, suppliers, and purchase orders — built with Python, Tkinter, and SQLite. Designed for small to medium businesses that need a local, lightweight solution for inventory and supplier tracking.

---

## 📸 Screenshots

> Replace the placeholder image links with your screenshots in the `/assets/` folder

| Login Page | Dashboard |
|------------|-----------|
| ![Login](assets/login.png) | ![Dashboard](assets/dashboard.png) |

| Stock List | Add New Item |
|------------|--------------|
| ![Stock List](assets/stock_list.png) | ![Add Item](assets/add_item.png) |

---

## 📚 Features at a Glance

| Feature                     | Description                                                                 |
|----------------------------|-----------------------------------------------------------------------------|
| 👥 User Login              | Secure login with hashed passwords and role-based access (`admin`, `staff`) |
| 📦 Stock Management        | Add, edit, delete, and view inventory items                                 |
| 📍 Location & Expiry Track | Monitor stock locations and expiry dates                                     |
| 🧾 Purchase Orders         | Record and track purchase orders                                            |
| 👨‍💼 Supplier Management     | Maintain supplier info with contact details                                 |
| 📤 Export Data              | CSV and JSON export support                                                 |
| 🔍 GUI Interface            | Built using Python’s built-in `tkinter` library                             |

---

## 🏗️ Project Architecture

```bash
stock_system/
│
├── stock_system.py        # Main script containing GUI and backend logic
├── stock_maintenance.db   # Created on first run (SQLite DB)
├── assets/                # Folder for screenshots and icons
└── README.md              # Project overview and instructions
```

---

## 🧑‍💻 How to Use

1. **Clone the Repository**

```bash
git clone https://github.com/VANSHAJAWASTHI/stock-maintenance-system.git
cd stock-maintenance-system
```

2. **Install Python (if not installed)**

- Download from [python.org](https://www.python.org/downloads/)

3. **Run the Application**

```bash
python stock_system.py
```

The database (`stock_maintenance.db`) will be created automatically on first run.

---

## 🔐 User Roles

| Role   | Capabilities                                 |
|--------|----------------------------------------------|
| Admin  | Full access: manage users, stock, suppliers  |
| Staff  | Limited to viewing/editing stock and orders  |

---

## 🛠 Tech Stack

| Component   | Tool / Library     |
|-------------|--------------------|
| Language    | Python 3.x         |
| GUI         | Tkinter            |
| Database    | SQLite3            |
| Security    | hashlib (SHA-256)  |
| Export      | CSV, JSON          |

---

## 🧪 To-Do / Improvements

- ✅ Expiry reminders and low stock alerts
- 📈 Dashboard with visual charts
- 📤 PDF export
- 🌐 Multi-language support
- 🧪 Unit & integration tests

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙋‍♂️ Author

Developed by **Vanshaj Awasthi**  
Feel free to [reach out](mailto:youremail@example.com) or connect via [LinkedIn](https://www.linkedin.com/).

---
