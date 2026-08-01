# Wedding Decoration & Bridal Makeup Rental System

### **Griya Rias Saraswati - Web-Based Rental & Management System**

A web application designed for renting wedding decorations and booking bridal makeup/services online. It streamlines customer reservations, prevents double bookings, automates availability scheduling, and provides administrators with comprehensive dashboard analytics, payment verification, and transaction reports.

---

## 📌 Key System Features

### 👤 Customer Module

- **Interactive Catalog & Product Details**: View decoration packages and makeup services with full portfolio images, package details (_includes_), item availability, and interactive availability calendars.
- **Cart & Date-Based Checkout**: Add items to cart and check out by selecting event dates (`start_date` to `end_date`), event location, and custom notes.
- **Double Booking Prevention**: Automatic date availability checking against physical item stock and daily makeup/service slot capacities.
- **Payment Proof Upload**: Upload bank transfer payment proofs with automatic WebP image compression.
- **Official Invoice & PDF/Print**: Automatically generated invoices with official print and PDF download capabilities.

### 🛡️ Administrator Module

- **Interactive Analytics Dashboard**: Visual revenue trends (Line Chart) and order status distribution (Doughnut Chart) powered by Chart.js.
- **Product & Category Management**: Full CRUD operations for decorations, makeup services, categories, stock/slots, and package items.
- **Availability Schedule Management**: Real-time management of rental schedules (Rented, Maintenance, Available).
- **Order & Payment Verification**: Verify customer payment proofs and manage order states (Waiting for Payment, Processing, Completed, Cancelled).
- **Site Settings**: Customize business details (Name, Tagline, Address, Phone) and upload dynamic catalog hero background images.
- **Automated Transaction Reports**: Filter transactions (Daily, Weekly, Monthly, Yearly) and export reports to PDF or Excel.
- **Administrator Transaction Restriction**: Safety controls preventing admin accounts from placing rental orders on storefront pages.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.8+, Flask, Flask-SQLAlchemy, Flask-Login, Flask-Migrate (Alembic)
- **Frontend**: HTML5, Custom CSS, Bootstrap 5, JavaScript (Vanilla JS), Chart.js
- **Database**: MySQL / MariaDB (SQLAlchemy ORM)
- **WSGI / Web Server**: Gunicorn, Nginx
- **Helper Libraries**: Pillow (WebP image processing), Pandas / OpenPyXL (Excel export), xhtml2pdf (PDF invoice export), bcrypt (Security)

---

## 💻 Part 1: Local Development Setup

Follow these steps to run the application locally on your machine (Windows / Laragon / XAMPP / macOS / Linux):

### 1. Clone & Set Up Project Directory

```bash
git clone https://github.com/username/wedding-decoration.git
cd wedding-decoration
```

### 2. Create & Activate Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Activate on Windows (CMD):
venv\Scripts\activate.bat

# Activate on Linux / macOS:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Local Database

By default, the application connects to MySQL via `mysql+pymysql://root:@localhost/wedding_db`.

Create the database in your local MySQL instance (Laragon / XAMPP):

```sql
CREATE DATABASE IF NOT EXISTS wedding_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Seed Initial Data & Run Server

```bash
# Initialize database tables and populate sample data
python seed_dashboard.py

# Start local development server
python run.py
```

Access the application in your browser at: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🚀 Part 2: Production Deployment Guide (Linux VPS)

Follow these step-by-step instructions for deploying to a production VPS (Ubuntu/Debian) under your user home directory (`/home/$USER/wedding-decoration`).

### Step 1: Server Package Installation

Connect to your VPS via SSH and install required system packages:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-dev build-essential \
                    libmysqlclient-dev pkg-config nginx git curl \
                    mariadb-server mariadb-client
```

---

### Step 2: Database Setup via Direct Terminal Shell

Execute database and user creation directly from your terminal:

```bash
# Create database, user, and grant privileges
sudo mysql -e "CREATE DATABASE IF NOT EXISTS wedding_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS 'wedding_user'@'localhost' IDENTIFIED BY 'StrongPassword123!'; GRANT ALL PRIVILEGES ON wedding_db.* TO 'wedding_user'@'localhost'; FLUSH PRIVILEGES;"
```

Export `DATABASE_URL` directly in your terminal session:

```bash
export DATABASE_URL="mysql+pymysql://wedding_user:StrongPassword123!@localhost:3306/wedding_db"
```

---

### Step 3: Clone Codebase & Setup Production Environment

```bash
# Clone to your user home directory
cd $HOME
git clone https://github.com/username/wedding-decoration.git wedding-decoration
cd $HOME/wedding-decoration

# Setup Virtual Environment
python3 -m venv venv
source venv/bin/activate

# Install production dependencies
pip install --upgrade pip
pip install -r requirements.txt gunicorn pymysql

# Create required upload directories under app/static/uploads
mkdir -p app/static/uploads/payments app/static/uploads/decorations app/static/uploads/settings

# Initialize database schema and initial data
python seed_dashboard.py
```

---

### Step 4: Systemd Service Configuration

Create a Systemd service configuration for Gunicorn:

```bash
sudo nano /etc/systemd/system/wedding.service
```

Paste the following configuration (replace `meliana` with your actual Linux username if different):

```ini
[Unit]
Description=Gunicorn instance serving Wedding Decoration Application
After=network.target mysql.service

[Service]
User=meliana
Group=meliana
WorkingDirectory=/home/meliana/wedding-decoration
Environment="PATH=/home/meliana/wedding-decoration/venv/bin"
Environment="DATABASE_URL=mysql+pymysql://wedding_user:StrongPassword123!@localhost:3306/wedding_db"
EnvironmentFile=-/home/meliana/wedding-decoration/.env
ExecStart=/home/meliana/wedding-decoration/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 "app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
# Reload systemd manager configuration
sudo systemctl daemon-reload

# Start and enable service on boot
sudo systemctl start wedding
sudo systemctl enable wedding

# Check service status
sudo systemctl status wedding
```

---

### Step 5: Nginx Web Server Configuration (Reverse Proxy)

Create an Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/wedding-decoration
```

Paste the Nginx server block (replace `griyariassaraswati.com` with your domain and `116.193.191.159` with your VPS IP):

```nginx
server {
    listen 80;
    # Separate multiple domains/IPs with spaces
    server_name griyariassaraswati.com www.griyariassaraswati.com [IP_ADDRESS];

    client_max_body_size 16M;

    # Serve static assets directly
    location /static/ {
        alias /home/meliana/wedding-decoration/app/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Serve media upload files directly
    location /uploads/ {
        alias /home/meliana/wedding-decoration/app/static/uploads/;
        expires 7d;
        add_header Cache-Control "public, no-transform";
    }

    # Proxy all application requests to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

Enable configuration and restart Nginx:

```bash
# Enable site configuration
sudo ln -s /etc/nginx/sites-available/wedding-decoration /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration syntax & restart Nginx
sudo nginx -t
sudo systemctl restart nginx
```

---

### Step 6: SSL/TLS Certificate Setup (HTTPS)

Install Certbot to enable free HTTPS encryption:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## 🔄 Part 3: How to Update Production (Maintenance & Redeployment)

Follow these instructions whenever deploying code updates to the live server.

### 1. Standard Production Update Checklist

```bash
cd $HOME/wedding-decoration

# 1. Pull latest code from main branch
git pull origin main

# 2. Activate virtual environment
source venv/bin/activate

# 3. Update dependencies if requirements.txt was modified
pip install -r requirements.txt

# 4. Apply database schema migrations
flask db upgrade

# 5. Reload application service gracefully (zero-downtime)
sudo systemctl reload wedding

# 6. Check status
sudo systemctl status wedding
```

---

### 2. Zero-Downtime Graceful Reload

Gunicorn reloads worker processes without dropping active HTTP requests:

```bash
sudo systemctl reload wedding
```

---

### 3. One-Click Automated Update Script (`deploy.sh`)

Create an automated update script in `$HOME/wedding-decoration/deploy.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Starting Production Update..."
cd $HOME/wedding-decoration

echo "📥 Pulling latest code..."
git pull origin main

echo "🐍 Updating virtual environment dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet

echo "🗄️ Running Database Migrations..."
flask db upgrade

echo "🔄 Reloading Application Service..."
sudo systemctl reload wedding

echo "✅ Production Update Complete!"
```

Grant execution permissions:

```bash
chmod +x $HOME/wedding-decoration/deploy.sh
```

Execute anytime:

```bash
./deploy.sh
```

---

### 4. Emergency Rollback Procedure

If a deployed update breaks functionality:

```bash
cd $HOME/wedding-decoration

# 1. Rollback code to previous commit
git reset --hard HEAD~1

# 2. Rollback database migration if needed
source venv/bin/activate
flask db downgrade

# 3. Restart application service
sudo systemctl restart wedding

# 4. Inspect system logs
sudo journalctl -u wedding.service -n 50 --no-pager
```

---

## 📊 Part 4: Troubleshooting Common Errors

### 1. MySQL Error 1698: `Access denied for user 'root'@'localhost'`

Ubuntu/Debian uses `auth_socket` for `root` by default. Fix by creating a dedicated user or switching auth plugin:

```bash
# Option A: Create dedicated user (Recommended)
sudo mysql -e "CREATE DATABASE IF NOT EXISTS wedding_db; CREATE USER IF NOT EXISTS 'wedding_user'@'localhost' IDENTIFIED BY 'StrongPassword123!'; GRANT ALL PRIVILEGES ON wedding_db.* TO 'wedding_user'@'localhost'; FLUSH PRIVILEGES;"
export DATABASE_URL="mysql+pymysql://wedding_user:StrongPassword123!@localhost:3306/wedding_db"

# Option B: Change root plugin
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root123'; FLUSH PRIVILEGES;"
export DATABASE_URL="mysql+pymysql://root:root123@localhost:3306/wedding_db"
```

### 2. Systemd Service Failures (`Job for wedding.service failed`)

Check detailed log output:

```bash
sudo journalctl -xeu wedding.service -n 30 --no-pager
```

Common causes & fixes:

- **Path mismatch**: Ensure `WorkingDirectory` and `ExecStart` in `/etc/systemd/system/wedding.service` point to `/home/$USER/wedding-decoration` (matching your actual user home path).
- **Log permissions**: Omit `/var/log/wedding_access.log` flags or let Gunicorn output to standard output (`stdout`/`journald`).

---

## 🔑 Default Initial Credentials

After running `python seed_dashboard.py`:

- **Administrator**: `admin@example.com` / `admin123`
- **Customer**: `budi@example.com` / `budi123`

---

## 🧪 Running Automated Unit Tests

To run the full unit test suite (63 tests):

```bash
python -m unittest discover tests
```

---

## 📄 License & Copyright

© 2026 **Griya Rias Saraswati**. All Rights Reserved.
