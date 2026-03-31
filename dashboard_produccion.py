# ============================================================
# Dashboard de Producción — Pad LOM-01
# Formación Vaca Muerta · Cuenca Neuquina
#
# Para correr:
#   pip install streamlit plotly pandas numpy
#   streamlit run dashboard_produccion.py
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Configuración de página ──────────────────────────────────
st.set_page_config(
    page_title="Pad LOM-01 · Producción",
    page_icon="🛢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Helpers ─────────────────────────────────────────────────
def hex_to_rgba(hex_color, opacity=0.15):
    """Convierte color hex a rgba string compatible con Plotly Python."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{opacity})"

# ── Estilos custom ───────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    .metric-card {
        background: #1e2530;
        border-radius: 10px;
        padding: 16px;
        border-left: 4px solid;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Flag_of_Argentina.svg/320px-Flag_of_Argentina.svg.png", width=120)
    st.title("⚙️ Parámetros")
    st.markdown("---")

    pozos_sel = st.multiselect(
        "Seleccioná los pozos:",
        ["LOM-01-H", "LOM-02-H", "LOM-03-H", "LOM-04-H"],
        default=["LOM-01-H", "LOM-02-H", "LOM-03-H", "LOM-04-H"]
    )

    periodo = st.slider(
        "Período (meses):",
        min_value=6, max_value=24, value=24, step=6
    )

    escala_y = st.radio(
        "Escala eje Y (producción):",
        ["Lineal", "Logarítmica"]
    )

    st.markdown("---")
    st.markdown("**📍 Pad LOM-01**")
    st.markdown("Loma Campana · Neuquén")
    st.markdown("Formación Vaca Muerta")
    st.markdown("*Datos sintéticos*")

# ── Generación de datos sintéticos ──────────────────────────
@st.cache_data
def generar_datos():
    meses = pd.date_range(start="2023-01-01", periods=24, freq="MS")

    def decline(qi, Di, b, n):
        return [round(qi / (1 + b * Di * t) ** (1 / b), 1) for t in range(n)]

    def add_noise(arr, pct=0.05):
        return [round(v * (1 + (np.random.rand() - 0.5) * pct), 1) for v in arr]

    pozos = {
        "LOM-01-H": {"qi": 847,  "Di": 0.080, "b": 1.30, "gor": 180, "gor_rate": 2.5, "color": "#58a6ff"},
        "LOM-02-H": {"qi": 912,  "Di": 0.075, "b": 1.25, "gor": 175, "gor_rate": 2.2, "color": "#3fb950"},
        "LOM-03-H": {"qi": 778,  "Di": 0.090, "b": 1.20, "gor": 190, "gor_rate": 2.8, "color": "#f78166"},
        "LOM-04-H": {"qi": 963,  "Di": 0.070, "b": 1.35, "gor": 170, "gor_rate": 2.0, "color": "#d2a8ff"},
    }

    df_list = []
    for nombre, p in pozos.items():
        oil  = add_noise(decline(p["qi"], p["Di"], p["b"], 24))
        gas  = [round(oil[i] * (p["gor"] + p["gor_rate"] * i) / 1000, 2) for i in range(24)]
        gor  = [round(gas[i] * 1000 / oil[i], 1) for i in range(24)]
        wc   = [round(min(2 + 0.8 * i + np.random.rand() * 0.5, 35), 1) for i in range(24)]
        cum  = list(np.cumsum([v * 30 for v in oil]))

        for i in range(24):
            df_list.append({
                "fecha": meses[i],
                "pozo": nombre,
                "color": p["color"],
                "oil_m3d": oil[i],
                "gas_mm3d": gas[i],
                "gor": gor[i],
                "wc": wc[i],
                "cum_oil": round(cum[i])
            })

    return pd.DataFrame(df_list)

df_full = generar_datos()

# Filtrar por selección del sidebar
df = df_full[
    (df_full["pozo"].isin(pozos_sel)) &
    (df_full["fecha"] <= df_full["fecha"].min() + pd.DateOffset(months=periodo - 1))
]

colores = dict(zip(df_full["pozo"].unique(), df_full.groupby("pozo")["color"].first()))

# ── Header ───────────────────────────────────────────────────
st.title("🛢 Pad LOM-01 — Dashboard de Producción")
st.markdown("**Formación Vaca Muerta · Cuenca Neuquina · Datos sintéticos**")
st.markdown("---")

# ── KPIs ─────────────────────────────────────────────────────
st.subheader("📊 Indicadores por Pozo")
cols = st.columns(len(pozos_sel)) if pozos_sel else st.columns(1)

for idx, pozo in enumerate(pozos_sel):
    d = df[df["pozo"] == pozo]
    if d.empty:
        continue
    pico  = d["oil_m3d"].max()
    actual = d["oil_m3d"].iloc[-1]
    cum   = d["cum_oil"].iloc[-1]
    delta = round((actual - pico) / pico * 100, 1)

    with cols[idx]:
        st.metric(
            label=f"**{pozo}**",
            value=f"{actual:,.0f} m³/d",
            delta=f"{delta}% vs pico"
        )
        st.caption(f"Pico: {pico:,.0f} m³/d | Acum: {cum/1000:,.0f} Mm³")

st.markdown("---")

# ── Gráficos principales ──────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("🛢 Producción de Petróleo (m³/d)")
    fig_oil = go.Figure()
    for pozo in pozos_sel:
        d = df[df["pozo"] == pozo]
        fig_oil.add_trace(go.Scatter(
            x=d["fecha"], y=d["oil_m3d"],
            name=pozo, mode="lines",
            line=dict(color=colores[pozo], width=2.5),
            hovertemplate=f"<b>{pozo}</b><br>%{{x|%b %y}}<br>%{{y:.0f}} m³/d<extra></extra>"
        ))
    fig_oil.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_type="log" if escala_y == "Logarítmica" else "linear",
        yaxis_title="m³/d",
        height=320,
        margin=dict(t=10, b=40, l=50, r=10),
        hovermode="x unified"
    )
    st.plotly_chart(fig_oil, use_container_width=True)

with col2:
    st.subheader("💨 Producción de Gas (Mm³/d)")
    fig_gas = go.Figure()
    for pozo in pozos_sel:
        d = df[df["pozo"] == pozo]
        fig_gas.add_trace(go.Scatter(
            x=d["fecha"], y=d["gas_mm3d"],
            name=pozo, mode="lines",
            line=dict(color=colores[pozo], width=2.5),
            hovertemplate=f"<b>{pozo}</b><br>%{{x|%b %y}}<br>%{{y:.2f}} Mm³/d<extra></extra>"
        ))
    fig_gas.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_title="Mm³/d",
        height=320,
        margin=dict(t=10, b=40, l=50, r=10),
        hovermode="x unified"
    )
    st.plotly_chart(fig_gas, use_container_width=True)

# ── Acumulada + GOR ──────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("📈 Producción Acumulada de Petróleo")
    fig_cum = go.Figure()
    for pozo in pozos_sel:
        d = df[df["pozo"] == pozo]
        fig_cum.add_trace(go.Scatter(
            x=d["fecha"], y=d["cum_oil"],
            name=pozo, mode="lines",
            fill="tozeroy",
            fillcolor=hex_to_rgba(colores[pozo], 0.15),
            line=dict(color=colores[pozo], width=2),
            hovertemplate=f"<b>{pozo}</b><br>%{{x|%b %y}}<br>%{{y:,.0f}} m³<extra></extra>"
        ))
    fig_cum.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_title="m³ acumulados",
        height=300,
        margin=dict(t=10, b=40, l=60, r=10),
        hovermode="x unified"
    )
    st.plotly_chart(fig_cum, use_container_width=True)

with col4:
    st.subheader("⚗️ GOR y Corte de Agua")
    fig_gor = make_subplots(specs=[[{"secondary_y": True}]])
    for pozo in pozos_sel:
        d = df[df["pozo"] == pozo]
        fig_gor.add_trace(go.Scatter(
            x=d["fecha"], y=d["gor"],
            name=f"GOR {pozo}", mode="lines",
            line=dict(color=colores[pozo], width=2),
            hovertemplate=f"GOR {pozo}: %{{y:.0f}} m³/m³<extra></extra>"
        ), secondary_y=False)
        fig_gor.add_trace(go.Scatter(
            x=d["fecha"], y=d["wc"],
            name=f"WC {pozo}", mode="lines",
            line=dict(color=colores[pozo], width=1.5, dash="dot"),
            hovertemplate=f"WC {pozo}: %{{y:.1f}}%<extra></extra>"
        ), secondary_y=True)
    fig_gor.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=300,
        margin=dict(t=10, b=40, l=50, r=50),
        hovermode="x unified"
    )
    fig_gor.update_yaxes(title_text="GOR (m³/m³)", secondary_y=False)
    fig_gor.update_yaxes(title_text="WC (%)", secondary_y=True)
    st.plotly_chart(fig_gor, use_container_width=True)

# ── Tabla de datos ───────────────────────────────────────────
st.markdown("---")
with st.expander("📋 Ver tabla de datos completa"):
    df_tabla = df[["fecha","pozo","oil_m3d","gas_mm3d","gor","wc","cum_oil"]].copy()
    df_tabla.columns = ["Fecha","Pozo","Petróleo (m³/d)","Gas (Mm³/d)","GOR (m³/m³)","WC (%)","Acum. (m³)"]
    df_tabla["Fecha"] = df_tabla["Fecha"].dt.strftime("%b %Y")
    st.dataframe(df_tabla, use_container_width=True, hide_index=True)

    csv = df_tabla.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Descargar CSV",
        data=csv,
        file_name="produccion_pad_lom01.csv",
        mime="text/csv"
    )

# ── Footer ───────────────────────────────────────────────────
st.markdown("---")
st.caption("Dashboard de ejemplo · Datos sintéticos · Desarrollado con Streamlit + Plotly · Cuenca Neuquina")
