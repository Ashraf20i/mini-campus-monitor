# Scénario de démonstration

Ce document décrit le déroulé d'une démonstration de **10 à 12 minutes**
du projet Mini Campus Network Monitor, destiné à un public technique
(recruteur, jury, encadrant).

## Préparation (avant l'audience)

À effectuer 10 minutes avant le début de la démo :

1. Démarrer les VMs `srv-admin` et `srv-biblio` dans VirtualBox
2. Attendre 60 secondes après leur démarrage complet (boot Linux + services)
3. Ouvrir 3 fenêtres :
   - Cisco Packet Tracer avec `docs/topology.pkt` chargé
   - PowerShell 1 : positionné dans le dossier du projet
   - PowerShell 2 : positionné dans le dossier du projet
4. Vérifier les pings : `ping 192.168.56.10` et `ping 192.168.56.11`
5. Vérifier que les VMs sont accessibles en SSH

## Acte 1 — Pitch d'ouverture (1 min)

> « Je vous présente le **Mini Campus Network Monitor**. C'est une plateforme
> de supervision réseau écrite en Python, qui surveille en temps réel un
> mini-campus simulé : disponibilité des serveurs, latence, détection
> d'anomalies, et alertes. Le projet reproduit en miniature l'architecture
> d'outils industriels comme Nagios ou Zabbix. »

**Points à souligner** :
- Projet personnel, hors cursus
- Stack Python complète (collecte + analyse + persistance + dashboard)
- Pensé pour être démontrable et défendable en 10 minutes

## Acte 2 — Architecture (2 min)

Ouvrir **Packet Tracer** et montrer la topologie.

> « Le projet repose sur une architecture à deux mondes parallèles. Côté
> conception, Cisco Packet Tracer me sert à modéliser le mini-campus :
> trois bâtiments — Administration, Bibliothèque, Laboratoires — reliés
> par un switch central, avec une sortie internet via NAT. Côté
> opérationnel, j'ai créé l'infrastructure correspondante avec VirtualBox :
> deux VMs Ubuntu configurées en IP statique sur le même plan d'adressage. »

**Points à souligner** :
- Réseau host-only `192.168.56.0/24`, isolé pour la supervision
- Plan IP cohérent entre PT et VirtualBox
- Le serveur Laboratoires est dans l'architecture cible

## Acte 3 — Structure du code (2 min)

Ouvrir **PyCharm** et montrer l'arborescence du projet.

> « Mon code est organisé en modules par responsabilité. `monitor.py`
> gère la mesure : il ping les hôtes et chronomètre la latence. `detector.py`
> est une machine à états qui applique des règles : trois échecs consécutifs
> déclenchent une alerte HOST_DOWN, un retour en service génère un
> HOST_RECOVERED, une latence excessive lève un HIGH_LATENCY. `storage.py`
> persiste les données en SQLite avec des requêtes paramétrées et des index.
> Et `dashboard/app.py` est une interface Streamlit qui lit la base et
> affiche l'état du réseau. »

**Points à souligner** :
- Séparation claire : mesure / analyse / stockage / affichage
- Single responsibility par fichier
- Configuration externalisée dans `config.py`

## Acte 4 — Démo nominale (2 min)

Dans **PowerShell 1**, lancer :
python -m src.monitor

Attendre 2-3 cycles. Montrer que les deux VMs sont UP, avec des latences
mesurées.

Dans **PowerShell 2**, lancer :
streamlit run dashboard/app.py

Le navigateur s'ouvre sur le dashboard. Pointer vers :
- Les 3 indicateurs globaux (Hôtes UP, DOWN, latence moyenne)
- Le tableau d'état actuel
- Le graphique d'historique des latences
- La liste des alertes récentes

> « Le dashboard se rafraîchit automatiquement. Chaque mesure est persistée
> en SQLite et visible immédiatement dans l'interface. »

## Acte 5 — Démo de panne (3 min)

**Le clou de la démo.** Sans toucher au script ni au dashboard :

1. Aller dans VirtualBox
2. Clic droit sur `srv-biblio` → `Fermer` → `Éteindre la machine`
3. Revenir au dashboard

**Attendre ~15 secondes** et commenter au fur et à mesure :

> « Mon détecteur n'alerte pas au premier échec — c'est un design volontaire
> pour éviter les fausses alertes liées au jitter réseau. Au bout de trois
> échecs consécutifs... »

Une alerte 🔴 HOST_DOWN apparaît dans le dashboard, le compteur "Hôtes DOWN"
passe à 1, l'état de srv-biblio passe au rouge.

> « ...le système alerte avec sévérité CRITICAL, et ne ré-alerte plus tant
> que la panne dure. C'est ce qu'on appelle un alerting à état, qui évite le
> spam d'alertes. »

Redémarrer `srv-biblio` dans VirtualBox. Attendre 30-60 secondes.

> « Quand le service revient... »

Une alerte 🟢 HOST_RECOVERED apparaît.

> « ...le détecteur génère automatiquement un message de recovery. Le cycle
> est complet. »

## Acte 6 — Conclusion et perspectives (1 min)

> « Pour finir : ce projet m'a permis de maîtriser une chaîne technique
> complète, depuis la configuration réseau et SSH jusqu'à un dashboard
> Streamlit, en passant par la persistance SQL et la détection d'anomalies
> à état. Les évolutions prévues incluent l'intégration du troisième
> serveur, et l'ajout d'un module de détection d'anomalies de sécurité
> — comme la force brute SSH ou le port scanning — qui exploiterait la
> même architecture modulaire. »

## Questions probables et réponses préparées

**Q : Pourquoi du polling et pas du push ?**
> Le polling est l'approche standard de Streamlit. Pour du push temps
> réel, on basculerait sur WebSocket avec FastAPI, ce qui est hors
> périmètre du MVP.

**Q : Comment l'état est-il géré ?**
> En mémoire dans l'objet AnomalyDetector. La persistance ajouterait peu
> de valeur sur un script qui tourne en continu. SQLite stocke en revanche
> tout l'historique des mesures et alertes.

**Q : Quelle est la limitation principale ?**
> La mesure de latence sur Windows passe par un subprocess `ping`, ce qui
> introduit un overhead. Une mesure précise nécessiterait une bibliothèque
> ICMP native comme `pythonping` ou `scapy`.

**Q : Comment scaler à 100 serveurs ?**
> Architecturalement, il suffit d'enrichir le dictionnaire HOSTS dans
> `config.py`. Pour les performances, on basculerait probablement vers
> du ping asynchrone (`asyncio`) au lieu du subprocess séquentiel.