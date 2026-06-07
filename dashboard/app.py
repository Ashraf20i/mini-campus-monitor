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

from streamlit_autorefresh import st_autorefresh

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
    initial_sidebar_state="expanded",
)


# ============================================================
#  FONCTIONS DE CHARGEMENT (avec cache)
# ============================================================

@st.cache_data(ttl=2)
def load_metrics(limit: int = 1000) -> list[dict]:
    """Charge les mesures récentes depuis SQLite (cache 2s)."""
    return storage.get_recent_metrics(limit=limit)


@st.cache_data(ttl=2)
def load_alerts(limit: int = 50) -> list[dict]:
    """Charge les alertes récentes depuis SQLite (cache 2s)."""
    return storage.get_recent_alerts(limit=limit)


@st.cache_data(ttl=2)
def load_severity_counts() -> dict[str, int]:
    """Charge le comptage des alertes par sévérité (cache 2s)."""
    return storage.count_alerts_by_severity()


# ============================================================
#  SIDEBAR (contrôles et infos)
# ============================================================

with st.sidebar:
    st.header("⚙ Contrôles")

    refresh_seconds = st.slider(
        "Intervalle de refresh (s)",
        min_value=1,
        max_value=30,
        value=POLL_INTERVAL,
        help="Fréquence de rafraîchissement automatique du dashboard",
    )

    if st.button("🔄 Forcer le rafraîchissement", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    time_window = st.selectbox(
        "📊 Fenêtre temporelle du graphique",
        options=["Dernière heure", "Dernières 24h", "Tout l'historique"],
        index=0,
        help="Filtre l'historique des latences pour le graphique",
    )

    st.markdown("---")

    st.subheader("📍 Hôtes supervisés")
    for host, ip in HOSTS.items():
        st.markdown(f"• **{host}** — `{ip}`")

    st.markdown("---")

    st.subheader("🛠 Stack technique")
    st.caption("Python • SQLite • Streamlit • Plotly")

    st.markdown("---")

    st.caption("📦 Projet open-source")
    st.caption("🎓 EMI Rabat — 2026")


# Auto-refresh : doit être appelé après le slider qui définit refresh_seconds
st_autorefresh(interval=refresh_seconds * 1000, key="data_refresh")


# ============================================================
#  HEADER
# ============================================================

st.title("📡 Mini Campus Network Monitor")
st.markdown(
    "**Supervision réseau temps réel** — Détection d'anomalies stateful, "
    "persistance SQLite, dashboard interactif."
)

last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.caption(
    f"🕐 Dernière actualisation : {last_update}  •  "
    f"⏱ Refresh automatique toutes les {refresh_seconds}s"
)

st.markdown("---")


# ============================================================
#  CHARGEMENT DES DONNÉES
# ============================================================

metrics = load_metrics(limit=1000)
alerts = load_alerts(limit=50)
severity_counts = load_severity_counts()

if not metrics:
    st.warning("⚠ Aucune donnée disponible. Lance d'abord `python -m src.monitor`.")
    st.stop()

# Transformation en DataFrames pandas
df_metrics = pd.DataFrame(metrics)
df_metrics["timestamp"] = pd.to_datetime(df_metrics["timestamp"])

df_alerts = pd.DataFrame(alerts) if alerts else pd.DataFrame()


# ============================================================
#  SECTION 1 — STATUT GLOBAL
# ============================================================

st.subheader("🎯 Statut global")

# Pour chaque hôte, on prend sa mesure la plus récente
latest_per_host = (
    df_metrics
    .sort_values("timestamp")
    .groupby("host")
    .tail(1)
)

hosts_up = (latest_per_host["status"] == "UP").sum()
hosts_down = (latest_per_host["status"] == "DOWN").sum()

# Latence moyenne (uniquement sur les UP récents pour rester pertinent)
recent_cutoff = pd.Timestamp.now() - pd.Timedelta(hours=1)
recent_metrics = df_metrics[df_metrics["timestamp"] >= recent_cutoff]
avg_latency = recent_metrics[recent_metrics["status"] == "UP"]["latency_ms"].mean()
avg_latency_str = f"{avg_latency:.1f} ms" if pd.notna(avg_latency) else "N/A"

col1, col2, col3, col4 = st.columns(4)
col1.metric(label="✅ Hôtes UP", value=int(hosts_up))
col2.metric(label="❌ Hôtes DOWN", value=int(hosts_down))
col3.metric(label="⏱ Latence moyenne (1h)", value=avg_latency_str)
col4.metric(label="📊 Mesures totales", value=len(df_metrics))

st.markdown("---")


# ============================================================
#  SECTION 2 — ÉTAT ACTUEL DES HÔTES
# ============================================================

st.subheader("🖥 État actuel des hôtes")

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

st.markdown("---")


# ============================================================
#  SECTION 3 — HISTORIQUE DES LATENCES (graphique)
# ============================================================

st.subheader("📈 Historique des latences")

# Filtrage selon la fenêtre temporelle choisie dans la sidebar
df_chart = df_metrics[df_metrics["status"] == "UP"].copy()

if time_window == "Dernière heure":
    cutoff = pd.Timestamp.now() - pd.Timedelta(hours=1)
    df_chart = df_chart[df_chart["timestamp"] >= cutoff]
    caption_text = "Fenêtre : dernière heure"
elif time_window == "Dernières 24h":
    cutoff = pd.Timestamp.now() - pd.Timedelta(hours=24)
    df_chart = df_chart[df_chart["timestamp"] >= cutoff]
    caption_text = "Fenêtre : dernières 24h"
else:
    caption_text = "Fenêtre : tout l'historique"

st.caption(f"_{caption_text} — {len(df_chart)} mesures affichées_")

if not df_chart.empty:
    fig = px.line(
        df_chart,
        x="timestamp",
        y="latency_ms",
        color="host",
        markers=True,
        labels={
            "timestamp": "Heure",
            "latency_ms": "Latence (ms)",
            "host": "Hôte",
        },
    )
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        hovermode="x unified",
    )
    fig.update_traces(line=dict(width=2), marker=dict(size=6))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Pas encore de données UP à afficher pour cette fenêtre.")

st.markdown("---")


# ============================================================
#  SECTION 4 — ALERTES
# ============================================================

st.subheader("🚨 Alertes récentes")

# Mini-bilan en haut : comptage par sévérité
if severity_counts:
    severity_order = ["CRITICAL", "WARNING", "INFO"]
    severity_icons = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🟢"}

    cols = st.columns(3)
    for i, sev in enumerate(severity_order):
        count = severity_counts.get(sev, 0)
        cols[i].metric(
            label=f"{severity_icons[sev]} {sev}",
            value=count,
        )

st.markdown("")

# Liste des dernières alertes
if not df_alerts.empty:
    df_alerts_display = df_alerts[
        ["timestamp", "host", "type", "severity", "message"]
    ].copy()
    df_alerts_display.columns = ["Heure", "Hôte", "Type", "Sévérité", "Message"]
    st.dataframe(df_alerts_display, use_container_width=True, hide_index=True)
else:
    st.success("✓ Aucune alerte enregistrée. Tout va bien.")


# ============================================================
#  PIED DE PAGE
# ============================================================

st.markdown("---")

footer_col1, footer_col2, footer_col3 = st.columns(3)
with footer_col1:
    st.caption(f"💾 {len(df_metrics)} mesures en base SQLite")
with footer_col2:
    total_alerts = sum(severity_counts.values()) if severity_counts else 0
    st.caption(f"🚨 {total_alerts} alertes historiques")
with footer_col3:
    st.caption("🏗 Mini Campus Network Monitor • v1.0")