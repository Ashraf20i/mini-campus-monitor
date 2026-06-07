# Topologie réseau du Mini Campus Network Monitor

## Vue d'ensemble

Le projet simule un mini-campus de petite taille composé de **3 bâtiments**
interconnectés par un switch central, avec une sortie internet via NAT.

![Topologie](topology.png)

## Architecture en deux mondes

Le projet repose sur une architecture à **deux mondes parallèles** :

| Monde | Outil | Rôle |
|---|---|---|
| Monde A — Conception | Cisco Packet Tracer | Topologie visuelle, plan IP, démonstration orale |
| Monde B — Opérationnel | VirtualBox + Python | Vraies VMs Linux supervisées en temps réel |

Les deux mondes utilisent **le même plan d'adressage IP** pour assurer la
cohérence entre le schéma théorique et l'infrastructure réelle.

## Plan d'adressage IP

### Sous-réseau de supervision

- **Réseau** : `192.168.56.0/24`
- **Masque** : `255.255.255.0` (24 bits réseau, 8 bits hôtes)
- **Adresses utilisables** : 254 hôtes maximum
- **Adresse de réseau** : `192.168.56.0` (réservée)
- **Adresse de broadcast** : `192.168.56.255` (réservée)
- **Type** : réseau privé isolé (host-only VirtualBox)

### Attribution des adresses

| Rôle | Hostname | IP | Statut MVP | Bâtiment |
|---|---|---|---|---|
| Superviseur | PC-Windows | `192.168.56.1` | Réel | Poste admin |
| Serveur | `srv-admin` | `192.168.56.10` | Réel, supervisé | Administration |
| Serveur | `srv-biblio` | `192.168.56.11` | Réel, supervisé | Bibliothèque |
| Serveur | `srv-labo` | `192.168.56.12` | Architecture cible | Laboratoires |

### Convention d'attribution

- `.1` → passerelle / superviseur (convention universelle)
- `.10` à `.99` → serveurs en IP statique (zone basse)
- `.100` à `.254` → réservé pour DHCP futur (zone haute)

Cette séparation **statique vs dynamique** évite tout conflit d'adressage en
cas d'extension du réseau.

## Sous-réseau d'accès internet

Chaque VM dispose d'une seconde interface réseau dédiée à l'accès internet :

- **Réseau** : `10.0.3.0/24` (NAT VirtualBox)
- **Attribution** : DHCP (géré par VirtualBox)
- **Rôle** : permettre `apt update`, résolution DNS, accès externe

Ce réseau **ne participe pas à la supervision**. Il existe uniquement pour
les besoins administratifs des VMs (installation de paquets, mises à jour).

## Séparation des plans

La séparation host-only / NAT est volontaire et critique :

- Le **plan de supervision** (host-only) est **isolé** : aucun trafic externe
  ne peut interférer avec les mesures de latence ou de disponibilité.
- Le **plan d'accès internet** (NAT) est **unidirectionnel** : les VMs
  sortent vers internet, mais aucun hôte externe ne peut entrer.

Cette architecture suit le principe de **séparation des préoccupations**
appliqué aux réseaux.

## Évolutions prévues

- **Court terme** : intégration du serveur `srv-labo` dans la supervision
  active (ajout d'une entrée dans `src/config.py`).
- **Moyen terme** : ajout d'un module de détection d'anomalies de sécurité
  (force brute SSH, port scanning) — voir documentation cybersécurité.