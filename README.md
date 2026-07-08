# Wedding Decoration Rental System

This is a web application for renting wedding decorations, built using Python (Flask), SQLAlchemy, and Flask-Migrate (Alembic) with a MySQL database.

## Prerequisites

Ensure you have the following installed on your system:

- **Python 3.8 or higher**
- **pip** (Python package installer)
- **MySQL/MariaDB Server** (e.g., Laragon, XAMPP, or standalone MySQL)

---

## Installation & Setup

Follow these steps to set up and run the project locally on your machine:

### 1. Clone or Open the Project

Open your terminal or command prompt and navigate to the project root directory:

```bash
cd path/to/wedding-decoration
```

### 2. Set Up Virtual Environment

It is highly recommended to use a virtual environment to manage dependencies:

```bash
# Create a virtual environment named 'venv'
python -m venv venv

# Activate the virtual environment
# On Windows (Command Prompt):
venv\Scripts\activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

Install the required Python packages (including driver for MySQL `pymysql` and encryption library `bcrypt`). Ensure your virtual environment is active before running the command:

```bash
pip install Flask Flask-SQLAlchemy Flask-Migrate Flask-Login Flask-WTF email-validator flask-security-too bcrypt pymysql
```

---

## Database Configuration

By default, the application is configured to use **MySQL/MariaDB** (specifically `mysql+pymysql://root:@localhost/wedding_db` which fits default Laragon/XAMPP setups without database password).

Before running the seed script, make sure to launch your MySQL server (Laragon) and create the database named **`wedding_db`**:

```sql
CREATE DATABASE IF NOT EXISTS wedding_db;
```

If you want to use a different database connection (like **PostgreSQL** or a MySQL server with custom credentials), you can override the default setting by configuring the **`DATABASE_URL`** environment variable:

### For MySQL / MariaDB (Custom Credentials)

1. Set the `DATABASE_URL` environment variable:
   - **Windows (PowerShell)**:
     ```powershell
     $env:DATABASE_URL="mysql+pymysql://username:password@localhost/wedding_db"
     ```
   - **Windows (CMD)**:
     ```cmd
     set DATABASE_URL=mysql+pymysql://username:password@localhost/wedding_db
     ```
   - **macOS / Linux**:
     ```bash
     export DATABASE_URL="mysql+pymysql://username:password@localhost/wedding_db"
     ```

### For PostgreSQL

1. Install the PostgreSQL driver package:
   ```bash
   pip install psycopg2-binary
   ```
2. Set the `DATABASE_URL` environment variable:
   - **Windows (PowerShell)**:
     ```powershell
     $env:DATABASE_URL="postgresql://username:password@localhost/wedding_db"
     ```
   - **macOS / Linux**:
     ```bash
     export DATABASE_URL="postgresql://username:password@localhost/wedding_db"
     ```

---

## Database Initialization & Seeding

The database structure uses a centralized `User` and `Role` model for multi-role security (Flask-Security). To initialize the database and load complete demo/sample data (including Admin, Customers, Categories, Products, and Schedules):

### 1. Reset and Seed Sample Data

Run the dashboard seed script to create all tables and populate the database with comprehensive mock transactions:

```bash
python seed_dashboard.py
```

_Note: If you are on Windows and virtual environment is not activated, you can run:_

```powershell
.\venv\Scripts\python seed_dashboard.py
```

### 2. Seed Admin Only

If you only want to create the default Administrator account on an existing database structure:

```bash
python seed_admin.py
```

---

## Running the Application

Start the local development server:

```bash
python run.py
```

_Note: If you are on Windows and virtual environment is not activated, you can run:_

```powershell
.\venv\Scripts\python run.py
```

By default, the application will run at:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## Running Automated Tests

To verify user registration, login security, input validations, and route authorization protections:

```bash
python -m unittest tests/test_auth.py
```

---

## Default Credentials

You can log in to the administrator dashboard using the following credentials:

- **Email:** `admin@example.com`
- **Password:** `admin123`

You can log in as a customer using:

- **Email:** `budi@example.com`
- **Password:** `budi123`
