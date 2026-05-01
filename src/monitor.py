"""
Module de supervision réseau.
Contient les fonctions de base pour vérifier la disponibilité des hôtes.
"""

import subprocess
import platform


def ping_host(ip: str, timeout: int = 1) -> bool:
    """
    Vérifie si un hôte répond au ping.

    Args:
        ip: adresse IP de la machine à tester (ex: '192.168.56.10')
        timeout: délai d'attente maximum en secondes (défaut: 1)

    Returns:
        True si la machine répond, False sinon
    """
    # Le paramètre count varie selon l'OS
    # Sur Windows : -n 1 (1 paquet) et -w 1000 (timeout en ms)
    # Sur Linux   : -c 1 (1 paquet) et -W 1   (timeout en s)
    if platform.system().lower() == "windows":
        command = ["ping", "-n", "1", "-w", str(timeout * 1000), ip]
    else:
        command = ["ping", "-c", "1", "-W", str(timeout), ip]

    # On exécute la commande et on capture le résultat
    # capture_output=True empêche l'affichage dans le terminal
    # text=True nous donne le résultat sous forme de chaîne (pas de bytes)
    result = subprocess.run(command, capture_output=True, text=True)

    # Le code de retour 0 signifie "succès" (machine joignable)
    # Tout autre code = échec
    return result.returncode == 0


# Test rapide quand on lance ce fichier directement
if __name__ == "__main__":
    test_ip = "192.168.56.10"
    is_alive = ping_host(test_ip)
    print(f"L'hôte {test_ip} est {'UP ✅' if is_alive else 'DOWN ❌'}")