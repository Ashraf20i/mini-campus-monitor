"""
Dashboard de supervision réseau.

Interface web Streamlit qui lit les données collectées par monitor.py
depuis la base SQLite, et les affiche en temps réel.

Lancement :
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px

# Ajout du dossier racine au path Python pour pouvoir importer src.*
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import storage
from src.config import HOSTS, POLL_INTERVAL


# ============================================================
#  CONFIGURATION DE LA PAGE
# ============================================================

st.set_page_config(
    page_title="Mini Campus Network Monitor",
    page_icon="📡",
    layout="wide",
)

from streamlit_autorefresh import st_autorefresh

# Auto-refresh : rafraîchissement fluide toutes les X secondes
REFRESH_INTERVAL_SEC = POLL_INTERVAL


# ============================================================
#  HEADER
# ============================================================

st.title("📡 Mini Campus Network Monitor")
# Sidebar pour les contrôles
with st.sidebar:
    st.header("⚙ Contrôles")
    refresh_seconds = st.slider(
        "Intervalle de refresh (s)",
        min_value=1,
        max_value=30,
        value=POLL_INTERVAL,
    )

st_autorefresh(interval=refresh_seconds * 1000, key="data_refresh")
st.caption(
    f"Supervision en temps réel — Dernière actualisation : "
    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
    f"(refresh auto toutes les {REFRESH_INTERVAL_SEC}s)"
)


# ============================================================
#  CHARGEMENT DES DONNÉES
# ============================================================

# On va lire jusqu'à 1000 mesures récentes pour avoir un bon historique
metrics = storage.get_recent_metrics(limit=1000)
alerts = storage.get_recent_alerts(limit=50)
severity_counts = storage.count_alerts_by_severity()

# Si la base est vide, on s'arrête proprement
if not metrics:
    st.warning("⚠ Aucune donnée disponible. Lance d'abord `python -m src.monitor`.")
    st.stop()

# Transformation en DataFrames pandas pour faciliter les manipulations
df_metrics = pd.DataFrame(metrics)
df_metrics["timestamp"] = pd.to_datetime(df_metrics["timestamp"])

df_alerts = pd.DataFrame(alerts) if alerts else pd.DataFrame()


# ============================================================
#  SECTION 1 — STATUT GLOBAL (3 grandes métriques en haut)
# ============================================================

st.markdown("### Statut global")

# Pour chaque hôte, on prend sa MESURE LA PLUS RÉCENTE
latest_per_host = (
    df_metrics
    .sort_values("timestamp")
    .groupby("host")
    .tail(1)
)

hosts_up = (latest_per_host["status"] == "UP").sum()
hosts_down = (latest_per_host["status"] == "DOWN").sum()

# Latence moyenne globale (uniquement sur les UP, DOWN n'a pas de latence)
avg_latency = df_metrics[df_metrics["status"] == "UP"]["latency_ms"].mean()
avg_latency_str = f"{avg_latency:.1f} ms" if pd.notna(avg_latency) else "N/A"

col1, col2, col3 = st.columns(3)
col1.metric(label="✅ Hôtes UP", value=int(hosts_up))
col2.metric(label="❌ Hôtes DOWN", value=int(hosts_down))
col3.metric(label="⏱ Latence moyenne", value=avg_latency_str)


# ============================================================
#  SECTION 2 — ÉTAT ACTUEL DES HÔTES
# ============================================================

st.markdown("### État actuel des hôtes")

# Construction d'un DataFrame présentation
display_rows = []
for _, row in latest_per_host.iterrows():
    icon = "🟢" if row["status"] == "UP" else "🔴"
    latency = f"{row['latency_ms']:.2f} ms" if pd.notna(row["latency_ms"]) else "—"
    display_rows.append({
        "État": icon,
        "Hôte": row["host"],
        "IP": row["ip"],
        "Statut": row["status"],
        "Latence": latency,
        "Dernier check": row["timestamp"].strftime("%H:%M:%S"),
    })

df_display = pd.DataFrame(display_rows)
st.dataframe(df_display, use_container_width=True, hide_index=True)


# ============================================================
#  SECTION 3 — HISTORIQUE DES LATENCES (graphique)
# ============================================================

st.markdown("### Historique des latences")

# On ne garde que les mesures UP avec latence (on ignore les DOWN pour le graphique)
df_chart = df_metrics[df_metrics["status"] == "UP"].copy()

if not df_chart.empty:
    fig = px.line(
        df_chart,
        x="timestamp",
        y="latency_ms",
        color="host",
        markers=True,
        labels={"timestamp": "Heure", "latency_ms": "Latence (ms)", "host": "Hôte"},
    )
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Pas encore de données UP à afficher.")


# ============================================================
#  SECTION 4 — ALERTES RÉCENTES
# ============================================================

st.markdown("### Alertes récentes")

# Mini-bilan en haut
if severity_counts:
    cols = st.columns(len(severity_counts))
    severity_order = ["CRITICAL", "WARNING", "INFO"]
    severity_icons = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🟢"}
    for i, sev in enumerate([s for s in severity_order if s in severity_counts]):
        cols[i].metric(
            label=f"{severity_icons.get(sev, '⚠')} {sev}",
            value=severity_counts[sev],
        )

# Liste des dernières alertes
if not df_alerts.empty:
    df_alerts_display = df_alerts[["timestamp", "host", "type", "severity", "message"]].copy()
    df_alerts_display.columns = ["Heure", "Hôte", "Type", "Sévérité", "Message"]
    st.dataframe(df_alerts_display, use_container_width=True, hide_index=True)
else:
    st.success("Aucune alerte enregistrée. Tout va bien.")


# ============================================================
#  PIED DE PAGE
# ============================================================

st.markdown("---")
st.caption(
    f"Mini Campus Network Monitor • {len(df_metrics)} mesures totales en base • "
    f"Refresh : {REFRESH_INTERVAL_SEC}s"
)