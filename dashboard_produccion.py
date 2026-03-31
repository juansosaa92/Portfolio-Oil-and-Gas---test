# ============================================================
# Dashboard Pad LOM-01 — Producción + Trayectorias 3D
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
    page_title="Pad LOM-01 · Vaca Muerta",
    page_icon="🛢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Helpers ──────────────────────────────────────────────────
def hex_to_rgba(hex_color, opacity=0.15):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{opacity})"

def make_colorscale(hex_color):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return [
        [0,   f"rgba({int(r*0.5)},{int(g*0.5)},{int(b*0.5)},0.72)"],
        [0.5, f"rgba({int(r*0.75)},{int(g*0.75)},{int(b*0.75)},0.72)"],
        [1,   f"rgba({r},{g},{b},0.72)"]
    ]

# ── Estilos custom ───────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ── Constantes ───────────────────────────────────────────────
COLORS  = ["#58a6ff", "#3fb950", "#f78166", "#d2a8ff"]
NAMES   = ["LOM-01-H", "LOM-02-H", "LOM-03-H", "LOM-04-H"]
COLOR_MAP = dict(zip(NAMES, COLORS))

STRAT = [
    {"name": "Neuquén",     "top": 0,    "base": 800,  "color": "#8b6f4e", "texture": "granular"},
    {"name": "Rayoso",      "top": 800,  "base": 1200, "color": "#4a9eff", "texture": "laminar"},
    {"name": "Agrio",       "top": 1200, "base": 1700, "color": "#a0c4ff", "texture": "nodular"},
    {"name": "Quintuco",    "top": 1700, "base": 2400, "color": "#ffd700", "texture": "masivo"},
    {"name": "VM Superior", "top": 2400, "base": 2900, "color": "#3fb950", "texture": "ondulado"},
    {"name": "VM Inferior", "top": 2900, "base": 3400, "color": "#f78166", "texture": "laminado"},
    {"name": "Tordillo",    "top": 3400, "base": 3700, "color": "#d2a8ff", "texture": "cruzado"},
    {"name": "Precuyano",   "top": 3700, "base": 4000, "color": "#ff6b6b", "texture": "irregular"},
]

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Parámetros")
    st.markdown("---")

    pozos_sel = st.multiselect(
        "Pozos:",
        NAMES,
        default=NAMES
    )

    periodo = st.slider("Período (meses):", 6, 24, 24, 6)

    escala_y = st.radio("Escala eje Y:", ["Lineal", "Logarítmica"])

    st.markdown("---")
    st.markdown("**📍 Pad LOM-01**")
    st.markdown("Loma Campana · Neuquén")
    st.markdown("Formación Vaca Muerta")
    st.markdown("*Datos sintéticos*")

# ── Datos de producción ───────────────────────────────────────
@st.cache_data
def generar_datos():
    meses = pd.date_range(start="2023-01-01", periods=24, freq="MS")

    def decline(qi, Di, b, n):
        return [round(qi / (1 + b * Di * t) ** (1 / b), 1) for t in range(n)]

    def add_noise(arr, pct=0.05):
        np.random.seed(42)
        return [round(v * (1 + (np.random.rand() - 0.5) * pct), 1) for v in arr]

    pozos_cfg = {
        "LOM-01-H": {"qi": 847,  "Di": 0.080, "b": 1.30, "gor": 180, "gor_rate": 2.5},
        "LOM-02-H": {"qi": 912,  "Di": 0.075, "b": 1.25, "gor": 175, "gor_rate": 2.2},
        "LOM-03-H": {"qi": 778,  "Di": 0.090, "b": 1.20, "gor": 190, "gor_rate": 2.8},
        "LOM-04-H": {"qi": 963,  "Di": 0.070, "b": 1.35, "gor": 170, "gor_rate": 2.0},
    }

    df_list = []
    for nombre, p in pozos_cfg.items():
        oil = add_noise(decline(p["qi"], p["Di"], p["b"], 24))
        gas = [round(oil[i] * (p["gor"] + p["gor_rate"] * i) / 1000, 2) for i in range(24)]
        gor = [round(gas[i] * 1000 / oil[i], 1) for i in range(24)]
        wc  = [round(min(2 + 0.8 * i + np.random.rand() * 0.5, 35), 1) for i in range(24)]
        cum = list(np.cumsum([v * 30 for v in oil]))
        for i in range(24):
            df_list.append({
                "fecha": meses[i], "pozo": nombre,
                "oil_m3d": oil[i], "gas_mm3d": gas[i],
                "gor": gor[i], "wc": wc[i], "cum_oil": round(cum[i])
            })
    return pd.DataFrame(df_list)

df_full = generar_datos()
df = df_full[
    (df_full["pozo"].isin(pozos_sel)) &
    (df_full["fecha"] <= df_full["fecha"].min() + pd.DateOffset(months=periodo - 1))
]

# ── Trayectorias 3D ───────────────────────────────────────────
@st.cache_data
def generar_trayectorias():
    dip_rate = np.tan(3 * np.pi / 180)

    def build_traj(surf_n, surf_e, kickoff, tvd_target, horz_len, az_deg):
        az = az_deg * np.pi / 180
        xs, ys, zs = [], [], []
        for i in range(41):
            xs.append(surf_e); ys.append(surf_n); zs.append(-(kickoff/40)*i)
        build_len = (tvd_target - kickoff) * 1.62
        tvd_c, e_c, n_c = kickoff, surf_e, surf_n
        for i in range(1, 81):
            inc = (i/80) * np.pi/2
            dl  = build_len / 80
            tvd_c = min(tvd_c + dl * np.cos(inc), tvd_target)
            e_c  += dl * np.sin(inc) * np.sin(az)
            n_c  += dl * np.sin(inc) * np.cos(az)
            xs.append(e_c); ys.append(n_c); zs.append(-tvd_c)
        lx, ly, lz = xs[-1], ys[-1], zs[-1]
        for i in range(1, 81):
            d = (horz_len/80) * i
            dip_adj = d * np.sin(az) * dip_rate
            xs.append(lx + d*np.sin(az))
            ys.append(ly + d*np.cos(az))
            zs.append(lz - dip_adj)
        return xs, ys, zs

    trajs = {}
    for i, name in enumerate(NAMES):
        trajs[name] = build_traj(i*300, 0, 900, 3150, 3200, 90)
    return trajs

trajs = generar_trayectorias()

# ── Superficies estratigráficas ───────────────────────────────
@st.cache_data
def generar_superficies():
    NX, NY = 25, 18
    xg = np.linspace(-300, 3700, NX)
    yg = np.linspace(-300, 1200, NY)
    dip = np.tan(3 * np.pi / 180)
    surfaces = []
    for s in STRAT:
        Z = np.array([[-( s["top"] + x * dip) for x in xg] for _ in yg])
        C = np.zeros((NY, NX))
        t = s["texture"]
        for j, y in enumerate(yg):
            for i, x in enumerate(xg):
                if t == "granular":
                    C[j,i] = np.sin(x*0.08)*np.cos(y*0.08) + np.sin(x*0.19+1.3)*0.5
                elif t == "laminar":
                    C[j,i] = np.sin(y*0.35) + np.sin(y*0.7)*0.3
                elif t == "nodular":
                    C[j,i] = np.sin(x*0.05)*np.sin(y*0.08) + np.cos(x*0.12)*0.4
                elif t == "masivo":
                    C[j,i] = (x/(3700+300))*0.3 + np.sin(x*0.01+y*0.01)*0.1
                elif t == "ondulado":
                    C[j,i] = np.sin(x*0.025+y*0.015) + np.cos(x*0.012)*0.5
                elif t == "laminado":
                    C[j,i] = np.sin(y*0.5) + np.sin(y*1.1)*0.4 + np.sin(x*0.03)*0.2
                elif t == "cruzado":
                    C[j,i] = np.sin((x+y)*0.06) + np.sin((x-y)*0.04)*0.6
                else:
                    C[j,i] = np.sin(x*0.1)*np.cos(y*0.13) + np.sin(x*0.07+y*0.09)*0.7
        surfaces.append({"name": s["name"], "color": s["color"],
                         "top": s["top"], "base": s["base"],
                         "xg": xg.tolist(), "yg": yg.tolist(),
                         "Z": Z.tolist(), "C": C.tolist(),
                         "is_target": s["name"] == "VM Inferior"})
    return surfaces

surfaces = generar_superficies()

# ════════════════════════════════════════════════════════════
# LAYOUT PRINCIPAL CON TABS
# ════════════════════════════════════════════════════════════
st.title("🛢 Pad LOM-01 — Dashboard Vaca Muerta")
st.markdown("**Formación Vaca Muerta · Cuenca Neuquina · Datos sintéticos**")
st.markdown("---")

tab1, tab2 = st.tabs(["📊 Producción", "🌍 Trayectorias 3D"])

# ════════════════════════════════════════════════════════════
# TAB 1: PRODUCCIÓN
# ════════════════════════════════════════════════════════════
with tab1:

    # KPIs
    st.subheader("Indicadores por Pozo")
    if pozos_sel:
        cols = st.columns(len(pozos_sel))
        for idx, pozo in enumerate(pozos_sel):
            d = df[df["pozo"] == pozo]
            if d.empty: continue
            pico   = d["oil_m3d"].max()
            actual = d["oil_m3d"].iloc[-1]
            cum    = d["cum_oil"].iloc[-1]
            delta  = round((actual - pico) / pico * 100, 1)
            with cols[idx]:
                st.metric(label=f"**{pozo}**",
                          value=f"{actual:,.0f} m³/d",
                          delta=f"{delta}% vs pico")
                st.caption(f"Pico: {pico:,.0f} m³/d | Acum: {cum/1000:,.0f} Mm³")

    st.markdown("---")

    # Petróleo + Gas
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🛢 Petróleo (m³/d)")
        fig_oil = go.Figure()
        for pozo in pozos_sel:
            d = df[df["pozo"] == pozo]
            fig_oil.add_trace(go.Scatter(
                x=d["fecha"], y=d["oil_m3d"], name=pozo, mode="lines",
                line=dict(color=COLOR_MAP[pozo], width=2.5),
                hovertemplate=f"<b>{pozo}</b><br>%{{x|%b %y}}<br>%{{y:.0f}} m³/d<extra></extra>"
            ))
        fig_oil.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis_type="log" if escala_y == "Logarítmica" else "linear",
            yaxis_title="m³/d", height=300,
            margin=dict(t=10,b=40,l=50,r=10), hovermode="x unified"
        )
        st.plotly_chart(fig_oil, use_container_width=True)

    with col2:
        st.subheader("💨 Gas (Mm³/d)")
        fig_gas = go.Figure()
        for pozo in pozos_sel:
            d = df[df["pozo"] == pozo]
            fig_gas.add_trace(go.Scatter(
                x=d["fecha"], y=d["gas_mm3d"], name=pozo, mode="lines",
                line=dict(color=COLOR_MAP[pozo], width=2.5),
                hovertemplate=f"<b>{pozo}</b><br>%{{x|%b %y}}<br>%{{y:.2f}} Mm³/d<extra></extra>"
            ))
        fig_gas.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", yaxis_title="Mm³/d", height=300,
            margin=dict(t=10,b=40,l=50,r=10), hovermode="x unified"
        )
        st.plotly_chart(fig_gas, use_container_width=True)

    # Acumulada + GOR
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("📈 Producción Acumulada (m³)")
        fig_cum = go.Figure()
        for pozo in pozos_sel:
            d = df[df["pozo"] == pozo]
            fig_cum.add_trace(go.Scatter(
                x=d["fecha"], y=d["cum_oil"], name=pozo, mode="lines",
                fill="tozeroy",
                fillcolor=hex_to_rgba(COLOR_MAP[pozo], 0.15),
                line=dict(color=COLOR_MAP[pozo], width=2),
                hovertemplate=f"<b>{pozo}</b><br>%{{x|%b %y}}<br>%{{y:,.0f}} m³<extra></extra>"
            ))
        fig_cum.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", yaxis_title="m³ acumulados", height=300,
            margin=dict(t=10,b=40,l=60,r=10), hovermode="x unified"
        )
        st.plotly_chart(fig_cum, use_container_width=True)

    with col4:
        st.subheader("⚗️ GOR y Corte de Agua")
        fig_gor = make_subplots(specs=[[{"secondary_y": True}]])
        for pozo in pozos_sel:
            d = df[df["pozo"] == pozo]
            fig_gor.add_trace(go.Scatter(
                x=d["fecha"], y=d["gor"], name=f"GOR {pozo}", mode="lines",
                line=dict(color=COLOR_MAP[pozo], width=2),
                hovertemplate=f"GOR {pozo}: %{{y:.0f}} m³/m³<extra></extra>"
            ), secondary_y=False)
            fig_gor.add_trace(go.Scatter(
                x=d["fecha"], y=d["wc"], name=f"WC {pozo}", mode="lines",
                line=dict(color=COLOR_MAP[pozo], width=1.5, dash="dot"),
                hovertemplate=f"WC {pozo}: %{{y:.1f}}%<extra></extra>"
            ), secondary_y=True)
        fig_gor.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", height=300,
            margin=dict(t=10,b=40,l=50,r=50), hovermode="x unified"
        )
        fig_gor.update_yaxes(title_text="GOR (m³/m³)", secondary_y=False)
        fig_gor.update_yaxes(title_text="WC (%)", secondary_y=True)
        st.plotly_chart(fig_gor, use_container_width=True)

    # Tabla
    st.markdown("---")
    with st.expander("📋 Ver tabla de datos"):
        df_t = df[["fecha","pozo","oil_m3d","gas_mm3d","gor","wc","cum_oil"]].copy()
        df_t.columns = ["Fecha","Pozo","Petróleo (m³/d)","Gas (Mm³/d)","GOR (m³/m³)","WC (%)","Acum. (m³)"]
        df_t["Fecha"] = df_t["Fecha"].dt.strftime("%b %Y")
        st.dataframe(df_t, use_container_width=True, hide_index=True)
        csv = df_t.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Descargar CSV", csv, "produccion_pad_lom01.csv", "text/csv")

# ════════════════════════════════════════════════════════════
# TAB 2: TRAYECTORIAS 3D
# ════════════════════════════════════════════════════════════
with tab2:

    col_3d, col_info = st.columns([3, 1])

    with col_info:
        st.subheader("🪨 Columna Estratigráfica")
        for s in STRAT:
            is_target = s["name"] == "VM Inferior"
            label = f"🎯 **{s['name']}**" if is_target else f"**{s['name']}**"
            st.markdown(
                f"<div style='border-left:3px solid {s['color']};padding:6px 10px;"
                f"margin-bottom:6px;background:{'#f7816611' if is_target else '#ffffff08'};"
                f"border-radius:0 6px 6px 0'>"
                f"{label}<br>"
                f"<span style='font-size:0.75rem;color:#8b949e'>{s['top']:,}–{s['base']:,} m TVD</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        st.markdown("---")
        st.markdown("**Parámetros del modelo**")
        st.caption("📐 Azimut: N 90° E")
        st.caption("↗ Buzamiento: ~3° E")
        st.caption("⬇ KOP: 900 m TVD")
        st.caption("🎯 Target: 3.150 m TVD")
        st.caption("📏 Rama horiz.: 3.200 m")
        st.caption("↔ Espaciado: 300 m")

    with col_3d:
        st.subheader("Vista 3D — Trayectorias + Estratigrafía")

        fig3d = go.Figure()

        # Superficies estratigráficas con go.Surface
        for s in surfaces:
            fig3d.add_trace(go.Surface(
                x=s["xg"], y=s["yg"], z=s["Z"],
                surfacecolor=s["C"],
                colorscale=make_colorscale(s["color"]),
                opacity=0.55 if s["is_target"] else 0.22,
                showscale=False,
                name=s["name"],
                showlegend=True,
                hovertemplate=f"<b>{s['name']}</b><br>E: %{{x:.0f}} m<br>N: %{{y:.0f}} m<br>TVD: %{{z:.0f}} m<extra></extra>",
                lighting=dict(ambient=0.9, diffuse=0.3)
            ))

        # Trayectorias
        for i, name in enumerate(NAMES):
            xs, ys, zs = trajs[name]
            fig3d.add_trace(go.Scatter3d(
                x=xs, y=ys, z=zs, name=name, mode="lines",
                line=dict(color=COLORS[i], width=6),
                hovertemplate=f"<b>{name}</b><br>E: %{{x:.0f}} m<br>N: %{{y:.0f}} m<br>TVD: %{{z:.0f}} m<extra></extra>"
            ))

        # Guías verticales punteadas
        for i in range(4):
            fig3d.add_trace(go.Scatter3d(
                x=[0,0], y=[i*300, i*300], z=[0,-900],
                mode="lines", line=dict(color=COLORS[i], width=1, dash="dot"),
                showlegend=False, hoverinfo="skip"
            ))

        # Bocas de pozo
        fig3d.add_trace(go.Scatter3d(
            x=[0,0,0,0], y=[0,300,600,900], z=[0,0,0,0],
            mode="markers+text", text=NAMES,
            textposition="top center",
            textfont=dict(color="#e6edf3", size=10),
            marker=dict(size=6, color=COLORS),
            name="Bocas de pozo",
            hovertemplate="<b>%{text}</b><br>Superficie<extra></extra>"
        ))

        fig3d.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8b949e", size=11),
            margin=dict(t=10, b=10, l=0, r=0),
            height=600,
            scene=dict(
                bgcolor="#0d1117",
                xaxis=dict(title="Este (m)",  gridcolor="#21262d", linecolor="#30363d"),
                yaxis=dict(title="Norte (m)", gridcolor="#21262d", linecolor="#30363d"),
                zaxis=dict(title="TVD (m)",   gridcolor="#21262d", linecolor="#30363d"),
                camera=dict(eye=dict(x=-1.6, y=-1.4, z=0.8)),
                aspectmode="manual",
                aspectratio=dict(x=2.2, y=1.2, z=1)
            ),
            legend=dict(bgcolor="#161b22", bordercolor="#30363d",
                        borderwidth=1, font=dict(size=10))
        )
        st.plotly_chart(fig3d, use_container_width=True)

        # Perfil vertical 2D
        with st.expander("📐 Ver perfil vertical (Este vs TVD)"):
            dip = np.tan(3 * np.pi / 180)
            fig2d = go.Figure()
            xr = [-300, 3700]
            for s in STRAT:
                tl = -(s["top"]  + xr[0]*dip); tr = -(s["top"]  + xr[1]*dip)
                bl = -(s["base"] + xr[0]*dip); br = -(s["base"] + xr[1]*dip)
                fig2d.add_trace(go.Scatter(
                    x=[xr[0],xr[1],xr[1],xr[0],xr[0]],
                    y=[tl,tr,br,bl,tl],
                    fill="toself",
                    fillcolor=hex_to_rgba(s["color"], 0.18 if s["name"]=="VM Inferior" else 0.07),
                    line=dict(color=s["color"],
                              width=1.5 if s["name"]=="VM Inferior" else 0.5,
                              dash="solid" if s["name"]=="VM Inferior" else "dot"),
                    showlegend=False,
                    hovertemplate=f"<b>{s['name']}</b><extra></extra>"
                ))
            for i, name in enumerate(NAMES):
                xs, _, zs = trajs[name]
                fig2d.add_trace(go.Scatter(
                    x=xs, y=zs, name=name, mode="lines",
                    line=dict(color=COLORS[i], width=2.5),
                    hovertemplate=f"<b>{name}</b><br>E: %{{x:.0f}} m<br>TVD: %{{y:.0f}} m<extra></extra>"
                ))
            fig2d.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)", height=320,
                margin=dict(t=10,b=50,l=65,r=20),
                xaxis=dict(title="Desplazamiento Este (m)", gridcolor="#21262d", zeroline=False),
                yaxis=dict(title="TVD (m)", gridcolor="#21262d", zeroline=False),
                hovermode="closest"
            )
            st.plotly_chart(fig2d, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────
st.markdown("---")
st.caption("Dashboard · Datos sintéticos · Desarrollado con Streamlit + Plotly · Cuenca Neuquina")
