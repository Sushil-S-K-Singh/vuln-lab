#!/usr/bin/env python3
"""Standalone DB initializer for VULNLAB."""
from app import init_db, DB_PATH
import os

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("[*] removed old db")
init_db()
print("[+] database created at", DB_PATH)
print("    users seeded: admin, guest, jdoe")
