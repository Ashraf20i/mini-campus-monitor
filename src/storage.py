"""
Module de stockage SQLite.

Gère la persistance des métriques et des alertes dans une base SQLite locale.
Encapsule toute la logique SQL pour que le reste du projet n'ait pas à
manipuler directement la base.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager

from src.config import DATABASE_FILE

# Chemin racine du projet (calculé dynamiquement)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / DATABASE_FILE


# --- SCHÉMA DE LA BASE ---

CREATE_METRICS_TABLE = """
CREATE TABLE IF NOT EXISTS metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    host        TEXT NOT NULL,
    ip          TEXT NOT NULL,
    status      TEXT NOT NULL,
    latency_ms  REAL
);
"""

CREATE_ALERTS_TABLE = """
CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    host        TEXT NOT NULL,
    ip          TEXT NOT NULL,
    type        TEXT NOT NULL,
    severity    TEXT NOT NULL,
    message     TEXT NOT NULL
);
"""

# Index pour accélérer les requêtes les plus fréquentes (filtrage par host/timestamp)
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_metrics_host ON metrics(host);",
    "CREATE INDEX IF NOT EXISTS idx_metrics_ts   ON metrics(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_host  ON alerts(host);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_ts    ON alerts(timestamp);",
]


# --- GESTION DE LA CONNEXION ---

@contextmanager
def get_connection():
    """
    Context manager pour ouvrir/fermer proprement la connexion SQLite.

    Usage:
        with get_connection() as conn:
            conn.execute(...)
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Pour récupérer les résultats sous forme de dict
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """
    Crée les tables et les index si la base n'existe pas encore.
    Idempotent : peut être appelé plusieurs fois sans risque.
    """
    with get_connection() as conn:
        conn.execute(CREATE_METRICS_TABLE)
        conn.execute(CREATE_ALERTS_TABLE)
        for index_sql in CREATE_INDEXES:
            conn.execute(index_sql)


# --- INSERTIONS ---

def insert_metric(timestamp: str, host: str, ip: str, status: str, latency_ms: float | None) -> None:
    """Insère une mesure dans la table metrics."""
    sql = """
    INSERT INTO metrics (timestamp, host, ip, status, latency_ms)
    VALUES (?, ?, ?, ?, ?);
    """
    with get_connection() as conn:
        conn.execute(sql, (timestamp, host, ip, status, latency_ms))


def insert_alert(alert: dict) -> None:
    """Insère une alerte (dict produit par le détecteur) dans la table alerts."""
    sql = """
    INSERT INTO alerts (timestamp, host, ip, type, severity, message)
    VALUES (?, ?, ?, ?, ?, ?);
    """
    with get_connection() as conn:
        conn.execute(sql, (
            alert["timestamp"],
            alert["host"],
            alert["ip"],
            alert["type"],
            alert["severity"],
            alert["message"],
        ))


# --- LECTURES (utiles pour le dashboard plus tard) ---

def get_recent_metrics(host: str | None = None, limit: int = 100) -> list[dict]:
    """
    Retourne les dernières mesures.

    Args:
        host: si fourni, filtre par hôte. Sinon, tous les hôtes.
        limit: nombre maximum de lignes à retourner.

    Returns:
        Liste de dicts (timestamp, host, ip, status, latency_ms).
    """
    if host:
        sql = "SELECT * FROM metrics WHERE host = ? ORDER BY id DESC LIMIT ?;"
        params = (host, limit)
    else:
        sql = "SELECT * FROM metrics ORDER BY id DESC LIMIT ?;"
        params = (limit,)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def get_recent_alerts(severity: str | None = None, limit: int = 50) -> list[dict]:
    """
    Retourne les dernières alertes, optionnellement filtrées par sévérité.
    """
    if severity:
        sql = "SELECT * FROM alerts WHERE severity = ? ORDER BY id DESC LIMIT ?;"
        params = (severity, limit)
    else:
        sql = "SELECT * FROM alerts ORDER BY id DESC LIMIT ?;"
        params = (limit,)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def count_alerts_by_severity() -> dict[str, int]:
    """
    Retourne un comptage des alertes groupées par sévérité.
    Utile pour le dashboard : 'X CRITICAL, Y WARNING, Z INFO'.
    """
    sql = "SELECT severity, COUNT(*) as count FROM alerts GROUP BY severity;"
    with get_connection() as conn:
        rows = conn.execute(sql).fetchall()
        return {row["severity"]: row["count"] for row in rows}


# --- TEST ISOLÉ ---

if __name__ == "__main__":
    """
    Test minimal du module : crée la DB, insère quelques données factices,
    puis les relit pour vérifier que tout fonctionne.
    """
    print("=== Test du module storage ===\n")

    print(f"Base de données : {DB_PATH}")

    print("1. Initialisation de la base...")
    init_db()
    print("   ✓ Tables et index créés")

    print("\n2. Insertion de mesures factices...")
    insert_metric("2026-05-01T15:00:00", "test-host", "192.168.99.1", "UP", 12.5)
    insert_metric("2026-05-01T15:00:05", "test-host", "192.168.99.1", "DOWN", None)
    insert_metric("2026-05-01T15:00:10", "test-host", "192.168.99.1", "UP", 18.7)
    print("   ✓ 3 mesures insérées")

    print("\n3. Insertion d'une alerte factice...")
    insert_alert({
        "timestamp": "2026-05-01T15:00:08",
        "host": "test-host",
        "ip": "192.168.99.1",
        "type": "HOST_DOWN",
        "severity": "CRITICAL",
        "message": "Test alert from storage module",
    })
    print("   ✓ 1 alerte insérée")

    print("\n4. Lecture des mesures récentes :")
    for metric in get_recent_metrics(limit=5):
        print(f"   {metric}")

    print("\n5. Lecture des alertes récentes :")
    for alert in get_recent_alerts(limit=5):
        print(f"   {alert}")

    print("\n6. Comptage par sévérité :")
    print(f"   {count_alerts_by_severity()}")

    print("\n=== Test terminé avec succès ===")