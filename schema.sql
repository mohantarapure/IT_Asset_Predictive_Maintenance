PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS asset_categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS assets (
    asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES asset_categories(category_id) ON DELETE RESTRICT,
    asset_name TEXT NOT NULL,
    asset_tag TEXT NOT NULL UNIQUE,
    manufacturer TEXT,
    model TEXT,
    purchase_date TEXT NOT NULL,
    warranty_expiry TEXT,
    location TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('Active','Under Maintenance','Retired')) DEFAULT 'Active',
    criticality TEXT NOT NULL CHECK(criticality IN ('Low','Medium','High')) DEFAULT 'Medium',
    installation_date TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS maintenance_records (
    maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
    maintenance_type TEXT NOT NULL CHECK(maintenance_type IN ('Preventive','Corrective','Emergency')),
    maintenance_date TEXT NOT NULL,
    description TEXT NOT NULL,
    technician TEXT NOT NULL,
    cost REAL NOT NULL DEFAULT 0 CHECK(cost >= 0),
    downtime_hours REAL NOT NULL DEFAULT 0 CHECK(downtime_hours >= 0),
    status TEXT NOT NULL CHECK(status IN ('Scheduled','Completed','Pending')) DEFAULT 'Completed',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS failure_records (
    failure_id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
    failure_date TEXT NOT NULL,
    failure_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('Low','Medium','High','Critical')),
    downtime_hours REAL NOT NULL DEFAULT 0 CHECK(downtime_hours >= 0),
    repair_cost REAL NOT NULL DEFAULT 0 CHECK(repair_cost >= 0),
    description TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS maintenance_schedule (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
    scheduled_date TEXT NOT NULL,
    maintenance_type TEXT NOT NULL CHECK(maintenance_type IN ('Preventive','Corrective','Emergency')),
    notes TEXT,
    status TEXT NOT NULL CHECK(status IN ('Scheduled','Completed','Pending')) DEFAULT 'Scheduled'
);
CREATE TABLE IF NOT EXISTS asset_readings (
    reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
    reading_date TEXT NOT NULL,
    cpu_usage REAL NOT NULL CHECK(cpu_usage BETWEEN 0 AND 100),
    memory_usage REAL NOT NULL CHECK(memory_usage BETWEEN 0 AND 100),
    temperature REAL NOT NULL CHECK(temperature >= 0),
    disk_usage REAL NOT NULL CHECK(disk_usage BETWEEN 0 AND 100),
    uptime_hours REAL NOT NULL CHECK(uptime_hours >= 0),
    error_count INTEGER NOT NULL CHECK(error_count >= 0)
);
CREATE TABLE IF NOT EXISTS deleted_asset_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    asset_tag TEXT NOT NULL,
    deleted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_assets_user ON assets(user_id);
CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(category_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_asset ON maintenance_records(asset_id);
CREATE INDEX IF NOT EXISTS idx_failures_asset ON failure_records(asset_id);
CREATE INDEX IF NOT EXISTS idx_readings_asset ON asset_readings(asset_id);

DROP VIEW IF EXISTS asset_maintenance_summary;
CREATE VIEW asset_maintenance_summary AS
SELECT a.asset_id, a.asset_name, a.asset_tag, c.category_name,
       COUNT(DISTINCT m.maintenance_id) AS maintenance_count,
       COUNT(DISTINCT f.failure_id) AS failure_count,
       COALESCE(SUM(DISTINCT m.cost),0) AS total_maintenance_cost,
       COALESCE(SUM(DISTINCT m.downtime_hours),0) + COALESCE(SUM(DISTINCT f.downtime_hours),0) AS total_downtime
FROM assets a JOIN asset_categories c ON c.category_id=a.category_id
LEFT JOIN maintenance_records m ON m.asset_id=a.asset_id
LEFT JOIN failure_records f ON f.asset_id=a.asset_id
GROUP BY a.asset_id;

DROP TRIGGER IF EXISTS log_deleted_asset;
CREATE TRIGGER log_deleted_asset AFTER DELETE ON assets
BEGIN INSERT INTO deleted_asset_log(asset_id, asset_tag) VALUES (OLD.asset_id, OLD.asset_tag); END;
