"""
Module de détection d'anomalies.

Analyse les résultats de supervision et génère des alertes selon des règles
configurables. Maintient un état par hôte pour détecter les pannes
consécutives et les retours en service.
"""

from datetime import datetime
from src.config import FAILURE_THRESHOLD, LATENCY_THRESHOLD_MS


class AnomalyDetector:
    """
    Détecteur d'anomalies à état.

    Pour chaque hôte supervisé, maintient :
    - Le nombre d'échecs consécutifs en cours
    - Le dernier statut connu (UP / DOWN / UNKNOWN)
    - Si une alerte HOST_DOWN a déjà été émise (pour éviter le spam)
    """

    def __init__(self):
        # État par hôte : {host_name: {...}}
        self._state: dict[str, dict] = {}

    def _ensure_host(self, host: str) -> None:
        """Initialise l'état d'un hôte s'il n'existe pas encore."""
        if host not in self._state:
            self._state[host] = {
                "consecutive_failures": 0,
                "last_status": "UNKNOWN",
                "down_alert_sent": False,
            }

    def evaluate(
        self,
        host: str,
        ip: str,
        is_alive: bool,
        latency_ms: float | None,
    ) -> list[dict]:
        """
        Évalue les règles pour un hôte donné.

        Args:
            host: nom logique de l'hôte (ex: "srv-admin")
            ip: adresse IP de l'hôte
            is_alive: True si l'hôte a répondu au ping
            latency_ms: latence en ms, ou None si DOWN

        Returns:
            Liste des alertes générées (peut être vide).
        """
        self._ensure_host(host)
        state = self._state[host]
        alerts: list[dict] = []
        timestamp = datetime.now().isoformat(timespec="seconds")

        if is_alive:
            # --- L'hôte répond ---

            # Règle 2 : HOST_RECOVERED
            # Si l'hôte était DOWN et qu'on avait alerté, on signale le retour
            if state["down_alert_sent"]:
                alerts.append({
                    "timestamp": timestamp,
                    "host": host,
                    "ip": ip,
                    "type": "HOST_RECOVERED",
                    "severity": "INFO",
                    "message": f"Host {host} is UP again after a DOWN period",
                })
                state["down_alert_sent"] = False

            # Règle 3 : HIGH_LATENCY
            if latency_ms is not None and latency_ms > LATENCY_THRESHOLD_MS:
                alerts.append({
                    "timestamp": timestamp,
                    "host": host,
                    "ip": ip,
                    "type": "HIGH_LATENCY",
                    "severity": "WARNING",
                    "message": f"Latency on {host} is {latency_ms:.2f} ms (threshold: {LATENCY_THRESHOLD_MS} ms)",
                })

            # Reset compteur d'échecs
            state["consecutive_failures"] = 0
            state["last_status"] = "UP"

        else:
            # --- L'hôte ne répond pas ---
            state["consecutive_failures"] += 1
            state["last_status"] = "DOWN"

            # Règle 1 : HOST_DOWN
            # Déclenchement quand on atteint le seuil, et UNE SEULE FOIS
            if (
                state["consecutive_failures"] >= FAILURE_THRESHOLD
                and not state["down_alert_sent"]
            ):
                alerts.append({
                    "timestamp": timestamp,
                    "host": host,
                    "ip": ip,
                    "type": "HOST_DOWN",
                    "severity": "CRITICAL",
                    "message": f"Host {host} is DOWN after {state['consecutive_failures']} consecutive failures",
                })
                state["down_alert_sent"] = True

        return alerts

    def get_state(self) -> dict[str, dict]:
        """Retourne une copie de l'état interne (pour debug ou affichage)."""
        return {host: state.copy() for host, state in self._state.items()}


# --- Point d'entrée pour test rapide ---
if __name__ == "__main__":
    """
    Test minimal du détecteur sans avoir à pinger réellement.
    Simule une séquence de cycles avec différents états.
    """
    detector = AnomalyDetector()

    # Scénario simulé : srv-test passe par UP / DOWN x4 / UP
    test_cycles = [
        ("srv-test", "192.168.56.99", True, 15.0),
        ("srv-test", "192.168.56.99", False, None),
        ("srv-test", "192.168.56.99", False, None),
        ("srv-test", "192.168.56.99", False, None),  # 3e échec → HOST_DOWN
        ("srv-test", "192.168.56.99", False, None),  # 4e échec → silence (pas de re-alerte)
        ("srv-test", "192.168.56.99", True, 18.0),   # Retour → HOST_RECOVERED
        ("srv-test", "192.168.56.99", True, 350.0),  # Latence élevée → HIGH_LATENCY
    ]

    print("=== Test du détecteur ===\n")
    for i, (host, ip, alive, latency) in enumerate(test_cycles, 1):
        status = "UP" if alive else "DOWN"
        latency_str = f"{latency} ms" if latency else "N/A"
        print(f"Cycle {i}: {host} → {status} ({latency_str})")

        alerts = detector.evaluate(host, ip, alive, latency)
        for alert in alerts:
            print(f"   ⚠ ALERT [{alert['severity']}] {alert['type']}: {alert['message']}")
        if not alerts:
            print(f"   (no alert)")
        print()

    print("État final du détecteur :")
    print(detector.get_state())