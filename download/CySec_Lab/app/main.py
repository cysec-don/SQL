"""
CySec Don SQLi Training Lab
============================
A professional, intentionally vulnerable web application for
learning SQL injection detection, analysis, and defense.

Author: CySec Don (cysecdon@gmail.com)
License: Educational use only. Never deploy on public networks.

WARNING: This application contains INTENTIONAL security vulnerabilities.
         Use ONLY in isolated lab environments (localhost, Docker, VMs).
         Unauthorized use against systems you do not own is ILLEGAL.
"""

import os
import re
import time
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, g, flash, abort
)
import mysql.connector
from mysql.connector import Error as MySQLError

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'cysec-lab-dev-key-change-in-production')

# Security level: 'low', 'medium', 'high'
# Low = full errors, no sanitization
# Medium = some escaping, suppressed errors
# High = parameterized queries (secure)
SECURITY_LEVEL = os.environ.get('SECURITY_LEVEL', 'low')

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'db'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'cysec_lab'),
    'password': os.environ.get('DB_PASSWORD', 'cysec_lab_pass'),
    'database': os.environ.get('DB_NAME', 'cysec_lab'),
    'autocommit': True,
    'pool_name': 'cysec_pool',
    'pool_size': 5,
}

# Challenge tracking
CHALLENGES = {
    'auth_bypass': {
        'name': 'Authentication Bypass',
        'category': 'In-Band (Error-Based)',
        'difficulty': 'Beginner',
        'description': 'Exploit a vulnerable login form to bypass authentication without valid credentials.',
        'points': 100,
        'table': 'users',
    },
    'error_based': {
        'name': 'Error-Based SQLi',
        'category': 'In-Band (Error-Based)',
        'difficulty': 'Beginner',
        'description': 'Extract database information through error messages returned by the server.',
        'points': 150,
        'table': 'products',
    },
    'union_based': {
        'name': 'Union-Based SQLi',
        'category': 'In-Band (Union-Based)',
        'difficulty': 'Intermediate',
        'description': 'Use UNION SELECT to combine results and extract data from other tables.',
        'points': 200,
        'table': 'products',
    },
    'boolean_blind': {
        'name': 'Boolean-Based Blind SQLi',
        'category': 'Blind (Boolean)',
        'difficulty': 'Intermediate',
        'description': 'Extract data by asking true/false questions and observing response differences.',
        'points': 250,
        'table': 'users',
    },
    'time_blind': {
        'name': 'Time-Based Blind SQLi',
        'category': 'Blind (Time)',
        'difficulty': 'Advanced',
        'description': 'Extract data when no visible difference exists, using time delays.',
        'points': 350,
        'table': 'users',
    },
    'second_order': {
        'name': 'Second-Order SQLi',
        'category': 'Second-Order',
        'difficulty': 'Advanced',
        'description': 'Payload stored in the database, triggered by a separate action later.',
        'points': 400,
        'table': 'users',
    },
    'data_extraction': {
        'name': 'Full Data Extraction',
        'category': 'In-Band (Union)',
        'difficulty': 'Advanced',
        'description': 'Extract sensitive data from the credit_cards table using injection techniques.',
        'points': 500,
        'table': 'credit_cards',
    },
    'privilege_escalation': {
        'name': 'Privilege Escalation',
        'category': 'In-Band',
        'difficulty': 'Expert',
        'description': 'Escalate a regular user account to admin privileges via SQL injection.',
        'points': 600,
        'table': 'users',
    },
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATABASE CONNECTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_db():
    """Get a database connection from the pool."""
    if 'db' not in g:
        try:
            g.db = mysql.connector.connect(**DB_CONFIG)
        except MySQLError as e:
            app.logger.error(f"Database connection failed: {e}")
            raise
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Close the database connection when the app context ends."""
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()

def query_db(query, params=None, fetch=True):
    """Execute a SQL query and return results. Raw SQL, no protection."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        if fetch:
            result = cursor.fetchall()
            return result
        conn.commit()
        return cursor.rowcount
    except MySQLError as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()

def safe_query_db(query, params=None, fetch=True):
    """Execute a parameterized SQL query (secure)."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        if fetch:
            return cursor.fetchall()
        conn.commit()
        return cursor.rowcount
    except MySQLError as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_completed_challenges():
    """Get list of completed challenge IDs from session."""
    return set(session.get('completed', []))

def mark_challenge_complete(challenge_id):
    """Mark a challenge as completed."""
    completed = get_completed_challenges()
    completed.add(challenge_id)
    session['completed'] = list(completed)
    session['score'] = sum(
        CHALLENGES[c]['points'] for c in completed
        if c in CHALLENGES
    )

def log_login_attempt(username, success):
    """Log a login attempt for monitoring demo."""
    ip = request.remote_addr or 'unknown'
    ua = request.headers.get('User-Agent', 'unknown')[:200]
    try:
        safe_query_db(
            "INSERT INTO login_attempts (username, ip_address, success, user_agent) VALUES (%s, %s, %s, %s)",
            (username, ip, success, ua), fetch=False
        )
    except Exception:
        pass  # Logging failures should not break the app

def is_safe_input(text, pattern=r'^[\w\s\-\.@,]*$'):
    """Basic input validation (medium security level)."""
    return bool(re.match(pattern, str(text)))

def sanitize_input(text):
    """Basic input sanitization (medium security level)."""
    # Escape single quotes by doubling them
    return str(text).replace("'", "''")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ROUTES: PAGES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.route('/')
def index():
    """Dashboard with challenge list and progress."""
    completed = get_completed_challenges()
    total_score = session.get('score', 0)
    max_score = sum(c['points'] for c in CHALLENGES.values())

    # Get recent login attempts for monitoring demo
    attempts = []
    try:
        attempts = safe_query_db(
            "SELECT * FROM login_attempts ORDER BY created_at DESC LIMIT 10"
        )
    except Exception:
        pass

    # Get audit log entries
    audit = []
    try:
        audit = safe_query_db(
            "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 10"
        )
    except Exception:
        pass

    return render_template('dashboard.html',
        challenges=CHALLENGES,
        completed=completed,
        total_score=total_score,
        max_score=max_score,
        security_level=SECURITY_LEVEL,
        recent_attempts=attempts,
        audit_log=audit,
    )

@app.route('/guide')
def guide():
    """Lab guide and instructions."""
    return render_template('guide.html',
        security_level=SECURITY_LEVEL,
        challenges=CHALLENGES,
    )

@app.route('/setup')
def setup_info():
    """Setup and installation guide."""
    return render_template('setup.html')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHALLENGE 1: AUTHENTICATION BYPASS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Vulnerable login form - demonstrates auth bypass."""
    error = None
    success = False

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        if SECURITY_LEVEL == 'low':
            # VULNERABLE: Direct string concatenation
            try:
                query = f"SELECT * FROM users WHERE username = '{username}' AND password_hash = '{password}'"
                results = query_db(query)
                if results:
                    session['user'] = results[0]
                    success = True
                    log_login_attempt(username, True)
                    # Check if bypassed (logged in as admin without real password)
                    if results[0]['role'] == 'admin':
                        mark_challenge_complete('auth_bypass')
                        flash('Challenge Complete: Authentication Bypass!', 'success')
                    return redirect(url_for('profile'))
                else:
                    error = "Invalid username or password."
                    log_login_attempt(username, False)
            except MySQLError as e:
                error = f"Database Error: {e}"
                log_login_attempt(username, False)

        elif SECURITY_LEVEL == 'medium':
            # MEDIUM: Basic escaping (still vulnerable to some techniques)
            try:
                safe_user = sanitize_input(username)
                safe_pass = sanitize_input(password)
                query = f"SELECT * FROM users WHERE username = '{safe_user}' AND password_hash = '{safe_pass}'"
                results = query_db(query)
                if results:
                    session['user'] = results[0]
                    success = True
                    log_login_attempt(username, True)
                    if results[0]['role'] == 'admin':
                        mark_challenge_complete('auth_bypass')
                        flash('Challenge Complete: Authentication Bypass!', 'success')
                    return redirect(url_for('profile'))
                else:
                    error = "Invalid username or password."
                    log_login_attempt(username, False)
            except MySQLError as e:
                error = "Login failed. Please try again."
                log_login_attempt(username, False)

        else:
            # HIGH: Parameterized query (secure)
            try:
                results = safe_query_db(
                    "SELECT * FROM users WHERE username = %s", (username,)
                )
                if results:
                    # In production, use bcrypt check; here simplified for lab
                    if results[0]['password_hash'] == password:
                        session['user'] = results[0]
                        success = True
                        log_login_attempt(username, True)
                        return redirect(url_for('profile'))
                error = "Invalid username or password."
                log_login_attempt(username, False)
            except MySQLError:
                error = "Login failed. Please try again."
                log_login_attempt(username, False)

    return render_template('login.html', error=error, challenge=CHALLENGES['auth_bypass'])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHALLENGE 2: ERROR-BASED SQLi (Product Search)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.route('/search', methods=['GET', 'POST'])
def search():
    """Product search vulnerable to error-based SQL injection."""
    results = []
    search_term = ''
    error_msg = None
    num_columns = 3  # Column count hint

    if request.method == 'POST':
        search_term = request.form.get('q', '')
        category = request.form.get('category', '')

        if SECURITY_LEVEL == 'low':
            # VULNERABLE: Direct string concatenation in WHERE clause
            try:
                query = f"SELECT product_id, name, price FROM products WHERE name LIKE '%{search_term}%'"
                if category:
                    query += f" AND category = '{category}'"
                results = query_db(query)

                # Detect information_schema access for challenge completion
                if 'information_schema' in search_term.lower():
                    mark_challenge_complete('error_based')
                    flash('Challenge Complete: Error-Based SQLi!', 'success')

            except MySQLError as e:
                error_msg = str(e)
                if 'information_schema' in search_term.lower():
                    mark_challenge_complete('error_based')
                    flash('Challenge Complete: Error-Based SQLi!', 'success')

        elif SECURITY_LEVEL == 'medium':
            # MEDIUM: Some escaping
            try:
                safe_term = sanitize_input(search_term).replace('%', '\\%').replace('_', '\\_')
                query = f"SELECT product_id, name, price FROM products WHERE name LIKE '%{safe_term}%'"
                if category and is_safe_input(category):
                    query += f" AND category = '{category}'"
                results = query_db(query)
            except MySQLError:
                error_msg = "An error occurred. Please refine your search."

        else:
            # HIGH: Parameterized query (secure)
            try:
                results = safe_query_db(
                    "SELECT product_id, name, price FROM products WHERE name LIKE %s",
                    (f'%{search_term}%',)
                )
            except MySQLError:
                error_msg = "An error occurred."

    return render_template('search.html',
        results=results, search_term=search_term, error=error_msg,
        num_columns=num_columns, category=category,
        challenge=CHALLENGES['error_based'],
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHALLENGE 3: UNION-BASED SQLi (Product Search Extended)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.route('/union-search', methods=['GET', 'POST'])
def union_search():
    """Product search vulnerable to UNION-based injection."""
    results = []
    search_term = ''
    error_msg = None

    if request.method == 'POST':
        search_term = request.form.get('q', '')

        if SECURITY_LEVEL == 'low':
            # VULNERABLE: Direct concatenation, 3 columns in original query
            try:
                query = f"""
                    SELECT product_id, name, price
                    FROM products
                    WHERE name LIKE '%{search_term}%'
                """
                results = query_db(query)

                # Detect UNION usage for challenge completion
                if 'union' in search_term.lower() and 'select' in search_term.lower():
                    if len(results) > 0:
                        mark_challenge_complete('union_based')
                        flash('Challenge Complete: Union-Based SQLi!', 'success')

                # Detect credit card extraction
                if 'credit_cards' in search_term.lower() and len(results) > 0:
                    mark_challenge_complete('data_extraction')
                    flash('Challenge Complete: Full Data Extraction!', 'success')

            except MySQLError as e:
                error_msg = str(e)
                if 'union' in search_term.lower():
                    mark_challenge_complete('union_based')
                    flash('Challenge Complete: Union-Based SQLi!', 'success')

        elif SECURITY_LEVEL == 'medium':
            try:
                safe_term = sanitize_input(search_term)
                query = f"SELECT product_id, name, price FROM products WHERE name LIKE '%{safe_term}%'"
                results = query_db(query)
            except MySQLError:
                error_msg = "An error occurred."

        else:
            results = safe_query_db(
                "SELECT product_id, name, price FROM products WHERE name LIKE %s",
                (f'%{search_term}%',)
            )

    return render_template('search.html',
        results=results, search_term=search_term, error=error_msg,
        num_columns=3, mode='union', category='',
        challenge=CHALLENGES['union_based'],
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHALLENGE 4: BOOLEAN-BASED BLIND SQLi (User Lookup)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.route('/user-lookup', methods=['GET', 'POST'])
def user_lookup():
    """User lookup vulnerable to boolean-based blind injection."""
    result = None
    lookup_id = ''
    hint = 'Enter a user ID (1-9) to look up user information.'

    if request.method == 'POST':
        lookup_id = request.form.get('user_id', '')

        if SECURITY_LEVEL == 'low':
            # VULNERABLE: Direct concatenation
            try:
                query = f"SELECT user_id, username, email, department, salary FROM users WHERE user_id = {lookup_id}"
                results = query_db(query)
                if results:
                    result = results[0]
                    hint = f"Found user: {result['username']}"

                    # Detect blind injection for challenge completion
                    if 'and' in lookup_id.lower() or 'or' in lookup_id.lower():
                        if 'select' in lookup_id.lower() or 'substr' in lookup_id.lower() or 'substring' in lookup_id.lower():
                            mark_challenge_complete('boolean_blind')
                            flash('Challenge Complete: Boolean-Based Blind SQLi!', 'success')
                else:
                    hint = "No user found with that ID."
            except MySQLError as e:
                hint = "An error occurred."
                if SECURITY_LEVEL == 'low':
                    hint += f" {e}"

        elif SECURITY_LEVEL == 'medium':
            if is_safe_input(lookup_id, r'^[\d\s]*$'):
                try:
                    results = safe_query_db(
                        "SELECT user_id, username, email, department, salary FROM users WHERE user_id = %s",
                        (int(lookup_id),)
                    )
                    if results:
                        result = results[0]
                        hint = f"Found user: {result['username']}"
                    else:
                        hint = "No user found with that ID."
                except (MySQLError, ValueError):
                    hint = "Invalid user ID."
            else:
                hint = "Invalid input. Only numbers allowed."

        else:
            try:
                uid = int(lookup_id)
                results = safe_query_db(
                    "SELECT user_id, username, email, department, salary FROM users WHERE user_id = %s",
                    (uid,)
                )
                if results:
                    result = results[0]
                    hint = f"Found user: {result['username']}"
                else:
                    hint = "No user found with that ID."
            except (MySQLError, ValueError):
                hint = "Invalid user ID."

    return render_template('user_lookup.html',
        result=result, lookup_id=lookup_id, hint=hint,
        submitted=True if request.method == 'POST' else False,
        challenge=CHALLENGES['boolean_blind'],
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHALLENGE 5: TIME-BASED BLIND SQLi (Ping Check)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.route('/ping', methods=['GET', 'POST'])
def ping():
    """Server check vulnerable to time-based blind injection."""
    response_text = 'Server is running.'
    response_time = 0
    target_id = ''
    hint = 'Enter a target ID to check server status.'

    if request.method == 'POST':
        target_id = request.form.get('target_id', '')
        start_time = time.time()

        if SECURITY_LEVEL == 'low':
            # VULNERABLE: Direct concatenation with timing function
            try:
                query = f"SELECT username FROM users WHERE user_id = {target_id}"
                results = query_db(query)
                if results:
                    response_text = f"Target {target_id}: Active ({results[0]['username']})"
                else:
                    response_text = f"Target {target_id}: Not found"

                # Detect time-based injection
                if 'sleep' in target_id.lower() or 'benchmark' in target_id.lower():
                    mark_challenge_complete('time_blind')
                    flash('Challenge Complete: Time-Based Blind SQLi!', 'success')

            except MySQLError:
                response_text = "Error checking target."

            response_time = round(time.time() - start_time, 2)

        elif SECURITY_LEVEL == 'medium':
            if is_safe_input(target_id, r'^[\d\s]*$'):
                try:
                    uid = int(target_id)
                    results = safe_query_db(
                        "SELECT username FROM users WHERE user_id = %s", (uid,)
                    )
                    response_text = f"Target {target_id}: {'Active' if results else 'Not found'}"
                except (MySQLError, ValueError):
                    response_text = "Error checking target."
            else:
                response_text = "Invalid target ID."

            response_time = round(time.time() - start_time, 2)

        else:
            try:
                uid = int(target_id)
                results = safe_query_db(
                    "SELECT username FROM users WHERE user_id = %s", (uid,)
                )
                response_text = f"Target {target_id}: {'Active' if results else 'Not found'}"
            except (MySQLError, ValueError):
                response_text = "Error checking target."

            response_time = round(time.time() - start_time, 2)

    return render_template('ping.html',
        response_text=response_text, response_time=response_time,
        target_id=target_id, hint=hint,
        challenge=CHALLENGES['time_blind'],
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHALLENGE 6: SECOND-ORDER SQLi (Registration + Profile)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration form that stores user input (second-order vector)."""
    error = None
    success_msg = None

    if request.method == 'POST':
        username = request.form.get('username', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        department = request.form.get('department', '')

        if SECURITY_LEVEL == 'low':
            # Store without sanitization (payload will be used unsafely later)
            try:
                query_db(
                    f"INSERT INTO users (username, email, password_hash, department) "
                    f"VALUES ('{username}', '{email}', '{password}', '{department}')",
                    fetch=False
                )
                success_msg = f"Registration successful! Welcome, {username}."
                flash('Registration successful! Try the Profile Search with your username.', 'info')
            except MySQLError as e:
                error = f"Registration failed: {e}" if SECURITY_LEVEL == 'low' else "Registration failed."

        elif SECURITY_LEVEL == 'medium':
            safe_user = sanitize_input(username)
            safe_email = sanitize_input(email)
            safe_dept = sanitize_input(department)
            try:
                safe_query_db(
                    "INSERT INTO users (username, email, password_hash, department) VALUES (%s, %s, %s, %s)",
                    (safe_user, safe_email, password, safe_dept), fetch=False
                )
                success_msg = f"Registration successful! Welcome, {safe_user}."
            except MySQLError:
                error = "Registration failed. Username or email may already exist."

        else:
            try:
                safe_query_db(
                    "INSERT INTO users (username, email, password_hash, department) VALUES (%s, %s, %s, %s)",
                    (username, email, password, department), fetch=False
                )
                success_msg = f"Registration successful! Welcome, {username}."
            except MySQLError:
                error = "Registration failed. Username or email may already exist."

    return render_template('register.html',
        error=error, success=success_msg,
        username=username, email=email, department=department,
        challenge=CHALLENGES['second_order'],
    )

@app.route('/profile-search', methods=['GET', 'POST'])
def profile_search():
    """Profile search that uses stored data unsafely (second-order trigger)."""
    result = None
    search_term = ''
    hint = 'Search for a user by name. (Try a username you registered with a payload!)'

    if request.method == 'POST':
        search_term = request.form.get('username', '')

        if SECURITY_LEVEL == 'low':
            # VULNERABLE: Uses stored data in unsanitized query (second-order)
            try:
                # This pulls the stored username and uses it in a new query
                query = f"""
                    SELECT u.user_id, u.username, u.email, u.department, u.salary, u.role
                    FROM users u
                    WHERE u.username = '{search_term}'
                """
                results = query_db(query)
                if results:
                    result = results[0]
                    hint = f"Profile found for: {result['username']}"

                    # Detect second-order injection trigger
                    if "'" in search_term or '"' in search_term:
                        mark_challenge_complete('second_order')
                        flash('Challenge Complete: Second-Order SQLi!', 'success')
                else:
                    hint = "No profile found."
            except MySQLError as e:
                hint = f"Query error: {e}" if SECURITY_LEVEL == 'low' else "Profile lookup failed."
                if "'" in search_term or '"' in search_term:
                    mark_challenge_complete('second_order')
                    flash('Challenge Complete: Second-Order SQLi!', 'success')

        elif SECURITY_LEVEL == 'medium':
            try:
                safe_term = sanitize_input(search_term)
                results = safe_query_db(
                    "SELECT user_id, username, email, department, salary, role FROM users WHERE username = %s",
                    (safe_term,)
                )
                if results:
                    result = results[0]
                    hint = f"Profile found for: {result['username']}"
                else:
                    hint = "No profile found."
            except MySQLError:
                hint = "Profile lookup failed."

        else:
            try:
                results = safe_query_db(
                    "SELECT user_id, username, email, department, salary, role FROM users WHERE username = %s",
                    (search_term,)
                )
                if results:
                    result = results[0]
                    hint = f"Profile found for: {result['username']}"
                else:
                    hint = "No profile found."
            except MySQLError:
                hint = "Profile lookup failed."

    return render_template('profile_search.html',
        result=result, search_term=search_term, hint=hint,
        challenge=CHALLENGES['second_order'],
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHALLENGE 7 & 8: PRIVILEGE ESCALATION & DATA EXTRACTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.route('/admin/update-role', methods=['GET', 'POST'])
def admin_update_role():
    """Admin panel to update user roles - demonstrates privilege escalation."""
    users_list = []
    error = None
    success_msg = None

    try:
        users_list = safe_query_db("SELECT user_id, username, role FROM users ORDER BY user_id")
    except Exception:
        pass

    if request.method == 'POST':
        user_id = request.form.get('user_id', '')
        new_role = request.form.get('new_role', '')

        if SECURITY_LEVEL == 'low':
            # VULNERABLE: Both user_id and new_role are injectable
            try:
                query = f"UPDATE users SET role = '{new_role}' WHERE user_id = {user_id}"
                rows = query_db(query, fetch=False)
                if rows > 0:
                    success_msg = f"Role updated to '{new_role}' for user ID {user_id}."
                    mark_challenge_complete('privilege_escalation')
                    flash('Challenge Complete: Privilege Escalation!', 'success')
                    users_list = safe_query_db("SELECT user_id, username, role FROM users ORDER BY user_id")
                else:
                    error = "No user found with that ID."
            except MySQLError as e:
                error = f"Update failed: {e}" if SECURITY_LEVEL == 'low' else "Update failed."

        elif SECURITY_LEVEL == 'medium':
            if is_safe_input(new_role, r'^[\w\s]*$'):
                try:
                    safe_query_db(
                        "UPDATE users SET role = %s WHERE user_id = %s",
                        (new_role, int(user_id)), fetch=False
                    )
                    success_msg = f"Role updated."
                    users_list = safe_query_db("SELECT user_id, username, role FROM users ORDER BY user_id")
                except (MySQLError, ValueError):
                    error = "Invalid input."
            else:
                error = "Invalid role value."

        else:
            try:
                valid_roles = ['admin', 'user', 'guest']
                if new_role in valid_roles:
                    safe_query_db(
                        "UPDATE users SET role = %s WHERE user_id = %s",
                        (new_role, int(user_id)), fetch=False
                    )
                    success_msg = f"Role updated."
                    users_list = safe_query_db("SELECT user_id, username, role FROM users ORDER BY user_id")
                else:
                    error = "Invalid role."
            except (MySQLError, ValueError):
                error = "Invalid input."

    return render_template('admin.html',
        users=users_list, error=error, success=success_msg,
        challenge=CHALLENGES['privilege_escalation'],
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROFILE PAGE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.route('/profile')
def profile():
    """User profile page after login."""
    if 'user' not in session:
        return redirect(url_for('login'))
    user = session['user']
    return render_template('profile.html', user=user)

@app.route('/logout')
def logout():
    """Clear session and redirect to login."""
    session.clear()
    return redirect(url_for('index'))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UTILITY ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.route('/reset-db')
def reset_db():
    """Reset the database to its initial state."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        # Try Docker path first, then local source path
        sql_path = '/app/db/init.sql'
        if not os.path.exists(sql_path):
            sql_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'db', 'init.sql')
        with open(sql_path, 'r') as f:
            sql = f.read()
        # mysql.connector doesn't support DELIMITER syntax
        statements = sql.split(';')
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt or stmt.startswith('DELIMITER') or stmt == '//':
                continue
            stmt = stmt.replace('//', '')
            if stmt.strip():
                try:
                    cursor.execute(stmt)
                except Exception:
                    pass  # Skip individual failures (e.g. partial trigger body)
        conn.commit()
        cursor.close()
        session.clear()
        flash('Database reset to initial state.', 'info')
    except Exception as e:
        flash(f'Reset failed: {e}', 'error')
    return redirect(url_for('index'))

@app.route('/set-level/<level>')
def set_level(level):
    """Change the security level (for educational comparison)."""
    if level in ('low', 'medium', 'high'):
        global SECURITY_LEVEL
        SECURITY_LEVEL = level
        session['security_level'] = level
        flash(f'Security level set to: {level.upper()}', 'info')
    return redirect(url_for('index'))

@app.route('/api/schema')
def api_schema():
    """Return database schema info (for lab reference)."""
    try:
        tables = safe_query_db(
            "SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema = %s",
            (DB_CONFIG['database'],)
        )
        columns = safe_query_db(
            "SELECT table_name, column_name, column_type, is_nullable, column_key "
            "FROM information_schema.columns WHERE table_schema = %s ORDER BY table_name, ordinal_position",
            (DB_CONFIG['database'],)
        )
        return jsonify({'tables': tables, 'columns': columns})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == '__main__':
    # Wait for database to be ready on first startup
    import time
    max_retries = 30
    for i in range(max_retries):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            conn.close()
            print("Database connection established!")
            break
        except MySQLError:
            print(f"Waiting for database... ({i+1}/{max_retries})")
            time.sleep(2)
    else:
        print("ERROR: Could not connect to database after 60 seconds.")
        print("Ensure the database container is running.")

    app.run(host='0.0.0.0', port=5000, debug=False)
