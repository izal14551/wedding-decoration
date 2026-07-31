# Production Deployment Guide

### **Griya Rias Saraswati - Wedding Decoration & Bridal Makeup Rental System**

This guide provides step-by-step instructions for deploying the **Griya Rias Saraswati** web application to a production environment running **Linux (Ubuntu/Debian)** using **Nginx** as a reverse proxy, **Gunicorn** as the WSGI application server, **Systemd** for process supervision, and **MySQL/MariaDB** as the database engine.

---

## 🏗️ Production Architecture

```
[ Client / Browser ]
       │ (HTTPS / Port 443)
       ▼
[ Nginx Web Server ] ──(Static Files & Uploads)──► [/app/static & /uploads]
       │ (Proxy Pass / HTTP Port 8000)
       ▼
[ WSGI Server: Gunicorn ] (Multi-Worker Processes)
       │
       ▼
[ Flask Web Application ]
       │ (SQLAlchemy ORM)
       ▼
[ MySQL / MariaDB Server ]
```

---

## 📋 Server Requirements & Prerequisites

### 1. Minimum Server Specifications

- **Operating System**: Ubuntu 22.04 LTS / 24.04 LTS or Debian 11/12
- **CPU**: Minimum 1 vCPU (2 vCPUs recommended)
- **RAM**: Minimum 1 GB (2 GB+ recommended)
- **Storage**: Minimum 20 GB SSD
- **Access Rights**: Linux user with `sudo` privileges

### 2. Domain Name & DNS Setup

- A Domain or Subdomain with its **A Record** pointed to your server's Public IP address (e.g., `griyariassaraswati.com`).

---

## 🛠️ Step 1: System Package Update & Server Preparation

Connect to your production server via SSH and update system packages:

```bash
sudo apt update && sudo apt upgrade -y
```

Install Python, MySQL client development tools, Nginx, Git, and build tools:

```bash
sudo apt install -y python3 python3-venv python3-dev build-essential \
                    libmysqlclient-dev pkg-config nginx git curl \
                    mariadb-server mariadb-client
```

---

## 🗄️ Step 2: Database Configuration (MySQL / MariaDB)

### 1. Secure MySQL Installation

Run the security script to secure your database server:

```bash
sudo mysql_secure_installation
```

_(Follow the prompt instructions: set root password, remove anonymous users, disallow root remote login, and drop test database)._

### 2. Create Production Database & User

Log into the MySQL shell:

```bash
sudo mysql -u root -p
```

Execute the following SQL commands (replace `StrongProductionPassword123!` with a secure password):

```sql
CREATE DATABASE wedding_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'wedding_user'@'localhost' IDENTIFIED BY 'StrongProductionPassword123!';
GRANT ALL PRIVILEGES ON wedding_db.* TO 'wedding_user'@'localhost';

FLUSH PRIVILEGES;
EXIT;
```

---

## 📂 Step 3: Source Code & Virtual Environment Setup

### 1. Clone the Application Repository

Clone the codebase into `/var/www/wedding-decoration`:

```bash
cd /var/www
sudo git clone https://github.com/username/wedding-decoration.git wedding-decoration
sudo chown -R $USER:$USER /var/www/wedding-decoration
cd /var/www/wedding-decoration
```

### 2. Create & Activate Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies & Gunicorn

Upgrade `pip` and install all required libraries along with Gunicorn and PyMySQL:

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn pymysql
```

---

## 🔐 Step 4: Production Environment Variables (`.env`)

Create a `.env` file in the project root directory (`/var/www/wedding-decoration/.env`):

```bash
nano /var/www/wedding-decoration/.env
```

Add the following environment configuration:

```env
# Production Environment Configuration
FLASK_ENV=production
FLASK_APP=run.py
SECRET_KEY=9b8f2e7a1c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f

# Production Database Connection URL
DATABASE_URL=mysql+pymysql://wedding_user:StrongProductionPassword123!@localhost:3306/wedding_db

# Media Uploads Path
UPLOAD_FOLDER=/var/www/wedding-decoration/uploads
```

_Tip: Generate a strong random `SECRET_KEY` by running `python3 -c "import secrets; print(secrets.token_hex(32))"` in your terminal._

---

## 🌱 Step 5: Directory Structure & Initial Database Seeding

### 1. Create Media Upload Directories

```bash
mkdir -p /var/www/wedding-decoration/uploads/payments
mkdir -p /var/www/wedding-decoration/uploads/decorations
mkdir -p /var/www/wedding-decoration/uploads/settings
```

### 2. Initialize Database & Seed Demo Data

Initialize database schema and populate initial administrator account and catalog items:

```bash
# Seed complete database & sample dashboard data
python seed_dashboard.py

# Alternatively, to seed only the Administrator account:
# python seed_admin.py
```

---

## ⚙️ Step 6: Gunicorn & Systemd Service Configuration

Configure a Systemd service to manage the Gunicorn application process in the background and ensure automatic restart on system reboots.

### 1. Test Gunicorn Manually (Optional)

```bash
gunicorn --bind 127.0.0.1:8000 "app:create_app()"
```

Press `Ctrl+C` after verifying that the application starts without errors.

### 2. Create Systemd Service File

```bash
sudo nano /etc/systemd/system/wedding.service
```

Add the following configuration:

```ini
[Unit]
Description=Gunicorn instance serving Wedding Decoration Application
After=network.target mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/wedding-decoration
Environment="PATH=/var/www/wedding-decoration/venv/bin"
EnvironmentFile=/var/www/wedding-decoration/.env
ExecStart=/var/www/wedding-decoration/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 --access-logfile /var/log/wedding_access.log --error-logfile /var/log/wedding_error.log "app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

### 3. Adjust File Permissions for `www-data`

```bash
sudo chown -R www-data:www-data /var/www/wedding-decoration
sudo chmod -R 775 /var/www/wedding-decoration/uploads
```

### 4. Enable & Start Systemd Service

```bash
sudo systemctl daemon-reload
sudo systemctl start wedding
sudo systemctl enable wedding
```

Verify that the service is **active (running)**:

```bash
sudo systemctl status wedding
```

---

## 🌐 Step 7: Nginx Web Server Setup (Reverse Proxy & Static Asset Serving)

### 1. Create Nginx Site Configuration

```bash
sudo nano /etc/nginx/sites-available/wedding-decoration
```

Add the following Nginx server block (replace `yourdomain.com` with your domain name):

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 16M;

    # Serve Static Assets Directly (CSS, JS, Fonts)
    location /static/ {
        alias /var/www/wedding-decoration/app/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Serve User Uploaded Media Files (Payment Proofs, Product Images)
    location /uploads/ {
        alias /var/www/wedding-decoration/uploads/;
        expires 7d;
        add_header Cache-Control "public, no-transform";
    }

    # Pass All Other Requests to Gunicorn WSGI Server
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

### 2. Enable Configuration & Restart Nginx

```bash
# Enable the site configuration link
sudo ln -s /etc/nginx/sites-available/wedding-decoration /etc/nginx/sites-enabled/

# Remove default site configuration if present
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx syntax configuration
sudo nginx -t

# Reload Nginx service
sudo systemctl restart nginx
```

---

## 🔒 Step 8: SSL/TLS HTTPS Certificate Setup (Let's Encrypt)

Secure your application with free HTTPS SSL certificates using **Certbot**:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

_Certbot will automatically configure HTTP to HTTPS redirects and maintain SSL certificate renewals via cron._

---

## 🔄 How to Update Production (Maintenance & Redeployment Guide)

Follow these instructions whenever you need to deploy new features, bug fixes, or code updates to the live production server.

### 1. Standard Production Update Checklist

Execute the following commands on your production server:

```bash
# Navigate to application root
cd /var/www/wedding-decoration

# 1. Fetch & pull latest commits from the main branch
sudo git pull origin main

# 2. Activate virtual environment
source venv/bin/activate

# 3. Update Python packages if requirements.txt was modified
pip install -r requirements.txt

# 4. Apply any pending database schema migrations
flask db upgrade

# 5. Fix & verify file permissions for www-data user
sudo chown -R www-data:www-data /var/www/wedding-decoration
sudo chmod -R 775 /var/www/wedding-decoration/uploads

# 6. Gracefully reload or restart the Gunicorn service
sudo systemctl reload wedding || sudo systemctl restart wedding

# 7. Check service status to confirm clean startup
sudo systemctl status wedding
```

---

### 2. Zero-Downtime Graceful Reload

Gunicorn supports graceful process reloads without dropping active HTTP connections. To reload worker processes gracefully without interrupting active customer sessions:

```bash
# Option A: Systemd reload signal (Sends HUP to Gunicorn master process)
sudo systemctl reload wedding

# Option B: Direct HUP signal via Process ID
sudo kill -HUP $(pgrep -f "gunicorn.*wedding")
```

---

### 3. One-Click Automated Update Script (`deploy.sh`)

You can create an automated deployment helper script on your server to execute updates in a single command:

1. Create a script named `deploy.sh` in `/var/www/wedding-decoration/deploy.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Starting Production Update Procedure..."

cd /var/www/wedding-decoration

echo "📥 Pulling latest code from Git..."
git pull origin main

echo "🐍 Activating Virtual Environment & updating dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet

echo "🗄️ Executing Database Migrations..."
flask db upgrade

echo "🔒 Setting file ownership and permissions..."
sudo chown -R www-data:www-data /var/www/wedding-decoration
sudo chmod -R 775 /var/www/wedding-decoration/uploads

echo "🔄 Reloading Gunicorn application service..."
sudo systemctl reload wedding

echo "✅ Production Update Successfully Completed!"
```

2. Grant execute permissions to the script:

```bash
chmod +x /var/www/wedding-decoration/deploy.sh
```

3. Run the automated deployment anytime:

```bash
./deploy.sh
```

---

### 4. Emergency Rollback Procedure

If an update introduces unexpected errors or breaks functionality in production, execute an emergency rollback immediately:

```bash
cd /var/www/wedding-decoration

# 1. Rollback code to the previous Git commit
sudo git reset --hard HEAD~1

# 2. Rollback the database migration (if schema was altered)
source venv/bin/activate
flask db downgrade

# 3. Restore ownership & permissions
sudo chown -R www-data:www-data /var/www/wedding-decoration

# 4. Restart application service
sudo systemctl restart wedding

# 5. Verify system recovery from logs
sudo journalctl -u wedding.service -n 50 --no-pager
```

---

## 📊 Logging & Troubleshooting

- **Check Application Runtime Logs (Systemd)**:
  ```bash
  sudo journalctl -u wedding.service -f
  ```
- **Check Gunicorn Error Logs**:
  ```bash
  sudo tail -f /var/log/wedding_error.log
  ```
- **Check Nginx Access & Error Logs**:
  ```bash
  sudo tail -f /var/log/nginx/error.log
  ```

---

## 🔑 Default Initial Credentials

After running `python seed_dashboard.py`, you can log into the Administrator Dashboard:

- **Login URL**: `https://yourdomain.com/admin/login`
- **Email**: `admin@example.com`
- **Password**: `admin123`

⚠️ **IMPORTANT**: _Change the default Administrator password immediately after your first login in a production environment!_

---

## 📄 License & Copyright

© 2026 **Griya Rias Saraswati**. All Rights Reserved.
