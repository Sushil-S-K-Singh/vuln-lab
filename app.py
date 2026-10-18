#!/usr/bin/env python3
"""
=============================================================================
  VULNLAB  ::  Deliberately Vulnerable Web Application
=============================================================================
  A self-hosted, intentionally insecure web app for security training.
  Modeled after TryHackMe / HackTheBox style labs.

  WARNING: This application is INTENTIONALLY VULNERABLE.
           Run it ONLY on an isolated local machine / lab network.
           NEVER expose it to the public internet.

  Vulnerabilities included:
    1. SQL Injection  -> authentication bypass on /login
    2. OS Command Injection -> RCE on /tools/ping
    3. Reverse shell / interactive RCE via #2
    4. (bonus) Verbose error leakage

  Author: built for the user's local lab.
=============================================================================
"""

import os
import re
import sqlite3
import subprocess
import platform
from datetime import datetime

from flask import (
    Flask, request, render_template, redirect, url_for,
    session, jsonify, make_response
)

# --------------------------------------------------------------------------
# App config
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "vulnlab.db")

app = Flask(__name__)
# Hardcoded weak secret -> also a "vulnerability" (forgeable sessions)
app.secret_key = "supersecretkey123"

FLAG = "FLAG{sql1_2_cmd1_2_r00t_1s_y0urs}"


# --------------------------------------------------------------------------
# Database helpers
# --------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create + seed the database with a couple of users."""
    conn = get_db()
    conn.executescript(
        """
        DROP TABLE IF EXISTS users;
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            email TEXT
        );
        """
    )
    users = [
        ("admin", "S3cur3Adm1nP@ss!", "admin", "admin@vulnlab.local"),
        ("guest", "guest", "user", "guest@vulnlab.local"),
        ("jdoe", "password123", "user", "jdoe@vulnlab.local"),
    ]
    conn.executemany(
        "INSERT INTO users (username, password, role, email) VALUES (?,?,?,?)",
        users,
    )
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", flag_unlocked=session.get("role") == "admin")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    query_shown = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        # ================================================================
        # VULNERABILITY #1 : SQL INJECTION (authentication bypass)
        # The query is built with raw string formatting -> injectable.
        #   Username: ' OR '1'='1' -- 
        #   Username: admin' -- 
        # ================================================================
        query_shown = (
            "SELECT * FROM users WHERE username = '%s' AND password = '%s'"
            % (username, password)
        )
        conn = get_db()
        user = None
        try:
            cur = conn.execute(query_shown)
            user = cur.fetchone()
        except Exception as exc:  # verbose error leak (bonus vuln)
            error = "SQL error: %s" % exc
        finally:
            conn.close()

        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        elif not error:
            error = "Invalid username or password."

    return render_template("login.html", error=error, query=query_shown)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template(
        "dashboard.html",
        user=session.get("user"),
        role=session.get("role"),
    )


@app.route("/tools/ping", methods=["GET", "POST"])
def ping():
    """
    ====================================================================
    VULNERABILITY #2 : OS COMMAND INJECTION  ->  RCE
    The user-supplied 'host' is concatenated straight into a shell
    command executed with shell=True. Any shell metacharacter works:
        ;  &&  ||  |  `...`  $(...)
    ====================================================================
    """
    output = None
    cmd_used = None
    if request.method == "POST":
        host = request.form.get("host", "")
        # VULNERABLE: no sanitisation, shell=True
        cmd_used = "ping -c 2 " + host
        try:
            proc = subprocess.run(
                cmd_used,
                shell=True,
                capture_output=True,
                text=True,
                timeout=20,
            )
            output = (proc.stdout or "") + (proc.stderr or "")
            if not output.strip():
                output = "[no output]"
        except subprocess.TimeoutExpired:
            output = "[command timed out]"
        except Exception as exc:
            output = "Error: %s" % exc
    return render_template("ping.html", output=output, cmd=cmd_used)


@app.route("/admin")
def admin():
    """Post-exploitation target: only reachable as admin (via SQLi bypass)."""
    if session.get("role") != "admin":
        return render_template("denied.html"), 403
    return render_template("admin.html", flag=FLAG, user=session.get("user"))


# --------------------------------------------------------------------------
# A small JSON API used by the dashboard "system info" widget.
# (Also handy for demonstrating that the box is Linux.)
# --------------------------------------------------------------------------
@app.route("/api/whoami")
def api_whoami():
    return jsonify(
        {
            "user": session.get("user", "anonymous"),
            "role": session.get("role", "guest"),
            "server": platform.platform(),
            "time": datetime.now().isoformat(timespec="seconds"),
        }
    )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        init_db()
    # Bind on all interfaces so you can reach it from your host machine.
    app.run(host="0.0.0.0", port=8000, debug=False)
