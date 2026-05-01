-- ═══════════════════════════════════════════════════════════════
-- CySec Don SQLi Training Lab - Database Initialization
-- ═══════════════════════════════════════════════════════════════
-- This database contains intentionally vulnerable tables for
-- educational purposes ONLY. Use exclusively in controlled lab
-- environments behind localhost or isolated Docker networks.
-- ═══════════════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS cysec_lab
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE cysec_lab;

-- ─── Users table ─────────────────────────────────────────────
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS credit_cards;
DROP TABLE IF EXISTS login_attempts;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          ENUM('admin','user','guest') NOT NULL DEFAULT 'user',
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    department    VARCHAR(100),
    salary        DECIMAL(12,2),
    secret_answer VARCHAR(255),
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ─── Products table (for search / union-based challenges) ───
CREATE TABLE products (
    product_id    INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(200) NOT NULL,
    description   TEXT,
    category      VARCHAR(100),
    price         DECIMAL(10,2) NOT NULL,
    stock         INT NOT NULL DEFAULT 0,
    is_visible    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ─── Credit cards (for demonstrating data extraction risk) ──
CREATE TABLE credit_cards (
    card_id       INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    card_type     VARCHAR(50),
    card_number   VARCHAR(255) NOT NULL,   -- encrypted in real apps, plain here for lab
    expiry_month  INT,
    expiry_year   INT,
    cvv           VARCHAR(10),
    holder_name   VARCHAR(200),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ─── Orders table (for second-order injection demo) ─────────
CREATE TABLE orders (
    order_id      INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    product_id    INT NOT NULL,
    quantity      INT NOT NULL DEFAULT 1,
    total_price   DECIMAL(10,2),
    status        ENUM('pending','shipped','delivered','cancelled') DEFAULT 'pending',
    notes         TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
) ENGINE=InnoDB;

-- ─── Login attempts (for monitoring / blind detection) ──────
CREATE TABLE login_attempts (
    attempt_id    INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50),
    ip_address    VARCHAR(45),
    success       BOOLEAN,
    user_agent    TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ─── Audit log (for trigger / monitoring demos) ─────────────
CREATE TABLE audit_log (
    log_id        INT AUTO_INCREMENT PRIMARY KEY,
    table_name    VARCHAR(100),
    action        VARCHAR(50),
    record_id     INT,
    old_value     TEXT,
    new_value     TEXT,
    performed_by  VARCHAR(100),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ═══════════════════════════════════════════════════════════════
-- SAMPLE DATA
-- ═══════════════════════════════════════════════════════════════

INSERT INTO users (username, email, password_hash, role, department, salary, secret_answer) VALUES
('admin',      'admin@cyseclab.local',    '$2b$12$LJ3m8a6B2XQFPvOGEMZOoOLwNqSDJGJLd8M5F3hGRmITZGZhFbvCe', 'admin', 'IT Security',       120000.00, 'shield'),
('alice',      'alice@cyseclab.local',    '$2b$12$LJ3m8a6B2XQFPvOGEMZOoOLwNqSDJGJLd8M5F3hGRmITZGZhFbvCe', 'user',  'Engineering',       95000.00,  'rabbit'),
('bob',        'bob@cyseclab.local',      '$2b$12$LJ3m8a6B2XQFPvOGEMZOoOLwNqSDJGJLd8M5F3hGRmITZGZhFbvCe', 'user',  'Marketing',        78000.00,  'dragon'),
('charlie',    'charlie@cyseclab.local',  '$2b$12$LJ3m8a6B2XQFPvOGEMZOoOLwNqSDJGJLd8M5F3hGRmITZGZhFbvCe', 'user',  'Finance',          88000.00,  'castle'),
('diana',      'diana@cyseclab.local',    '$2b$12$LJ3m8a6B2XQFPvOGEMZOoOLwNqSDJGJLd8M5F3hGRmITZGZhFbvCe', 'user',  'Human Resources',  72000.00,  'phoenix'),
('eve',        'eve@cyseclab.local',      '$2b$12$LJ3m8a6B2XQFPvOGEMZOoOLwNqSDJGJLd8M5F3hGRmITZGZhFbvCe', 'user',  'Engineering',       92000.00,  'matrix'),
('mallory',    'mallory@cyseclab.local',  '$2b$12$LJ3m8a6B2XQFPvOGEMZOoOLwNqSDJGJLd8M5F3hGRmITZGZhFbvCe', 'guest', 'Contractor',       65000.00,  'trojan'),
('oscar',      'oscar@cyseclab.local',    '$2b$12$LJ3m8a6B2XQFPvOGEMZOoOLwNqSDJGJLd8M5F3hGRmITZGZhFbvCe', 'user',  'Sales',            70000.00,  'falcon'),
('pentest',    'pentest@cyseclab.local',  '$2b$12$LJ3m8a6B2XQFPvOGEMZOoOLwNqSDJGJLd8M5F3hGRmITZGZhFbvCe', 'admin', 'Quality Assurance', 85000.00, 'testing');
-- All passwords hash to the bcrypt hash of "password"

INSERT INTO products (name, description, category, price, stock) VALUES
('SecureVault Pro',    'Enterprise-grade firewall appliance with IDS/IPS',       'Security',    2499.99, 15),
('DataShield X1',      'Hardware encryption module for data-at-rest',            'Security',    899.99,  42),
('NetMonitor 360',     'Network traffic analysis and anomaly detection suite',   'Monitoring',  1299.99, 28),
('LogMaster Pro',      'Centralized log management and SIEM solution',           'Monitoring',  1799.99, 19),
('PatchGuard',         'Automated vulnerability scanning and patch management',  'Security',    599.99,  55),
('AuthForge',          'Multi-factor authentication and identity management',    'Access',      449.99,  67),
('CryptoSafe USB',     'Hardware-encrypted USB storage device (256GB)',           'Storage',     189.99,  120),
('IncidentBoard',      'Collaborative incident response and case management',    'Operations',  2199.99, 11),
('ThreatIntel Feed',   'Real-time threat intelligence aggregation platform',      'Intelligence',699.99,  33),
('PenTest Toolkit',    'Automated penetration testing and reporting framework',   'Testing',     999.99,  24),
('BackupVault NAS',    '4-bay NAS with deduplication and ransomware protection',  'Storage',     749.99,  38),
('ZeroTrust Gateway',  'Zero-trust network access (ZTNA) gateway appliance',      'Access',      1899.99, 17);

INSERT INTO credit_cards (user_id, card_type, card_number, expiry_month, expiry_year, cvv, holder_name) VALUES
(1, 'Visa',       '4532-XXXX-XXXX-7891', 12, 2027, 'XXX', 'Admin User'),
(2, 'Mastercard', '5412-XXXX-XXXX-3456', 6,  2026, 'XXX', 'Alice Chen'),
(3, 'Visa',       '4916-XXXX-XXXX-9012', 9,  2028, 'XXX', 'Bob Martinez'),
(4, 'Amex',       '3782-XXXX-XXXX-5678', 3,  2025, 'XXX', 'Charlie Davis'),
(5, 'Mastercard', '5500-XXXX-XXXX-2345', 1,  2027, 'XXX', 'Diana Patel');

INSERT INTO orders (user_id, product_id, quantity, total_price, status, notes) VALUES
(2, 1, 1, 2499.99, 'delivered',   'Standard deployment'),
(2, 3, 2, 2599.98, 'shipped',     'One for each data center'),
(3, 5, 5, 2999.95, 'delivered',   'Company-wide deployment'),
(4, 10, 1, 999.99, 'pending',     'PO-2024-0847'),
(5, 6, 10, 4499.90, 'shipped',    'Employee onboarding batch');

-- ─── Indexes for performance and lab realism ────────────────
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);

-- ─── Audit trigger (demonstrates monitoring for Part VI) ────
DELIMITER //
CREATE TRIGGER trg_users_audit
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    IF OLD.role != NEW.role OR OLD.is_active != NEW.is_active THEN
        INSERT INTO audit_log (table_name, action, record_id, old_value, new_value, performed_by)
        VALUES ('users', 'UPDATE', NEW.user_id,
                CONCAT('role=', OLD.role, ', active=', OLD.is_active),
                CONCAT('role=', NEW.role, ', active=', NEW.is_active),
                CURRENT_USER());
    END IF;
END//
DELIMITER ;
