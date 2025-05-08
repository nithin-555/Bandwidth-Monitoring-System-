import sqlite3
from datetime import datetime

def adapt_datetime_iso(val):
    """Adapt datetime.datetime to ISO 8601 date."""
    return val.isoformat()

def convert_datetime_iso(val):
    """Convert ISO 8601 datetime to datetime.datetime object."""
    return datetime.fromisoformat(val.decode())

# Register the adapter and converter
sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_converter("datetime", convert_datetime_iso)

def init_db():
    conn = sqlite3.connect(
        'bandwidth.db',
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    cursor = conn.cursor()
    
    # Bandwidth usage by interface
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bandwidth_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        interface TEXT NOT NULL,
        bytes_sent INTEGER NOT NULL,
        bytes_received INTEGER NOT NULL,
        total_bytes INTEGER NOT NULL
    )
    ''')
    
    # Alerts table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        message TEXT NOT NULL,
        threshold INTEGER NOT NULL,
        actual_value INTEGER NOT NULL,
        resolved BOOLEAN DEFAULT 0
    )
    ''')
    
    # Device usage tracking
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS device_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        ip_address TEXT NOT NULL,
        mac_address TEXT,
        bytes_sent INTEGER NOT NULL,
        bytes_received INTEGER NOT NULL,
        top_application TEXT
    )
    ''')
    
    # Application usage tracking
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS application_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        application_name TEXT NOT NULL,
        protocol TEXT,
        port INTEGER,
        bytes_sent INTEGER NOT NULL,
        bytes_received INTEGER NOT NULL
    )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bw_timestamp ON bandwidth_usage(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bw_interface ON bandwidth_usage(interface)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_timestamp ON device_usage(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_ip ON device_usage(ip_address)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_app_timestamp ON application_usage(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_app_name ON application_usage(application_name)')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()