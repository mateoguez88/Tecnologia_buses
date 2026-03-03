# -*- coding: utf-8 -*-
"""Página de Análisis de Sensibilidad.

Permite explorar cómo varían los resultados operativos cuando se modifican
los parámetros generales de la ruta, tanto de forma individual (barrido
continuo) como en escenarios combinados definidos por el usuario.
"""

from __future__ import annotations

import math
from dataclasses import replace, asdict
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engine import GeneralInputs, run_all
from utils import TECH_COLORS, TECH_ICONS, TECH_NAMES, TECH_ORDER, TECH_SHORT, inject_css

# ─────────────────────────────────────────────────────────────────────────────
# Configuración de página
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sensibilidad | Tecnologías de Buses",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ─────────────────────────────────────────────────────────────────────────────
# Guard clause
# ─────────────────────────────────────────────────────────────────────────────

if "operational_results" not in st.session_state:
    st.warning(
        "⚠️ **Sin datos base.** Primero configura y ejecuta el análisis en la página principal (🚌 Inicio).",
        icon="⚠️",
    )
    st.stop()

base_g: GeneralInputs = st.session_state["general_inputs"]
tech_inputs: Dict[str, Any] = st.session_state["tech_inputs"]

# ─────────────────────────────────────────────────────────────────────────────
# Constantes y configuración de parámetros
# ─────────────────────────────────────────────────────────────────────────────

PARAM_LABELS: Dict[str, str] = {
    "km_trazado_sentido": "Longitud por sentido (km)",
    "velocidad_kmh": "Velocidad comercial (km/h)",
    "headway_min": "Headway (min)",
    "tiempo_servicio_min": "Tiempo de servicio (min)",
    "tiempo_entre_servicios_min": "Regulación en terminal (min)",
    "km_vacio_frac": "Km en vacío (%)",
}

PARAM_STEP: Dict[str, float] = {
    "km_trazado_sentido": 0.5,
    "velocidad_kmh": 1.0,
    "headway_min": 1.0,
    "tiempo_servicio_min": 10.0,
    "tiempo_entre_servicios_min": 0.5,
    "km_vacio_frac": 0.01,
}

PARAM_DISPLAY_FACTOR: Dict[str, float] = {
    "km_vacio_frac": 100.0,  # Mostrar como % en vez de fracción
}

PARAM_DISPLAY_SUFFIX: Dict[str, str] = {
    "km_trazado_sentido": " km",
    "velocidad_kmh": " km/h",
    "headway_min": " min",
    "tiempo_servicio_min": " min",
    "tiempo_entre_servicios_min": " min",
    "km_vacio_frac": "%",
}

PARAM_KEYS = list(PARAM_LABELS.keys())

# ─────────────────────────────────────────────────────────────────────────────
# Funciones auxiliares
# ─────────────────────────────────────────────────────────────────────────────

def run_scenario(g: GeneralInputs) -> Dict[str, Dict[str, Any]]:
    """Ejecuta run_all con los tech_inputs del session_state."""
    return run_all(
        g,
        diesel=tech_inputs.get("diesel"),
        overnight=tech_inputs.get("overnight"),
        flash=tech_inputs.get("flash"),
        opportunity=tech_inputs.get("opportunity"),
        hydrogen=tech_inputs.get("hydrogen"),
    )


def extract_metrics(results: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Extrae las métricas clave de los resultados de run_all.
    Retorna un dict keyed por tech_key con métricas normalizadas.
    """
    out = {}
    for key in TECH_ORDER:
        if key not in results:
            continue
        r = results[key]
        tech_name = r["tecnologia"]

        # Consumo energético según tecnología
        if key == "diesel":
            energia_val = r.get("combustible_total_l", 0)
            energia_label = "L/día"
        elif key == "hydrogen":
            energia_val = r.get("h2_total_kg", 0)
            energia_label = "kg H₂/día"
        else:
            energia_val = r.get("energia_total_dia_kwh") or r.get("energia_total_patio_kwh", 0)
            energia_label = "kWh/día"

        # Cargadores totales (solo eléctricos)
        cargadores_cab = r.get("n_cargadores_cabecera", 0) or 0
        cargadores_traz = r.get("n_cargadores_trazado", 0) or 0
        cargadores_patio = r.get("cargadores_patio", 0) or 0
        cargadores_total = cargadores_cab + cargadores_traz + cargadores_patio

        out[key] = {
            "tecnologia": tech_name,
            "flota_requerida": r.get("flota_requerida", 0),
            "km_comerciales_dia": r.get("km_comerciales_dia", 0),
            "cargadores_total": cargadores_total,
            "cargadores_patio": cargadores_patio,
            "cargadores_cabecera": cargadores_cab,
            "cargadores_trazado": cargadores_traz,
            "energia_val": energia_val,
            "energia_label": energia_label,
        }
    return out


def format_param_value(key: str, value: float) -> str:
    """Formatea un valor de parámetro para mostrar en etiquetas."""
    factor = PARAM_DISPLAY_FACTOR.get(key, 1.0)
    suffix = PARAM_DISPLAY_SUFFIX.get(key, "")
    display_val = value * factor
    if key == "km_vacio_frac":
        return f"{display_val:.0f}{suffix}"
    elif display_val == int(display_val):
        return f"{int(display_val)}{suffix}"
    else:
        return f"{display_val:.1f}{suffix}"


def plotly_layout_defaults() -> dict:
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
        xaxis=dict(gridcolor="rgba(0,0,0,0.06)", showgrid=True),
        yaxis=dict(gridcolor="rgba(0,0,0,0.06)", showgrid=True),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("# 📊 Análisis de Sensibilidad")
st.markdown(
    "Explora cómo cambian los resultados operativos al variar los parámetros de la ruta. "
    "Usa el **Barrido paramétrico** para ver curvas continuas o **Escenarios comparados** para comparar casos específicos."
)

# Resumen de caso base en sidebar
with st.sidebar:
    st.markdown("## 📌 Caso Base")
    st.caption("Valores configurados en la página principal")
    st.markdown("---")
    base_dict = asdict(base_g)
    for k, label in PARAM_LABELS.items():
        val = base_dict.get(k, "-")
        factor = PARAM_DISPLAY_FACTOR.get(k, 1.0)
        suffix = PARAM_DISPLAY_SUFFIX.get(k, "")
        if isinstance(val, float):
            display = f"{val * factor:.1f}{suffix}" if k == "km_vacio_frac" else f"{val:.1f}{suffix}"
        else:
            display = f"{val}{suffix}"
        st.metric(label=label, value=display)

st.markdown("---")

tab_barrido, tab_escenarios = st.tabs(["🔀 Barrido Paramétrico", "📋 Escenarios Comparados"])

# =============================================================================
# TAB 1 — BARRIDO PARAMÉTRICO
# =============================================================================

with tab_barrido:
    st.markdown("### Configuración del barrido")
    st.markdown(
        "Selecciona uno o varios parámetros para analizar su impacto. "
        "Cuando se seleccionan **múltiples parámetros**, todos varían **simultáneamente** "
        "desde su mínimo hasta su máximo (interpolación lineal)."
    )

    col_sel, col_steps = st.columns([3, 1])

    with col_sel:
        selected_params = st.multiselect(
            "Parámetros a variar",
            options=PARAM_KEYS,
            default=["km_trazado_sentido"],
            format_func=lambda k: PARAM_LABELS[k],
            key="sweep_params",
        )

    with col_steps:
        n_pasos = st.slider("Nº de pasos", min_value=5, max_value=30, value=10, key="sweep_steps")

    if not selected_params:
        st.info("Selecciona al menos un parámetro para comenzar el análisis.")
        st.stop()

    # ── Rangos por parámetro ──────────────────────────────────────────────────
    st.markdown("#### Rangos de variación")

    param_ranges: Dict[str, tuple[float, float]] = {}
    base_vals = asdict(base_g)

    range_cols = st.columns(min(len(selected_params), 3))
    for idx, param_key in enumerate(selected_params):
        col = range_cols[idx % 3]
        base_val = base_vals[param_key]
        factor = PARAM_DISPLAY_FACTOR.get(param_key, 1.0)
        suffix = PARAM_DISPLAY_SUFFIX.get(param_key, "")
        step = PARAM_STEP[param_key] * factor

        default_min = round(base_val * 0.6 * factor, 4)
        default_max = round(base_val * 1.4 * factor, 4)

        with col:
            st.markdown(f"**{PARAM_LABELS[param_key]}**")
            r_col1, r_col2 = st.columns(2)
            with r_col1:
                rmin_display = st.number_input(
                    f"Mín{suffix}",
                    value=float(default_min),
                    step=float(step),
                    key=f"rmin_{param_key}",
                    label_visibility="visible",
                )
            with r_col2:
                rmax_display = st.number_input(
                    f"Máx{suffix}",
                    value=float(default_max),
                    step=float(step),
                    key=f"rmax_{param_key}",
                    label_visibility="visible",
                )
            # Convertir back a unidades internas si es necesario
            rmin = rmin_display / factor
            rmax = rmax_display / factor
            param_ranges[param_key] = (rmin, rmax)

    # ── Cálculo del barrido ───────────────────────────────────────────────────
    sweep_results: List[Dict[str, Any]] = []
    t_values = np.linspace(0.0, 1.0, n_pasos)

    for t in t_values:
        # Interpolar todos los parámetros seleccionados
        overrides = {}
        for pk in selected_params:
            v_min, v_max = param_ranges[pk]
            overrides[pk] = v_min + t * (v_max - v_min)

        g_new = replace(base_g, **overrides)
        res = run_scenario(g_new)
        metrics = extract_metrics(res)

        row = {"t": t}
        # Eje X: si 1 param → valor real del param; si varios → % de variación
        if len(selected_params) == 1:
            pk = selected_params[0]
            row["x_val"] = overrides[pk] * PARAM_DISPLAY_FACTOR.get(pk, 1.0)
            row["x_base"] = base_vals[pk] * PARAM_DISPLAY_FACTOR.get(pk, 1.0)
        else:
            row["x_val"] = t * 100.0  # porcentaje 0–100
            row["x_base"] = None  # base está dentro del rango, no en 0%

        for tech_key, m in metrics.items():
            row[f"{tech_key}_flota"] = m["flota_requerida"]
            row[f"{tech_key}_km_com"] = m["km_comerciales_dia"]
            row[f"{tech_key}_cargadores"] = m["cargadores_total"]
            row[f"{tech_key}_energia"] = m["energia_val"]
            row[f"{tech_key}_energia_label"] = m["energia_label"]

        sweep_results.append(row)

    df_sweep = pd.DataFrame(sweep_results)

    # Encontrar posición del caso base en el eje X
    if len(selected_params) == 1:
        x_label = PARAM_LABELS[selected_params[0]]
        x_base = df_sweep["x_base"].iloc[0]
    else:
        x_label = "Variación simultánea (%)"
        # Calcular t del caso base para cada param
        t_bases = []
        for pk in selected_params:
            v_min, v_max = param_ranges[pk]
            base_v = base_vals[pk]
            if v_max != v_min:
                t_bases.append((base_v - v_min) / (v_max - v_min))
        x_base = float(np.mean(t_bases)) * 100.0 if t_bases else None

    available_techs = [k for k in TECH_ORDER if k in tech_inputs]

    def make_line_chart(y_col_suffix: str, title: str, y_label: str, only_keys=None) -> go.Figure:
        fig = go.Figure()
        keys = only_keys if only_keys else available_techs
        for tech_key in keys:
            if tech_key not in available_techs:
                continue
            col_name = f"{tech_key}_{y_col_suffix}"
            if col_name not in df_sweep.columns:
                continue
            tech_full = TECH_NAMES[tech_key]
            color = TECH_COLORS.get(tech_full, "#999")
            short = TECH_SHORT.get(tech_full, tech_full)
            fig.add_trace(
                go.Scatter(
                    x=df_sweep["x_val"],
                    y=df_sweep[col_name],
                    name=short,
                    mode="lines+markers",
                    marker=dict(size=6),
                    line=dict(color=color, width=2),
                )
            )
        # Línea de caso base
        if x_base is not None:
            fig.add_vline(
                x=x_base,
                line_dash="dash",
                line_color="rgba(100,100,100,0.5)",
                annotation_text="Base",
                annotation_position="top right",
                annotation_font_color="rgba(100,100,100,0.8)",
            )
        layout = plotly_layout_defaults()
        layout["title"] = title
        layout["xaxis"]["title"] = x_label
        layout["yaxis"]["title"] = y_label
        fig.update_layout(**layout)
        return fig

    st.markdown("---")
    st.markdown("### 📈 Resultados del barrido")

    # ── Una tarjeta por tecnología: min / mediana / max de buses en el barrido ─
    import statistics as _st
    _card_cols = st.columns(len(available_techs))
    for _ci, _tk in enumerate(available_techs):
        _col = f"{_tk}_flota"
        if _col not in df_sweep.columns:
            continue
        _tech_full = TECH_NAMES[_tk]
        _color = TECH_COLORS.get(_tech_full, "#666")
        _icon  = TECH_ICONS.get(_tech_full, "🚌")
        _short = _tech_full.replace("Eléctrico - ", "")
        _vals  = df_sweep[_col].tolist()
        _vmin  = int(min(_vals))
        _vmax  = int(max(_vals))
        _vmed  = int(_st.median(_vals))
        with _card_cols[_ci]:
            st.markdown(f"""
            <div class="metric-card" style="border-left:4px solid {_color};">
                <div style="display:flex;justify-content:space-between;
                            align-items:center;margin-bottom:6px;">
                    <div style="font-size:24px;">{_icon}</div>
                </div>
                <div style="font-size:11px;font-weight:600;color:{_color};
                            margin-bottom:10px;">{_short}</div>
                <div style="display:flex;align-items:flex-end;
                            justify-content:space-between;">
                    <div style="text-align:center;">
                        <div style="font-size:18px;font-weight:600;
                                    color:#86868b;line-height:1;">{_vmin}</div>
                        <div style="font-size:9px;color:#86868b;
                                    text-transform:uppercase;margin-top:2px;">Mín</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:36px;font-weight:700;
                                    color:#1d1d1f;line-height:1;">{_vmed}</div>
                        <div style="font-size:9px;color:#86868b;
                                    text-transform:uppercase;margin-top:2px;">Mediana</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:18px;font-weight:600;
                                    color:#86868b;line-height:1;">{_vmax}</div>
                        <div style="font-size:9px;color:#86868b;
                                    text-transform:uppercase;margin-top:2px;">Máx</div>
                    </div>
                </div>
                <div style="font-size:9px;color:#86868b;text-align:center;
                            text-transform:uppercase;letter-spacing:0.4px;
                            margin-top:6px;">Buses</div>
            </div>
            """, unsafe_allow_html=True)

    # Row 1: Flota + Km comerciales
    c1, c2 = st.columns(2)
    with c1:
        fig_flota = make_line_chart("flota", "Flota requerida", "Buses")
        st.plotly_chart(fig_flota, use_container_width=True)
    with c2:
        fig_km = make_line_chart("km_com", "Km comerciales / día", "Km")
        st.plotly_chart(fig_km, use_container_width=True)

    # Row 2: Cargadores (solo eléctricos) + Energía por tecnología
    electric_keys = [k for k in ["overnight", "flash", "opportunity"] if k in available_techs]

    c3, c4 = st.columns(2)
    with c3:
        if electric_keys:
            fig_carg = make_line_chart("cargadores", "Cargadores requeridos", "Unidades", only_keys=electric_keys)
            st.plotly_chart(fig_carg, use_container_width=True)
        else:
            st.info("Sin tecnologías eléctricas para mostrar cargadores.")

    with c4:
        # Energía: gráfico compuesto con eje secundario o figura por grupo
        fig_en = go.Figure()
        # Diesel — L/día (eje izquierdo)
        if "diesel" in available_techs and "diesel_energia" in df_sweep.columns:
            fig_en.add_trace(
                go.Scatter(
                    x=df_sweep["x_val"],
                    y=df_sweep["diesel_energia"],
                    name="Diesel (L/día)",
                    mode="lines+markers",
                    marker=dict(size=6),
                    line=dict(color=TECH_COLORS["Diesel"], width=2, dash="dot"),
                    yaxis="y2",
                )
            )
        # Eléctricos — kWh/día (eje derecho por defecto)
        for ek in electric_keys:
            col_name = f"{ek}_energia"
            if col_name not in df_sweep.columns:
                continue
            tech_full = TECH_NAMES[ek]
            fig_en.add_trace(
                go.Scatter(
                    x=df_sweep["x_val"],
                    y=df_sweep[col_name],
                    name=f"{TECH_SHORT[tech_full]} (kWh/día)",
                    mode="lines+markers",
                    marker=dict(size=6),
                    line=dict(color=TECH_COLORS[tech_full], width=2),
                )
            )
        # Hidrógeno — kg/día (eje izquierdo secundario)
        if "hydrogen" in available_techs and "hydrogen_energia" in df_sweep.columns:
            fig_en.add_trace(
                go.Scatter(
                    x=df_sweep["x_val"],
                    y=df_sweep["hydrogen_energia"],
                    name="H₂ (kg/día)",
                    mode="lines+markers",
                    marker=dict(size=6),
                    line=dict(color=TECH_COLORS["Hidrógeno"], width=2, dash="dashdot"),
                    yaxis="y3",
                )
            )
        if x_base is not None:
            fig_en.add_vline(
                x=x_base,
                line_dash="dash",
                line_color="rgba(100,100,100,0.5)",
                annotation_text="Base",
                annotation_position="top left",
                annotation_font_color="rgba(100,100,100,0.8)",
            )
        layout_en = plotly_layout_defaults()
        layout_en["title"] = "Consumo energético / día"
        layout_en["xaxis"]["title"] = x_label
        layout_en["yaxis"] = dict(title="kWh/día", gridcolor="rgba(0,0,0,0.06)")
        layout_en["yaxis2"] = dict(
            title="L Diesel/día",
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(color=TECH_COLORS["Diesel"]),
        )
        layout_en["yaxis3"] = dict(
            title="kg H₂/día",
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(color=TECH_COLORS["Hidrógeno"]),
            anchor="free",
            position=1.0,
        )
        fig_en.update_layout(**layout_en)
        st.plotly_chart(fig_en, use_container_width=True)

    # Tabla de datos detallada (expandible)
    with st.expander("📋 Ver tabla de datos del barrido"):
        display_cols = {"x_val": x_label}
        for tech_key in available_techs:
            short = TECH_SHORT.get(TECH_NAMES[tech_key], tech_key)
            display_cols[f"{tech_key}_flota"] = f"{short} — Flota"
            display_cols[f"{tech_key}_km_com"] = f"{short} — Km com."
            display_cols[f"{tech_key}_cargadores"] = f"{short} — Cargadores"
            display_cols[f"{tech_key}_energia"] = f"{short} — Energía"

        df_display = df_sweep[[c for c in display_cols if c in df_sweep.columns]].rename(
            columns={k: v for k, v in display_cols.items() if k in df_sweep.columns}
        )
        st.dataframe(df_display.style.format(precision=1), use_container_width=True)

# =============================================================================
# TAB 2 — ESCENARIOS COMPARADOS
# =============================================================================

with tab_escenarios:
    st.markdown("### Definir escenarios")
    st.markdown(
        "Añade filas en la tabla para definir escenarios personalizados. "
        "Puedes cambiar **múltiples parámetros** en cada escenario. "
        "La primera fila corresponde al **Caso Base** actual."
    )

    # Preparar DataFrame inicial con caso base
    base_row = {
        "Escenario": "Caso Base",
        "km_trazado_sentido": base_g.km_trazado_sentido,
        "velocidad_kmh": base_g.velocidad_kmh,
        "headway_min": base_g.headway_min,
        "tiempo_servicio_min": base_g.tiempo_servicio_min,
        "tiempo_entre_servicios_min": base_g.tiempo_entre_servicios_min,
        "km_vacio_frac": round(base_g.km_vacio_frac * 100.0, 1),  # Display as %
    }

    if "sensitivity_scenarios_df" not in st.session_state:
        st.session_state["sensitivity_scenarios_df"] = pd.DataFrame([
            base_row,
            {
                "Escenario": "Escenario A",
                "km_trazado_sentido": base_g.km_trazado_sentido,
                "velocidad_kmh": base_g.velocidad_kmh,
                "headway_min": base_g.headway_min,
                "tiempo_servicio_min": base_g.tiempo_servicio_min,
                "tiempo_entre_servicios_min": base_g.tiempo_entre_servicios_min,
                "km_vacio_frac": round(base_g.km_vacio_frac * 100.0, 1),
            },
        ])

    column_config = {
        "Escenario": st.column_config.TextColumn("Escenario", width="medium"),
        "km_trazado_sentido": st.column_config.NumberColumn(
            "Longitud (km)", min_value=0.1, max_value=200.0, step=0.5, format="%.1f km"
        ),
        "velocidad_kmh": st.column_config.NumberColumn(
            "Velocidad (km/h)", min_value=1.0, max_value=120.0, step=1.0, format="%.1f km/h"
        ),
        "headway_min": st.column_config.NumberColumn(
            "Headway (min)", min_value=1.0, max_value=60.0, step=1.0, format="%.0f min"
        ),
        "tiempo_servicio_min": st.column_config.NumberColumn(
            "T. Servicio (min)", min_value=60.0, max_value=1440.0, step=10.0, format="%.0f min"
        ),
        "tiempo_entre_servicios_min": st.column_config.NumberColumn(
            "Regulación (min)", min_value=0.0, max_value=60.0, step=0.5, format="%.1f min"
        ),
        "km_vacio_frac": st.column_config.NumberColumn(
            "Km vacío (%)", min_value=0.0, max_value=50.0, step=1.0, format="%.1f%%"
        ),
    }

    edited_df = st.data_editor(
        st.session_state["sensitivity_scenarios_df"].reset_index(drop=True),
        column_config=column_config,
        num_rows="dynamic",
        use_container_width=True,
        key="scenarios_editor",
        hide_index=True,
    )

    st.markdown("---")

    # Botón de cálculo
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        calc_btn = st.button("▶ Calcular Escenarios", type="primary", use_container_width=True)
    with col_info:
        st.markdown(
            f"*Se calcularán {len(edited_df)} escenario(s) para las {len(available_techs)} tecnologías configuradas.*"
        )

    if calc_btn or "sensitivity_scenarios_results" in st.session_state:
        if calc_btn:
            # Guardar tabla de escenarios y calcular
            st.session_state["sensitivity_scenarios_df"] = edited_df.reset_index(drop=True)
            scenarios_results: List[Dict[str, Any]] = []
            for _, row in edited_df.iterrows():
                scenario_name = str(row.get("Escenario", "Sin nombre"))
                try:
                    g_sc = GeneralInputs(
                        km_trazado_sentido=float(row["km_trazado_sentido"]),
                        velocidad_kmh=float(row["velocidad_kmh"]),
                        headway_min=float(row["headway_min"]),
                        tiempo_servicio_min=float(row["tiempo_servicio_min"]),
                        tiempo_entre_servicios_min=float(row["tiempo_entre_servicios_min"]),
                        km_vacio_frac=float(row["km_vacio_frac"]) / 100.0,  # % → fracción
                    )
                    res = run_scenario(g_sc)
                    metrics = extract_metrics(res)
                    scenarios_results.append({
                        "nombre": scenario_name,
                        "g": g_sc,
                        "metrics": metrics,
                    })
                except Exception as e:
                    st.warning(f"Error en escenario '{scenario_name}': {e}")

            st.session_state["sensitivity_scenarios_results"] = scenarios_results

        # ── Mostrar resultados ────────────────────────────────────────────────

        scenarios_data = st.session_state.get("sensitivity_scenarios_results", [])

        if not scenarios_data:
            st.info("No hay resultados disponibles. Pulsa **▶ Calcular Escenarios**.")
        else:
            st.markdown("### 📊 Resultados por escenario")
            scenario_names = [s["nombre"] for s in scenarios_data]

            def make_bar_chart(metric_key: str, title: str, y_label: str, only_keys=None) -> go.Figure:
                fig = go.Figure()
                keys = only_keys if only_keys else available_techs
                for tech_key in keys:
                    if tech_key not in available_techs:
                        continue
                    tech_full = TECH_NAMES[tech_key]
                    color = TECH_COLORS.get(tech_full, "#999")
                    short = TECH_SHORT.get(tech_full, tech_full)

                    y_vals = []
                    for sc in scenarios_data:
                        m = sc["metrics"].get(tech_key, {})
                        y_vals.append(m.get(metric_key, 0))

                    fig.add_trace(
                        go.Bar(
                            name=short,
                            x=scenario_names,
                            y=y_vals,
                            marker_color=color,
                        )
                    )
                layout = plotly_layout_defaults()
                layout["title"] = title
                layout["yaxis"]["title"] = y_label
                layout["xaxis"]["title"] = "Escenario"
                layout["barmode"] = "group"
                fig.update_layout(**layout)
                return fig

            # Fila 1: Flota + Km comerciales
            c1, c2 = st.columns(2)
            with c1:
                fig_s_flota = make_bar_chart("flota_requerida", "Flota requerida por escenario", "Buses")
                st.plotly_chart(fig_s_flota, use_container_width=True)
            with c2:
                fig_s_km = make_bar_chart("km_comerciales_dia", "Km comerciales / día por escenario", "Km")
                st.plotly_chart(fig_s_km, use_container_width=True)

            # Fila 2: Cargadores (eléctricos) + Energía
            c3, c4 = st.columns(2)
            with c3:
                if electric_keys:
                    fig_s_carg = make_bar_chart(
                        "cargadores_total",
                        "Cargadores requeridos por escenario",
                        "Unidades",
                        only_keys=electric_keys,
                    )
                    st.plotly_chart(fig_s_carg, use_container_width=True)
                else:
                    st.info("Sin tecnologías eléctricas para mostrar cargadores.")

            with c4:
                # Energía separada por tipo de unidad
                fig_s_en = go.Figure()

                if "diesel" in available_techs:
                    y_diesel = [sc["metrics"].get("diesel", {}).get("energia_val", 0) for sc in scenarios_data]
                    fig_s_en.add_trace(
                        go.Bar(
                            name="Diesel (L/día)",
                            x=scenario_names,
                            y=y_diesel,
                            marker_color=TECH_COLORS["Diesel"],
                            yaxis="y2",
                        )
                    )
                for ek in electric_keys:
                    tech_full = TECH_NAMES[ek]
                    y_el = [sc["metrics"].get(ek, {}).get("energia_val", 0) for sc in scenarios_data]
                    fig_s_en.add_trace(
                        go.Bar(
                            name=f"{TECH_SHORT[tech_full]} (kWh/día)",
                            x=scenario_names,
                            y=y_el,
                            marker_color=TECH_COLORS[tech_full],
                        )
                    )
                if "hydrogen" in available_techs:
                    y_h2 = [sc["metrics"].get("hydrogen", {}).get("energia_val", 0) for sc in scenarios_data]
                    fig_s_en.add_trace(
                        go.Bar(
                            name="H₂ (kg/día)",
                            x=scenario_names,
                            y=y_h2,
                            marker_color=TECH_COLORS["Hidrógeno"],
                            yaxis="y2",
                        )
                    )
                layout_se = plotly_layout_defaults()
                layout_se["title"] = "Consumo energético / día por escenario"
                layout_se["xaxis"]["title"] = "Escenario"
                layout_se["yaxis"] = dict(title="kWh/día", gridcolor="rgba(0,0,0,0.06)")
                layout_se["yaxis2"] = dict(
                    title="L / kg",
                    overlaying="y",
                    side="right",
                    showgrid=False,
                )
                layout_se["barmode"] = "group"
                fig_s_en.update_layout(**layout_se)
                st.plotly_chart(fig_s_en, use_container_width=True)

            # ── Tabla resumen detallada ───────────────────────────────────────
            st.markdown("---")
            st.markdown("### 📋 Tabla resumen")

            summary_rows = []
            for sc in scenarios_data:
                for tech_key in available_techs:
                    m = sc["metrics"].get(tech_key, {})
                    tech_full = TECH_NAMES[tech_key]
                    energia_label = m.get("energia_label", "—")
                    summary_rows.append({
                        "Escenario": sc["nombre"],
                        "Tecnología": TECH_SHORT.get(tech_full, tech_full),
                        "Flota (buses)": m.get("flota_requerida", "—"),
                        "Km com./día": round(m.get("km_comerciales_dia", 0), 0),
                        "Cargadores": m.get("cargadores_total", 0),
                        f"Energía ({energia_label})": round(m.get("energia_val", 0), 1),
                    })

            df_summary = pd.DataFrame(summary_rows)
            st.dataframe(df_summary, use_container_width=True, hide_index=True)

            # Parámetros de cada escenario
            with st.expander("⚙️ Ver parámetros de cada escenario"):
                param_rows = []
                for sc in scenarios_data:
                    g_sc = sc["g"]
                    param_rows.append({
                        "Escenario": sc["nombre"],
                        "Longitud (km)": g_sc.km_trazado_sentido,
                        "Velocidad (km/h)": g_sc.velocidad_kmh,
                        "Headway (min)": g_sc.headway_min,
                        "T. Servicio (min)": g_sc.tiempo_servicio_min,
                        "Regulación (min)": g_sc.tiempo_entre_servicios_min,
                        "Km vacío (%)": round(g_sc.km_vacio_frac * 100.0, 1),
                    })
                df_params = pd.DataFrame(param_rows)
                st.dataframe(df_params, use_container_width=True, hide_index=True)
