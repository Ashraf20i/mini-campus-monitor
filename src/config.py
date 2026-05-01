"""
Configuration du projet de supervision réseau.
Centralise les hôtes à superviser, les seuils, et les paramètres d'exécution.
"""

# --- HÔTES À SUPERVISER ---
# Clé = nom logique (utilisé dans les logs)
# Valeur = adresse IP dans le réseau host-only
HOSTS = {
    "srv-admin": "192.168.56.10",
    "srv-biblio": "192.168.56.11",
}

# --- PARAMÈTRES DE SUPERVISION ---

# Intervalle entre deux cycles de supervision, en secondes
POLL_INTERVAL = 5

# Timeout du ping, en secondes
PING_TIMEOUT = 1

# --- PARAMÈTRES DE DÉTECTION D'ANOMALIES ---

# Nombre d'échecs consécutifs avant déclenchement d'une alerte HOST_DOWN
FAILURE_THRESHOLD = 3

# Latence (en ms) au-delà de laquelle on déclenche une alerte HIGH_LATENCY
LATENCY_THRESHOLD_MS = 200

# --- CHEMINS DE FICHIERS ---

# Chemin du fichier de log des métriques (relatif à la racine du projet)
METRICS_FILE = "data/metrics.csv"

# Chemin du fichier de log des alertes (relatif à la racine du projet)
ALERTS_FILE = "data/alerts.csv"