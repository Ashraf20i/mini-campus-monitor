"""
Configuration du projet de supervision réseau.
Centralise les hôtes à superviser, les seuils, et les paramètres d'exécution.
"""

# --- HÔTES À SUPERVISER ---
HOSTS = {
    "srv-admin": "192.168.56.10",
    "srv-biblio": "192.168.56.11",
}

# --- PARAMÈTRES DE SUPERVISION ---
POLL_INTERVAL = 5
PING_TIMEOUT = 1

# --- PARAMÈTRES DE DÉTECTION D'ANOMALIES ---
FAILURE_THRESHOLD = 3
LATENCY_THRESHOLD_MS = 200

# --- CHEMINS DE FICHIERS ---
METRICS_FILE = "data/metrics.csv"
ALERTS_FILE = "data/alerts.csv"
DATABASE_FILE = "data/monitoring.db"   # ← nouvelle ligne