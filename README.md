# Wedding Decoration Rental System

This is a web application for renting wedding decorations, built using Python (Flask), SQLAlchemy, and Flask-Migrate (Alembic) with an SQLite database.

## Prerequisites

Ensure you have the following installed on your system:

- **Python 3.8 or higher**
- **pip** (Python package installer)

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

Install the required Python packages. If a `requirements.txt` is not present, you can install the core packages manually:

```bash
pip install Flask Flask-SQLAlchemy Flask-Migrate Flask-Login Flask-WTF email-validator
```

---

## Database Configuration

By default, the application uses **SQLite** (a local `app.db` file) for simplicity. If you want to use an external database like **MySQL/MariaDB** or **PostgreSQL**, you can configure it using the **`DATABASE_URL`** environment variable (Option A).

### For MySQL / MariaDB

1. Install the MySQL driver package:
   ```bash
   pip install pymysql
   ```
2. Set the `DATABASE_URL` environment variable:
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

## Database Migration & Seeding

The database structure has been updated according to the latest ERD design. To initialize the SQLite database (`app.db`) and seed the initial data:

### 1. Run Migrations

Generate the database schema by upgrading to the latest migration script:

```bash
flask db upgrade
```

### 2. Seed Initial Data

Populate the database with a default administrator account and sample product packages:

```bash
# Seed default Administrator
python seed_admin.py

# Seed default Products/Packages
python seed_products.py
```

---

## Running the Application

Start the local development server:

```bash
python run.py
```

By default, the application will run at:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## Default Credentials

You can log in to the administrator dashboard using the following credentials:

- **Email:** `admin@example.com`
- **Password:** `admin123`
