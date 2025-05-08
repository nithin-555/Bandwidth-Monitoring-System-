from flask import Flask, render_template, jsonify, request
import psutil
import sqlite3
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import pandas as pd
import threading
import time
import warnings
import os
import platform
import subprocess
import re
from collections import defaultdict

# Suppress warnings
warnings.filterwarnings("ignore", message="Matplotlib is building the font cache")

app = Flask(__name__)

# Configuration
UPDATE_INTERVAL = 5  # seconds
ALERT_THRESHOLD = 100 * 1024 * 1024  # 100 MB
MAX_LOG_DAYS = 30

# Global variables
current_usage = {
    'bytes_sent': 0,
    'bytes_recv': 0,
    'total': 0,
    'interfaces': {},
    'devices': {},
    'applications': {}
}

# Known applications
KNOWN_APPS = {
    'netflix': 'Netflix',
    'zoom': 'Zoom',
    'bittorrent': 'BitTorrent',
    'utorrent': 'uTorrent',
    'chrome': 'Chrome',
    'firefox': 'Firefox',
    'msedge': 'Edge',
    'teams': 'Microsoft Teams',
    'slack': 'Slack',
    'spotify': 'Spotify'
}

# SQLite datetime handling
def adapt_datetime_iso(val):
    return val.isoformat()

def convert_datetime_iso(val):
    return datetime.fromisoformat(val.decode())

sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_converter("datetime", convert_datetime_iso)

def get_db_connection():
    conn = sqlite3.connect(
        'bandwidth.db',
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    conn.row_factory = sqlite3.Row
    return conn

def get_mac_address(ip):
    try:
        if platform.system() == "Windows":
            arp_output = subprocess.check_output(["arp", "-a", ip], stderr=subprocess.DEVNULL)
            match = re.search(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", arp_output.decode())
            return match.group(0) if match else "00:00:00:00:00:00"
        return "00:00:00:00:00:00"
    except:
        return "00:00:00:00:00:00"

def get_application_name(process_name):
    lower_name = process_name.lower()
    for key, value in KNOWN_APPS.items():
        if key in lower_name:
            return value
    return process_name

def track_device_usage():
    device_stats = defaultdict(lambda: {'sent': 0, 'recv': 0, 'apps': defaultdict(int)})
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == psutil.CONN_ESTABLISHED and conn.raddr:
                ip = conn.raddr.ip
                try:
                    proc = psutil.Process(conn.pid)
                    app_name = get_application_name(proc.name())
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    app_name = "Unknown"
                
                device_stats[ip]['sent'] += getattr(conn, 'bytes_sent', 0)
                device_stats[ip]['recv'] += getattr(conn, 'bytes_recv', 0)
                device_stats[ip]['apps'][app_name] += getattr(conn, 'bytes_sent', 0) + getattr(conn, 'bytes_recv', 0)
                device_stats[ip]['mac'] = get_mac_address(ip)
    except Exception as e:
        print(f"Device tracking error: {e}")
    return device_stats

def track_application_usage():
    app_stats = defaultdict(lambda: {'sent': 0, 'recv': 0})
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                # Get connections for this process
                conns = proc.connections()
                app_name = get_application_name(proc.info['name'])
                
                for conn in conns:
                    if conn.status == psutil.CONN_ESTABLISHED:
                        app_stats[app_name]['sent'] += getattr(conn, 'bytes_sent', 0)
                        app_stats[app_name]['recv'] += getattr(conn, 'bytes_recv', 0)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                print(f"Error processing process {proc.pid}: {str(e)}")
                continue
    except Exception as e:
        print(f"Application tracking error: {e}")
    return app_stats

def purge_old_data():
    cutoff_date = datetime.now() - timedelta(days=MAX_LOG_DAYS)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bandwidth_usage WHERE timestamp < ?", (adapt_datetime_iso(cutoff_date),))
        cursor.execute("DELETE FROM alerts WHERE timestamp < ?", (adapt_datetime_iso(cutoff_date),))
        cursor.execute("DELETE FROM device_usage WHERE timestamp < ?", (adapt_datetime_iso(cutoff_date),))
        cursor.execute("DELETE FROM application_usage WHERE timestamp < ?", (adapt_datetime_iso(cutoff_date),))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error purging old data: {e}")

def log_bandwidth():
    global current_usage
    
    while True:
        try:
            timestamp = datetime.now()
            
            # Track interface usage
            net_io = psutil.net_io_counters(pernic=True)
            total_sent = 0
            total_recv = 0
            interfaces = {}
            
            for interface, stats in net_io.items():
                interfaces[interface] = {
                    'bytes_sent': stats.bytes_sent,
                    'bytes_recv': stats.bytes_recv
                }
                total_sent += stats.bytes_sent
                total_recv += stats.bytes_recv
            
            # Track devices and applications
            device_stats = track_device_usage()
            app_stats = track_application_usage()
            
            # Update global state
            current_usage = {
                'bytes_sent': total_sent,
                'bytes_recv': total_recv,
                'total': total_sent + total_recv,
                'interfaces': interfaces,
                'devices': device_stats,
                'applications': app_stats
            }
            
            # Store in database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Interface usage
            for interface, stats in interfaces.items():
                cursor.execute('''
                    INSERT INTO bandwidth_usage 
                    (timestamp, interface, bytes_sent, bytes_received, total_bytes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (adapt_datetime_iso(timestamp), interface, 
                     stats['bytes_sent'], stats['bytes_recv'], 
                     stats['bytes_sent'] + stats['bytes_recv']))
            
            # Device usage
            for ip, stats in device_stats.items():
                top_app = max(stats['apps'].items(), key=lambda x: x[1])[0] if stats['apps'] else 'Unknown'
                cursor.execute('''
                    INSERT INTO device_usage 
                    (timestamp, ip_address, mac_address, bytes_sent, bytes_received, top_application)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (adapt_datetime_iso(timestamp), ip, stats.get('mac', ''), 
                     stats['sent'], stats['recv'], top_app))
            
            # Application usage
            for app, stats in app_stats.items():
                cursor.execute('''
                    INSERT INTO application_usage 
                    (timestamp, application_name, bytes_sent, bytes_received)
                    VALUES (?, ?, ?, ?)
                ''', (adapt_datetime_iso(timestamp), app, stats['sent'], stats['recv']))
            
            # Check for alerts
            if (total_sent + total_recv) > ALERT_THRESHOLD:
                cursor.execute('''
                    INSERT INTO alerts (timestamp, message, threshold, actual_value)
                    VALUES (?, ?, ?, ?)
                ''', (adapt_datetime_iso(timestamp), 'High bandwidth usage detected', 
                     ALERT_THRESHOLD, total_sent + total_recv))
            
            conn.commit()
            conn.close()
            
            # Purge old data periodically
            if time.localtime().tm_min % 10 == 0:
                purge_old_data()
            
            time.sleep(UPDATE_INTERVAL)
        except Exception as e:
            print(f"Monitoring error: {e}")
            time.sleep(10)

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/current_usage')
def get_current_usage():
    return jsonify(current_usage)

@app.route('/api/historical')
def get_historical():
    time_range = request.args.get('range', '1h')  # 1h, 24h, 7d
    interface = request.args.get('interface', 'all')
    
    now = datetime.now()
    
    if time_range == '1h':
        start_time = now - timedelta(hours=1)
    elif time_range == '24h':
        start_time = now - timedelta(days=1)
    else:  # 7d
        start_time = now - timedelta(days=7)
    
    conn = get_db_connection()
    
    if interface == 'all':
        cursor = conn.execute('''
            SELECT timestamp as "[datetime]",
                   SUM(bytes_sent) as sent, 
                   SUM(bytes_received) as received
            FROM bandwidth_usage
            WHERE timestamp >= ?
            GROUP BY strftime('%Y-%m-%d %H:%M', timestamp)
            ORDER BY timestamp
        ''', (adapt_datetime_iso(start_time),))
    else:
        cursor = conn.execute('''
            SELECT timestamp as "[datetime]",
                   bytes_sent as sent, 
                   bytes_received as received
            FROM bandwidth_usage
            WHERE timestamp >= ? AND interface = ?
            ORDER BY timestamp
        ''', (adapt_datetime_iso(start_time), interface))
    
    data = cursor.fetchall()
    conn.close()
    
    result = {
        'times': [row[0].isoformat() for row in data],
        'sent': [row[1] for row in data],
        'received': [row[2] for row in data]
    }
    
    return jsonify(result)

@app.route('/api/top_interfaces')
def get_top_interfaces():
    conn = get_db_connection()
    cursor = conn.execute('''
        SELECT interface, SUM(total_bytes) as total
        FROM bandwidth_usage
        WHERE timestamp >= datetime('now', '-1 day')
        GROUP BY interface
        ORDER BY total DESC
        LIMIT 5
    ''')
    
    data = cursor.fetchall()
    conn.close()
    
    result = {
        'interfaces': [row['interface'] for row in data],
        'totals': [row['total'] for row in data]
    }
    
    return jsonify(result)

@app.route('/api/device_usage')
def get_device_usage_api():
    time_range = request.args.get('range', '1h')
    limit = min(int(request.args.get('limit', '10')), 50)
    
    now = datetime.now()
    if time_range == '1h':
        start_time = now - timedelta(hours=1)
    elif time_range == '24h':
        start_time = now - timedelta(days=1)
    else:
        start_time = now - timedelta(days=7)
    
    conn = get_db_connection()
    cursor = conn.execute('''
        SELECT ip_address, mac_address, 
               SUM(bytes_sent) as sent, 
               SUM(bytes_received) as received,
               top_application
        FROM device_usage
        WHERE timestamp >= ?
        GROUP BY ip_address
        ORDER BY sent + received DESC
        LIMIT ?
    ''', (adapt_datetime_iso(start_time), limit))
    
    devices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(devices)

@app.route('/api/application_usage')
def get_application_usage_api():
    time_range = request.args.get('range', '1h')
    limit = min(int(request.args.get('limit', '10')), 50)
    
    now = datetime.now()
    if time_range == '1h':
        start_time = now - timedelta(hours=1)
    elif time_range == '24h':
        start_time = now - timedelta(days=1)
    else:
        start_time = now - timedelta(days=7)
    
    conn = get_db_connection()
    cursor = conn.execute('''
        SELECT application_name, 
               SUM(bytes_sent) as sent, 
               SUM(bytes_received) as received
        FROM application_usage
        WHERE timestamp >= ?
        GROUP BY application_name
        ORDER BY sent + received DESC
        LIMIT ?
    ''', (adapt_datetime_iso(start_time), limit))
    
    apps = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(apps)

@app.route('/api/device_details/<ip>')
def get_device_details(ip):
    time_range = request.args.get('range', '1h')
    
    now = datetime.now()
    if time_range == '1h':
        start_time = now - timedelta(hours=1)
    elif time_range == '24h':
        start_time = now - timedelta(days=1)
    else:
        start_time = now - timedelta(days=7)
    
    conn = get_db_connection()
    
    # Get device summary
    cursor = conn.execute('''
        SELECT ip_address, mac_address, 
               SUM(bytes_sent) as sent, 
               SUM(bytes_received) as received
        FROM device_usage
        WHERE ip_address = ? AND timestamp >= ?
        GROUP BY ip_address
    ''', (ip, adapt_datetime_iso(start_time)))
    
    device = dict(cursor.fetchone()) if cursor.rowcount > 0 else None
    
    # Get top applications
    cursor = conn.execute('''
        SELECT top_application as application, 
               SUM(bytes_sent + bytes_received) as total_bytes
        FROM device_usage
        WHERE ip_address = ? AND timestamp >= ?
        GROUP BY top_application
        ORDER BY total_bytes DESC
        LIMIT 5
    ''', (ip, adapt_datetime_iso(start_time)))
    
    apps = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    device['applications'] = apps
    return jsonify(device)

@app.route('/api/alerts')
def get_alerts():
    resolved = request.args.get('resolved', 'false').lower() == 'true'
    
    conn = get_db_connection()
    cursor = conn.execute('''
        SELECT id, timestamp as "[datetime]", message, threshold, actual_value, resolved
        FROM alerts
        WHERE resolved = ?
        ORDER BY timestamp DESC
        LIMIT 10
    ''', (1 if resolved else 0,))
    
    alerts = []
    for row in cursor.fetchall():
        alert = dict(row)
        alert['timestamp'] = row[1].isoformat()  # Convert datetime to string
        alerts.append(alert)
    conn.close()
    
    return jsonify(alerts)

@app.route('/api/resolve_alert/<int:alert_id>', methods=['POST'])
def resolve_alert(alert_id):
    conn = get_db_connection()
    conn.execute('''
        UPDATE alerts
        SET resolved = 1
        WHERE id = ?
    ''', (alert_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/api/usage_report')
def get_usage_report():
    # Generate a matplotlib plot
    conn = get_db_connection()
    
    # Get last 24 hours data
    cursor = conn.execute('''
        SELECT timestamp as "[datetime]",
               SUM(bytes_sent) as sent,
               SUM(bytes_received) as received
        FROM bandwidth_usage
        WHERE timestamp >= datetime('now', '-1 day')
        GROUP BY strftime('%Y-%m-%d %H:00', timestamp)
        ORDER BY timestamp
    ''')
    
    data = cursor.fetchall()
    conn.close()
    
    if not data:
        return jsonify({'error': 'No data available'})
    
    times = [row[0] for row in data]
    sent = [row[1] for row in data]
    received = [row[2] for row in data]
    
    plt.figure(figsize=(10, 5))
    plt.plot(times, [s / (1024 * 1024) for s in sent], label='Sent (MB)')
    plt.plot(times, [r / (1024 * 1024) for r in received], label='Received (MB)')
    plt.xlabel('Time')
    plt.ylabel('Bandwidth (MB)')
    plt.title('Bandwidth Usage Last 24 Hours')
    plt.legend()
    plt.grid()
    plt.xticks(rotation=45)
    
    # Save plot to a bytes buffer
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    # Encode plot image
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    
    return jsonify({'image': image_base64})

if __name__ == '__main__':
    # Initialize database
    from models import init_db
    init_db()
    
    # Start bandwidth monitoring thread
    monitor_thread = threading.Thread(target=log_bandwidth, daemon=True)
    
    # Configure Flask to not start the monitor thread twice in debug mode
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        monitor_thread.start()
    
    app.run(debug=True)