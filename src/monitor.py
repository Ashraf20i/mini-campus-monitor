"""
Module de supervision réseau.
Contient les fonctions de ping, la boucle de supervision, et l'intégration
avec le détecteur d'anomalies.
"""

import subprocess
import platform
import time
import csv
from datetime import datetime
from pathlib import Path

from src.config import (
    HOSTS,
    POLL_INTERVAL,
    PING_TIMEOUT,
    METRICS_FILE,
    ALERTS_FILE,
)
from src.detector import AnomalyDetector

# Chemin racine du projet (calculé dynamiquement)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def ping_with_latency(ip: str, timeout: int = PING_TIMEOUT) -> tuple[bool, float | None]:
    """
    Ping un hôte et mesure la latence.

    Returns:
        (is_alive, latency_ms)
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
    """Écrit une ligne de mesure dans le fichier CSV des métriques."""
    file_path = PROJECT_ROOT / METRICS_FILE
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = file_path.exists()

    with open(file_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "host", "ip", "status", "latency_ms"])
        latency_str = f"{latency_ms:.2f}" if latency_ms is not None else ""
        writer.writerow([timestamp, host, ip, status, latency_str])


def log_alert(alert: dict) -> None:
    """Écrit une alerte dans le fichier CSV des alertes."""
    file_path = PROJECT_ROOT / ALERTS_FILE
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = file_path.exists()

    with open(file_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "host", "ip", "type", "severity", "message"])
        writer.writerow([
            alert["timestamp"],
            alert["host"],
            alert["ip"],
            alert["type"],
            alert["severity"],
            alert["message"],
        ])


def format_alert_console(alert: dict) -> str:
    """Formate une alerte pour affichage dans la console."""
    severity_icons = {
        "CRITICAL": "🔴",
        "WARNING": "🟡",
        "INFO": "🟢",
    }
    icon = severity_icons.get(alert["severity"], "⚠")
    return f"     {icon} [{alert['severity']}] {alert['type']}: {alert['message']}"


def supervise_once(detector: AnomalyDetector) -> None:
    """
    Lance UN cycle de supervision : ping tous les hôtes, log, et évaluation
    par le détecteur.
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

        # Log de la métrique brute
        log_metric(timestamp, host, ip, status, latency)

        # Évaluation par le détecteur d'anomalies
        alerts = detector.evaluate(host, ip, is_alive, latency)
        for alert in alerts:
            print(format_alert_console(alert))
            log_alert(alert)


def supervise_loop() -> None:
    """Boucle infinie de supervision. Ctrl+C pour arrêter."""
    print(f"Démarrage de la supervision (intervalle: {POLL_INTERVAL}s)")
    print(f"Hôtes supervisés: {list(HOSTS.keys())}")
    print(f"Métriques écrites dans: {PROJECT_ROOT / METRICS_FILE}")
    print(f"Alertes écrites dans: {PROJECT_ROOT / ALERTS_FILE}")
    print("Ctrl+C pour arrêter\n")

    # Le détecteur est créé UNE SEULE FOIS, en dehors de la boucle.
    # C'est lui qui maintient l'état entre les cycles.
    detector = AnomalyDetector()

    try:
        while True:
            supervise_once(detector)
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n\nSupervision arrêtée par l'utilisateur.")
        print("\nÉtat final du détecteur :")
        for host, state in detector.get_state().items():
            print(f"  {host}: {state}")


if __name__ == "__main__":
    supervise_loop()