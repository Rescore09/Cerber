"""
License Key Authentication API
A secure Flask-based license validation system with admin management
"""

import os
import json
import uuid
import hashlib
import secrets
import sqlite3
import platform
import subprocess
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Any, Optional, Tuple

import requests
from flask import Flask, request, jsonify
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich import box
import threading
import time

console = Console()

class LicenseDB:
    
    def __init__(self, db_path: str = "licenses.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                key TEXT PRIMARY KEY,
                hwid TEXT,
                expires_at TEXT NOT NULL,
                plan TEXT DEFAULT 'basic',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT,
                ip_address TEXT,
                user_agent TEXT,
                hwid TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                geo_country TEXT,
                FOREIGN KEY (license_key) REFERENCES licenses (key)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_license(self, key: str, hwid: str, expires_at: str, plan: str = "basic") -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO licenses (key, hwid, expires_at, plan) VALUES (?, ?, ?, ?)",
                (key, hwid, expires_at, plan)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_license(self, key: str) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT key, hwid, expires_at, plan FROM licenses WHERE key = ?",
            (key,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "key": result[0],
                "hwid": result[1],
                "expires_at": result[2],
                "plan": result[3]
            }
        return None
    
    def delete_license(self, key: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM licenses WHERE key = ?", (key,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    
    def reset_hwid(self, key: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE licenses SET hwid = NULL WHERE key = ?", (key,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    
    def log_usage(self, license_key: str, ip: str, user_agent: str, hwid: str, geo_country: str = "Unknown"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usage_logs (license_key, ip_address, user_agent, hwid, geo_country) VALUES (?, ?, ?, ?, ?)",
            (license_key, ip, user_agent, hwid, geo_country)
        )
        conn.commit()
        conn.close()
    
    def get_usage_info(self, license_key: str) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                ip_address, user_agent, hwid, geo_country,
                MIN(timestamp) as first_login,
                MAX(timestamp) as last_login,
                COUNT(*) as login_count
            FROM usage_logs 
            WHERE license_key = ?
            GROUP BY license_key
        ''', (license_key,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "ip": result[0],
                "user_agent": result[1],
                "hwid": result[2],
                "geo_country": result[3],
                "first_login": result[4],
                "last_login": result[5],
                "login_count": result[6]
            }
        return None

class SystemInfo:
    
    @staticmethod
    def get_cpu_serial() -> str:
        try:
            system = platform.system()
            if system == "Windows":
                result = subprocess.run(
                    ['wmic', 'cpu', 'get', 'ProcessorId', '/value'],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.split('\n'):
                    if 'ProcessorId=' in line:
                        return line.split('=')[1].strip()
            elif system == "Linux":
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'Serial' in line or 'processor' in line:
                            return hashlib.md5(line.encode()).hexdigest()[:16]
            elif system == "Darwin":  
                result = subprocess.run(
                    ['system_profiler', 'SPHardwareDataType'],
                    capture_output=True, text=True, timeout=5
                )
                return hashlib.md5(result.stdout.encode()).hexdigest()[:16]
        except:
            pass
        
        system_info = f"{platform.node()}{platform.processor()}{platform.machine()}"
        return hashlib.md5(system_info.encode()).hexdigest()[:16]

class GeoLocation:
    
    @staticmethod
    def get_country(ip: str) -> str:
        try:
            response = requests.get(f"http://ip-api.com/json/{ip}", timeout=2)
            if response.status_code == 200:
                data = response.json()
                return data.get('countryCode', 'Unknown')
        except:
            pass
        return 'Unknown'

class APIStats:
    
    def __init__(self):
        self.start_time = datetime.now()
        self.request_count = 0
        self.verify_requests = 0
        self.admin_requests = 0
        self.error_count = 0
        self.active_licenses = 0
        self.lock = threading.Lock()
    
    def increment_request(self, endpoint_type: str = "general"):
        with self.lock:
            self.request_count += 1
            if endpoint_type == "verify":
                self.verify_requests += 1
            elif endpoint_type == "admin":
                self.admin_requests += 1
    
    def increment_error(self):
        with self.lock:
            self.error_count += 1
    
    def get_stats(self) -> Dict:
        with self.lock:
            uptime = datetime.now() - self.start_time
            return {
                "uptime": str(uptime).split('.')[0],
                "total_requests": self.request_count,
                "verify_requests": self.verify_requests,
                "admin_requests": self.admin_requests,
                "error_count": self.error_count,
                "success_rate": f"{((self.request_count - self.error_count) / max(self.request_count, 1) * 100):.1f}%"
            }

db = LicenseDB()
stats = APIStats()
admin_key = secrets.token_urlsafe(32)
app = Flask(__name__)

def require_admin_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            stats.increment_error()
            return jsonify({"error": "Missing or invalid authorization header"}), 401
        
        token = auth_header.split(' ')[1]
        if token != admin_key:
            stats.increment_error()
            return jsonify({"error": "Invalid admin key"}), 401
        
        stats.increment_request("admin")
        return f(*args, **kwargs)
    return decorated_function

def generate_license_key() -> str:
    return f"LIC-{secrets.token_urlsafe(16).upper()}"

def is_expired(expires_at: str) -> bool:
    try:
        expiry_date = datetime.strptime(expires_at, "%Y-%m-%d")
        return datetime.now() > expiry_date
    except:
        return True

@app.route('/verify', methods=['POST'])
def verify_license():
    try:
        data = request.get_json()
        if not data or 'key' not in data or 'hwid' not in data:
            stats.increment_error()
            return jsonify({"error": "Missing required fields"}), 400
        
        license_key = data['key']
        hwid = data['hwid']
        
        license_info = db.get_license(license_key)
        if not license_info:
            stats.increment_error()
            return jsonify({"error": "Key not found"}), 401

        if is_expired(license_info['expires_at']):
            stats.increment_error()
            return jsonify({"error": "License expired"}), 410
        
        if license_info['hwid'] is None:
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE licenses SET hwid = ? WHERE key = ?", (hwid, license_key))
            conn.commit()
            conn.close()
        elif license_info['hwid'] != hwid:
            stats.increment_error()
            return jsonify({"error": "HWID mismatch"}), 403
        
        ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent', 'Unknown')
        geo_country = GeoLocation.get_country(ip)
        
        db.log_usage(license_key, ip, user_agent, hwid, geo_country)
        stats.increment_request("verify")
        
        return jsonify({
            "valid": True,
            "expires_at": license_info['expires_at'],
            "plan": license_info['plan']
        })
        
    except Exception as e:
        stats.increment_error()
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/generate', methods=['POST'])
@require_admin_key
def generate_license():
    try:
        data = request.get_json()
        if not data or 'expires_at' not in data or 'hwid' not in data:
            stats.increment_error()
            return jsonify({"error": "Missing required fields"}), 400
        
        try:
            datetime.strptime(data['expires_at'], "%Y-%m-%d")
        except ValueError:
            stats.increment_error()
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        license_key = generate_license_key()
        plan = data.get('plan', 'basic')
        
        if db.add_license(license_key, data['hwid'], data['expires_at'], plan):
            return jsonify({
                "key": license_key,
                "expires_at": data['expires_at']
            })
        else:
            stats.increment_error()
            return jsonify({"error": "Failed to generate license"}), 500
            
    except Exception as e:
        stats.increment_error()
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/delete', methods=['DELETE'])
@require_admin_key
def delete_license():
    try:
        data = request.get_json()
        if not data or 'key' not in data:
            stats.increment_error()
            return jsonify({"error": "Missing license key"}), 400
        
        if db.delete_license(data['key']):
            return jsonify({"message": "successfully deleted"})
        else:
            stats.increment_error()
            return jsonify({"error": "License key not found"}), 404
            
    except Exception as e:
        stats.increment_error()
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/resethwid', methods=['PATCH'])
@require_admin_key
def reset_hwid():
    try:
        data = request.get_json()
        if not data or 'key' not in data:
            stats.increment_error()
            return jsonify({"error": "Missing license key"}), 400
        
        if db.reset_hwid(data['key']):
            return jsonify({"hwid": None})
        else:
            stats.increment_error()
            return jsonify({"error": "License key not found"}), 404
            
    except Exception as e:
        stats.increment_error()
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/keyinfo', methods=['GET'])
@require_admin_key
def get_key_info():
    try:
        license_key = request.args.get('key')
        if not license_key:
            stats.increment_error()
            return jsonify({"error": "Missing license key parameter"}), 400
        
        usage_info = db.get_usage_info(license_key)
        if not usage_info:
            return jsonify({"message": "no key info"})
        
        return jsonify(usage_info)
        
    except Exception as e:
        stats.increment_error()
        return jsonify({"error": "Internal server error"}), 500

def create_dashboard():
    layout = Layout()
    
    layout.split_column(
        Layout(name="header", size=8),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3)
    )
    
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    
    return layout

def update_dashboard(layout):
    current_stats = stats.get_stats()
    cpu_serial = SystemInfo.get_cpu_serial()
    
    header_text = Text("🔐 License Key Authentication API Server", style="bold blue")
    header_panel = Panel(
        header_text,
        box=box.DOUBLE,
        style="bright_blue"
    )
    layout["header"].update(header_panel)

    system_table = Table(show_header=False, box=box.ROUNDED)
    system_table.add_column("Property", style="cyan")
    system_table.add_column("Value", style="green")
    
    system_table.add_row("🖥️  System", f"{platform.system()} {platform.release()}")
    system_table.add_row("🔧 CPU Serial", cpu_serial)
    system_table.add_row("🌐 Host", "localhost:5000")
    system_table.add_row("⏰ Started", stats.start_time.strftime("%Y-%m-%d %H:%M:%S"))
    system_table.add_row("📊 Uptime", current_stats["uptime"])
    
    system_panel = Panel(
        system_table,
        title="[bold]System Information[/bold]",
        border_style="green"
    )
    layout["left"].update(system_panel)

    stats_table = Table(show_header=False, box=box.ROUNDED)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="yellow")
    
    stats_table.add_row("📈 Total Requests", str(current_stats["total_requests"]))
    stats_table.add_row("✅ Verify Requests", str(current_stats["verify_requests"]))
    stats_table.add_row("🔧 Admin Requests", str(current_stats["admin_requests"]))
    stats_table.add_row("❌ Errors", str(current_stats["error_count"]))
    stats_table.add_row("📊 Success Rate", current_stats["success_rate"])
    
    stats_panel = Panel(
        stats_table,
        title="[bold]API Statistics[/bold]",
        border_style="yellow"
    )
    layout["right"].update(stats_panel)
    
    admin_key_text = Text(f"🔑 Admin Key: {admin_key}", style="bold red")
    footer_panel = Panel(
        admin_key_text,
        title="[bold red]⚠️  CONFIDENTIAL ⚠️[/bold red]",
        border_style="red"
    )
    layout["footer"].update(footer_panel)

def run_dashboard():
    layout = create_dashboard()
    
    with Live(layout, refresh_per_second=1, screen=True):
        while True:
            update_dashboard(layout)
            time.sleep(1)

if __name__ == '__main__':
    console.print(Panel.fit(
        "[bold blue]🔐 License Key Authentication API[/bold blue]\n"
        "[yellow]Initializing secure license validation system...[/yellow]",
        border_style="blue"
    ))
    
    console.print(Panel(
        f"[bold red]Admin Key: {admin_key}[/bold red]\n"
        "[yellow]⚠️  Keep this key secure! Use it in Authorization: Bearer <key>[/yellow]",
        title="[bold red]Admin Authentication[/bold red]",
        border_style="red"
    ))

    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server shutting down...[/yellow]")
