# CySec Don SQLi Training Lab

<p align="center">
  <strong>A professional, intentionally vulnerable web application for learning SQL injection detection, analysis, and defense.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.0-green.svg" alt="Flask">
  <img src="https://img.shields.io/badge/MariaDB-11.4-orange.svg" alt="MariaDB">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg" alt="Docker">
  <img src="https://img.shields.io/badge/License-Education-yellow.svg" alt="License">
</p>

> **WARNING:** This application contains INTENTIONAL security vulnerabilities for educational purposes ONLY. Use exclusively in isolated lab environments (localhost, Docker, VMs). Never deploy on public networks or systems you do not own. Unauthorized access to computer systems is illegal.

**Author:** CySec Don (cysecdon@gmail.com)

---

## Features

| Feature | Description |
|---------|-------------|
| **8 Hands-On Challenges** | Covers every SQLi type from the textbook |
| **3 Security Levels** | Low (vulnerable), Medium (partially protected), High (secure) |
| **Progress Tracking** | Score system with challenge completion badges |
| **Real-Time Monitoring** | Login attempt logs and audit trail |
| **phpMyAdmin Included** | Direct database access for query analysis |
| **Docker-First Design** | One-command deployment |
| **Build From Source** | Full source code with Python setup |
| **Companion Textbook** | 40-page professional textbook (see below) |

---

## Challenge Map

| # | Challenge | Category | Difficulty | Points |
|---|-----------|----------|------------|--------|
| 1 | Authentication Bypass | In-Band (Error-Based) | Beginner | 100 |
| 2 | Error-Based SQLi | In-Band (Error-Based) | Beginner | 150 |
| 3 | Union-Based SQLi | In-Band (Union-Based) | Intermediate | 200 |
| 4 | Boolean-Based Blind SQLi | Blind (Boolean) | Intermediate | 250 |
| 5 | Time-Based Blind SQLi | Blind (Time) | Advanced | 350 |
| 6 | Second-Order SQLi | Second-Order | Advanced | 400 |
| 7 | Full Data Extraction | In-Band (Union) | Advanced | 500 |
| 8 | Privilege Escalation | In-Band | Expert | 600 |

---

## Quick Start (Docker)

### Option A: Docker Compose (Recommended)

```bash
# 1. Clone or download the lab
cd CySec_Lab

# 2. Build and start all services (app + database + phpMyAdmin)
docker compose up -d --build

# 3. Wait for services to be healthy (~30 seconds)
docker compose ps

# 4. Access the lab
#    Lab:       http://localhost:5000
#    phpMyAdmin: http://localhost:8080
```

### Option B: Docker Run (Standalone)

```bash
# 1. Start MariaDB
docker run -d --name cysec-db \
  -e MARIADB_ROOT_PASSWORD=root_password \
  -e MARIADB_DATABASE=cysec_lab \
  -e MARIADB_USER=cysec_lab \
  -e MARIADB_PASSWORD=cysec_lab_pass \
  -v $(pwd)/db/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro \
  -p 3306:3306 \
  mariadb:11.4

# 2. Wait for MariaDB to initialize
sleep 15

# 3. Build and start the lab
docker build -t cysec-lab .
docker run -d --name cysec-app \
  --link cysec-db:db \
  -p 5000:5000 \
  cysec-lab

# 4. Access: http://localhost:5000
```

### Option C: Pull from Docker Hub

```bash
# (If published to Docker Hub)
docker compose pull
docker compose up -d
```

---

## Build from Source

### Prerequisites

- Python 3.10 or later
- MariaDB 10.6+ or MySQL 8.0+
- pip (Python package manager)
- Git (optional)

### Step-by-Step

```bash
# 1. Navigate to the lab directory
cd CySec_Lab

# 2. Run the build script
bash scripts/build.sh
#   - Checks prerequisites
#   - Creates Python virtual environment
#   - Installs dependencies
#   - Configures MariaDB
#   - Imports the database schema
#   - Creates .env file

# 3. Activate the environment and start
source venv/bin/activate
export $(cat .env | xargs)
python -m app.main

# 4. Open http://localhost:5000
```

### Manual Setup (without build script)

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up database manually
mysql -u root -p
```

```sql
CREATE DATABASE cysec_lab CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cysec_lab'@'localhost' IDENTIFIED BY 'cysec_lab_pass';
GRANT ALL PRIVILEGES ON cysec_lab.* TO 'cysec_lab'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

```bash
# 4. Import schema
mysql -u cysec_lab -p'cysec_lab_pass' cysec_lab < db/init.sql

# 5. Configure environment
export FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=cysec_lab
export DB_PASSWORD=cysec_lab_pass
export DB_NAME=cysec_lab
export SECURITY_LEVEL=low

# 6. Run
python -m app.main
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_SECRET_KEY` | (random) | Flask session encryption key |
| `DB_HOST` | `db` | Database hostname |
| `DB_PORT` | `3306` | Database port |
| `DB_USER` | `cysec_lab` | Database username |
| `DB_PASSWORD` | `cysec_lab_pass` | Database password |
| `DB_NAME` | `cysec_lab` | Database name |
| `SECURITY_LEVEL` | `low` | Security level: `low`, `medium`, or `high` |

### Security Levels

| Level | Description | What Changes |
|-------|-------------|--------------|
| **LOW** | Fully vulnerable | No sanitization, full error messages, direct concatenation |
| **MEDIUM** | Partially protected | Basic escaping, suppressed errors, some validation |
| **HIGH** | Secure | Parameterized queries, input validation, type checking |

Change level via the Dashboard UI or by setting the `SECURITY_LEVEL` environment variable.

---

## Database Schema

```
cysec_lab
├── users          (9 users, including admin/guest accounts)
├── products       (12 cybersecurity products)
├── credit_cards   (5 sample cards - masked for realism)
├── orders         (5 sample orders)
├── login_attempts (audit trail for login attempts)
└── audit_log      (trigger-based change monitoring)
```

All passwords hash to the bcrypt hash of `password` for lab convenience.

---

## Project Structure

```
CySec_Lab/
├── app/
│   ├── __init__.py
│   ├── main.py              # Flask application (all routes + logic)
│   ├── challenges/          # Challenge modules (future)
│   ├── templates/           # Jinja2 HTML templates (12 files)
│   └── static/
│       └── css/
│           └── style.css    # Dark cybersecurity theme
├── db/
│   └── init.sql             # Database schema + sample data
├── scripts/
│   └── build.sh             # Build-from-source setup script
├── Dockerfile               # Multi-stage Docker image
├── docker-compose.yml       # Full stack orchestration
├── requirements.txt         # Python dependencies
├── .gitignore
└── README.md                # This file
```

---

## Default Credentials

| Account | Username | Password | Role |
|---------|----------|----------|------|
| Administrator | `admin` | `password` | admin |
| Regular User | `alice` | `password` | user |
| Pentest Account | `pentest` | `password` | admin |
| Guest | `mallory` | `password` | guest |

---

## Companion Textbook

This lab is the hands-on companion to the professional textbook:

**"SQL and SQL Injection: Defensive Security & Ethical Testing"**
by CySec Don

The textbook covers:
- Part I-III: Complete SQL education (DDL, DML, DCL, TCL, Advanced SQL)
- Part IV-VI: SQL Injection theory, types, detection, and testing
- Part VII: Prevention and defense strategies
- Part VIII: Hands-on lab exercises (this lab!)
- Part IX-X: Real-world case studies and assessments

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Waiting for database..." | Ensure MariaDB is running: `docker compose ps` |
| Port 5000 already in use | Change port: `docker compose up -d` then edit `docker-compose.yml` ports |
| Database connection refused | Check DB_HOST matches container name (`db` for Docker, `localhost` for source) |
| Blank page / 500 error | Check logs: `docker compose logs -f app` |
| Reset database | Visit `http://localhost:5000/reset-db` or re-run `init.sql` |

---

## Legal & Ethical Notice

This software is provided **exclusively for educational and authorized security testing purposes**. By using this software, you agree to:

1. Use it ONLY in environments you own or have explicit written authorization to test
2. Never use the techniques demonstrated against production systems without authorization
3. Comply with all applicable laws and regulations in your jurisdiction
4. Not hold the author liable for any misuse of this software

Unauthorized access to computer systems is a criminal offense in most jurisdictions.

---

## License

Educational Use Only. Copyright CySec Don. All rights reserved.
