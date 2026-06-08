import json
import sqlite3
import time
from pathlib import Path


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  wechat_union_id TEXT,
  wechat_open_id TEXT,
  nickname TEXT NOT NULL DEFAULT '',
  avatar_url TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'active',
  created_at INTEGER NOT NULL,
  last_login_at INTEGER
);

CREATE INDEX IF NOT EXISTS idx_users_wechat_union
ON users(wechat_union_id);

CREATE INDEX IF NOT EXISTS idx_users_wechat_open
ON users(wechat_open_id);

CREATE TABLE IF NOT EXISTS wechat_identities (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  union_id TEXT,
  open_id TEXT NOT NULL,
  raw_json TEXT NOT NULL DEFAULT '{}',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS desktop_login_nonces (
  nonce TEXT PRIMARY KEY,
  state TEXT NOT NULL UNIQUE,
  device_id TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending',
  user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  completed_at INTEGER
);

CREATE TABLE IF NOT EXISTS desktop_sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  device_id TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  revoked_at INTEGER
);

CREATE TABLE IF NOT EXISTS tenants (
  id TEXT PRIMARY KEY,
  profile TEXT NOT NULL,
  display_name TEXT NOT NULL,
  gateway_url TEXT NOT NULL,
  auth_mode TEXT NOT NULL DEFAULT 'ticket',
  features_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'active',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS tenant_memberships (
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_by TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY(user_id, tenant_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_user_id TEXT,
  tenant_id TEXT,
  action TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at INTEGER NOT NULL
);
"""


class Database:
    def __init__(self, path: str):
        self.path = path
        db_path = Path(path)
        if db_path.parent and str(db_path.parent) != ".":
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def execute(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def query_one(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def query_all(self, sql, params=()):
        return list(self.conn.execute(sql, params).fetchall())

    def audit(self, action, actor_user_id=None, tenant_id=None, **metadata):
        self.execute(
            "INSERT INTO audit_events(actor_user_id, tenant_id, action, metadata_json, created_at) VALUES(?,?,?,?,?)",
            (actor_user_id, tenant_id, action, json.dumps(metadata, ensure_ascii=False, sort_keys=True), now()),
        )


def now() -> int:
    return int(time.time())


def row_to_tenant(row, role=None):
    features = json.loads(row["features_json"] or "{}")
    value = {
        "id": row["id"],
        "profile": row["profile"],
        "displayName": row["display_name"],
        "gatewayUrl": row["gateway_url"],
        "authMode": row["auth_mode"],
        "features": features,
    }
    if role:
        value["role"] = role
    return value
