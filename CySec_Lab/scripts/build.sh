#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# CySec Don SQLi Training Lab - Build from Source
# ═══════════════════════════════════════════════════════════════
# This script sets up the lab without Docker.
# Requires: Python 3.10+, MariaDB/MySQL 8+
# ═══════════════════════════════════════════════════════════════

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║     CySec Don SQLi Training Lab              ║"
echo "  ║     Build from Source                        ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# ─── Check Prerequisites ─────────────────────────────────
check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "  ${GREEN}[OK]${NC} $1 found: $(command -v "$1")"
        return 0
    else
        echo -e "  ${RED}[MISSING]${NC} $1 not found"
        return 1
    fi
}

echo -e "${BOLD}Checking prerequisites...${NC}"
check_command python3
check_command pip3
check_command mysql || check_command mariadb

# ─── Create Virtual Environment ───────────────────────────
echo ""
echo -e "${BOLD}Setting up Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate
echo -e "  ${GREEN}[OK]${NC} Virtual environment activated"

# ─── Install Dependencies ────────────────────────────────
echo ""
echo -e "${BOLD}Installing Python dependencies...${NC}"
pip install -r requirements.txt
echo -e "  ${GREEN}[OK]${NC} Dependencies installed"

# ─── Database Setup ──────────────────────────────────────
echo ""
echo -e "${BOLD}Setting up database...${NC}"

# Prompt for database credentials
read -p "  Database host [localhost]: " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "  Database port [3306]: " DB_PORT
DB_PORT=${DB_PORT:-3306}

read -p "  Database root password: " -s DB_ROOT_PASS
echo ""

read -p "  Create new database user? [Y/n]: " CREATE_USER
CREATE_USER=${CREATE_USER:-Y}

if [[ "$CREATE_USER" =~ ^[Yy]$ ]]; then
    echo -e "  Creating database and user..."
    mysql -h "$DB_HOST" -P "$DB_PORT" -u root -p"$DB_ROOT_PASS" <<EOSQL
CREATE DATABASE IF NOT EXISTS cysec_lab CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'cysec_lab'@'localhost' IDENTIFIED BY 'cysec_lab_pass';
GRANT ALL PRIVILEGES ON cysec_lab.* TO 'cysec_lab'@'localhost';
FLUSH PRIVILEGES;
EOSQL
    echo -e "  ${GREEN}[OK]${NC} Database 'cysec_lab' and user 'cysec_lab' created"
fi

# Import schema
echo -e "  Importing schema..."
mysql -h "$DB_HOST" -P "$DB_PORT" -u cysec_lab -p'cysec_lab_pass' cysec_lab < db/init.sql
echo -e "  ${GREEN}[OK]${NC} Schema imported"

# ─── Create .env file ────────────────────────────────────
echo ""
echo -e "${BOLD}Creating environment configuration...${NC}"
cat > .env <<EOF
FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_USER=cysec_lab
DB_PASSWORD=cysec_lab_pass
DB_NAME=cysec_lab
SECURITY_LEVEL=low
EOF
echo -e "  ${GREEN}[OK]${NC} .env file created"

# ─── Done ────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}Setup complete!${NC}"
echo ""
echo -e "  To start the lab:"
echo -e "    ${CYAN}source venv/bin/activate${NC}"
echo -e "    ${CYAN}export \$(cat .env | xargs)${NC}"
echo -e "    ${CYAN}python -m app.main${NC}"
echo ""
echo -e "  Then open: ${CYAN}http://localhost:5000${NC}"
echo ""
echo -e "  To reset the database:"
echo -e "    ${CYAN}mysql -u cysec_lab -p'cysec_lab_pass' cysec_lab < db/init.sql${NC}"
echo ""
