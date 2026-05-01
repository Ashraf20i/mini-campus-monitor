"""
Module de supervision réseau.
Contient les fonctions de ping et la boucle de supervision multi-hôtes.
"""

import subprocess
import platform
import time
import csv
from datetime import datetime
from pathlib import Path

from src.config import HOSTS, POLL_INTERVAL, PING_TIMEOUT, METRICS_FILE

PROJECT_ROOT = Path(__file__).resolve().parent.parent
def ping_with_latency(ip: str, timeout: int = PING_TIMEOUT) -> tuple[bool, float | None]:
    """
    Ping un hôte et mesure la latence.

    Args:
        ip: adresse IP à tester
        timeout: délai maximum en secondes

    Returns:
        (is_alive, latency_ms)
        - is_alive: True si la machine répond
        - latency_ms: latence en millisecondes, ou None si DOWN
    """
    if platform.system().lower() == "windows":
        command = ["ping", "-n", "1", "-w", str(timeout * 1000), ip]
    else:
        command = ["ping", "-c", "1", "-W", str(timeout), ip]

    start = time.time()
    result = subprocess.run(command, capture_output=True, text=True)
    elapsed_ms = (time.time() - start) * 1000

    is_alive = result.returncode == 0
    latency = elapsed_ms if is_alive else None

    return is_alive, latency


def log_metric(timestamp: str, host: str, ip: str, status: str, latency_ms: float | None) -> None:
    """
    Écrit une ligne de mesure dans le fichier CSV.

    Crée l'en-tête si le fichier n'existe pas encore.
    """
    file_path = PROJECT_ROOT / METRICS_FILE
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = file_path.exists()

    # On ouvre en mode "append" (ajouter à la fin)
    with open(file_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Si nouveau fichier, on écrit l'en-tête
        if not file_exists:
            writer.writerow(["timestamp", "host", "ip", "status", "latency_ms"])

        # Latence formatée à 2 décimales, ou vide si DOWN
        latency_str = f"{latency_ms:.2f}" if latency_ms is not None else ""
        writer.writerow([timestamp, host, ip, status, latency_str])


def supervise_once() -> None:
    """
    Lance UN cycle de supervision : ping tous les hôtes, log les résultats.
    """
    timestamp = datetime.now().isoformat(timespec="seconds")
    print(f"\n[{timestamp}] Cycle de supervision...")

    for host, ip in HOSTS.items():
        is_alive, latency = ping_with_latency(ip)
        status = "UP" if is_alive else "DOWN"

        if is_alive:
            print(f"  {host:12} ({ip}) → {status} ({latency:.2f} ms)")
        else:
            print(f"  {host:12} ({ip}) → {status}")

        log_metric(timestamp, host, ip, status, latency)


def supervise_loop() -> None:
    """
    Boucle infinie de supervision. Ctrl+C pour arrêter.
    """
    print(f"Démarrage de la supervision (intervalle: {POLL_INTERVAL}s)")
    print(f"Hôtes supervisés: {list(HOSTS.keys())}")
    print(f"Logs écrits dans: {METRICS_FILE}")
    print("Ctrl+C pour arrêter\n")

    try:
        while True:
            supervise_once()
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n\nSupervision arrêtée par l'utilisateur.")


# Point d'entrée
if __name__ == "__main__":
    supervise_loop()