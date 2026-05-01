"""
Configuration du projet de supervision réseau.
Centralise les hôtes à superviser, les seuils, et les paramètres d'exécution.
"""

# Liste des hôtes à superviser
# Clé = nom logique (utilisé dans les logs)
# Valeur = adresse IP dans le réseau host-only
HOSTS = {
    "srv-admin": "192.168.56.10",
    "srv-biblio": "192.168.56.11",
}

# Intervalle entre deux cycles de supervision, en secondes
POLL_INTERVAL = 5

# Timeout du ping, en secondes
PING_TIMEOUT = 1

# Chemin du fichier de log
METRICS_FILE = "data/metrics.csv"