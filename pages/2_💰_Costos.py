# -*- coding: utf-8 -*-
"""Página de análisis de costos CAPEX / OPEX / TCO."""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from engine import (
    CostGeneralInputs,
    CostCapexDiesel, CostCapexOvernight, CostCapexFlash,
    CostCapexOpportunity, CostCapexHydrogen,
    CostOpexDiesel, CostOpexOvernight, CostOpexFlash,
    CostOpexOpportunity, CostOpexHydrogen,
    calc_all_costs,
)
from utils import (
    TECH_COLORS, TECH_ICONS, TECH_NAMES, TECH_SHORT,
    inject_css, format_eur, generate_excel_report,
)

# ─────────────────────────────────────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title='Costos – Tecnologías de Buses',
    page_icon='💰',
    layout='wide',
    initial_sidebar_state='expanded',
)

inject_css()

# ─────────────────────────────────────────────────────────────────────────────
# Verificar que existan resultados operacionales
# ─────────────────────────────────────────────────────────────────────────────

if 'operational_results' not in st.session_state:
    st.warning(
        "⚠️ No se encontraron resultados operacionales. "
        "Primero configura los parámetros en la página **🚌 Operación** (app.py) "
        "y luego vuelve aquí."
    )
    st.stop()

op_results = st.session_state['operational_results']

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar – Parámetros financieros generales
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 💰 Parámetros financieros")
    st.caption("Configura horizonte y días de operación")
    st.markdown("---")

    horizonte = st.number_input(
        'Horizonte del proyecto (años)',
        min_value=1, max_value=40, value=15, step=1,
        help="Vida útil del proyecto para calcular el TCO",
    )
    dias_anio = st.number_input(
        'Días de operación / año',
        min_value=100, max_value=365, value=365, step=5,
    )

    cost_general = CostGeneralInputs(
        horizonte_anios=horizonte,
        dias_operacion_anio=dias_anio,
    )

    # Resumen operacional rápido
    st.markdown("---")
    st.markdown("### 📋 Resumen operacional")
    for key, data in op_results.items():
        name = TECH_NAMES.get(key, key)
        icon = TECH_ICONS.get(name, '🚌')
        st.markdown(f"**{icon} {TECH_SHORT.get(name, name)}**: {data['flota_requerida']} buses")

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("# 💰 Análisis de Costos")
st.markdown("CAPEX, OPEX y Costo Total de Propiedad (TCO) por tecnología")
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Inputs de costos por tecnología (tabs)
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("## Parámetros de costos por tecnología")

cost_tabs = st.tabs([
    '⛽ Diesel', '🔋 Nocturna', '⚡ Flash', '🔌 Oportunidad', '💧 Hidrógeno'
])

# --- Diesel ---
capex_diesel = None
opex_diesel = None
if 'diesel' in op_results:
    with cost_tabs[0]:
        st.markdown("#### CAPEX")
        c1, c2 = st.columns(2)
        with c1:
            d_vehiculo = st.number_input(
                'Vehículo (€)', min_value=0.0, value=250_000.0,
                step=10_000.0, key='cd_veh',
                help="Precio unitario del bus diésel",
            )
        with c2:
            d_deposito = st.number_input(
                'Infra depósito (€/bus)', min_value=0.0, value=15_000.0,
                step=1_000.0, key='cd_dep',
            )
        capex_diesel = CostCapexDiesel(
            vehiculo_eur=d_vehiculo,
            infraestructura_deposito_eur_bus=d_deposito,
        )

        st.markdown("#### OPEX")
        c1, c2 = st.columns(2)
        with c1:
            d_comb = st.number_input(
                'Diésel (€/litro)', min_value=0.0, value=1.50,
                step=0.05, key='cd_comb',
            )
        with c2:
            d_mant = st.number_input(
                'Mantenimiento (€/km)', min_value=0.0, value=0.30,
                step=0.01, key='cd_mant',
            )
        opex_diesel = CostOpexDiesel(
            combustible_eur_litro=d_comb,
            mantenimiento_eur_km=d_mant,
        )
else:
    with cost_tabs[0]:
        st.info("Tecnología no configurada en la página de operación")

# --- Overnight ---
capex_overnight = None
opex_overnight = None
if 'overnight' in op_results:
    with cost_tabs[1]:
        st.markdown("#### CAPEX")
        c1, c2, c3 = st.columns(3)
        with c1:
            on_vehiculo = st.number_input(
                'Vehículo (€)', min_value=0.0, value=450_000.0,
                step=10_000.0, key='con_veh',
            )
            on_carg = st.number_input(
                'Cargador pistola (€/ud)', min_value=0.0, value=40_000.0,
                step=5_000.0, key='con_carg',
            )
        with c2:
            on_sub = st.number_input(
                'Subestación eléctrica (€)', min_value=0.0, value=200_000.0,
                step=10_000.0, key='con_sub',
            )
        with c3:
            on_dep = st.number_input(
                'Infra depósito (€/bus)', min_value=0.0, value=20_000.0,
                step=1_000.0, key='con_dep',
            )
        capex_overnight = CostCapexOvernight(
            vehiculo_eur=on_vehiculo,
            cargador_pistola_eur=on_carg,
            subestacion_electrica_eur=on_sub,
            infraestructura_deposito_eur_bus=on_dep,
        )

        st.markdown("#### OPEX")
        c1, c2, c3 = st.columns(3)
        with c1:
            on_en = st.number_input(
                'Energía (€/kWh)', min_value=0.0, value=0.12,
                step=0.01, key='con_en',
            )
            on_mant = st.number_input(
                'Mantenimiento (€/km)', min_value=0.0, value=0.18,
                step=0.01, key='con_mant',
            )
        with c2:
            on_bat_a = st.number_input(
                'Batería mant. anual (€/bus)', min_value=0.0, value=2_000.0,
                step=500.0, key='con_bata',
            )
        with c3:
            on_bat_r = st.number_input(
                'Reemplazo batería (€)', min_value=0.0, value=80_000.0,
                step=5_000.0, key='con_batr',
            )
            on_bat_v = st.number_input(
                'Vida útil batería (años)', min_value=1, value=8,
                step=1, key='con_batv',
            )
        opex_overnight = CostOpexOvernight(
            energia_eur_kwh=on_en,
            mantenimiento_eur_km=on_mant,
            bateria_mantenimiento_anual_eur_bus=on_bat_a,
            bateria_reemplazo_eur=on_bat_r,
            bateria_vida_util_anios=on_bat_v,
        )
else:
    with cost_tabs[1]:
        st.info("Tecnología no configurada en la página de operación")

# --- Flash ---
capex_flash = None
opex_flash = None
if 'flash' in op_results:
    with cost_tabs[2]:
        st.markdown("#### CAPEX")
        c1, c2, c3 = st.columns(3)
        with c1:
            fl_vehiculo = st.number_input(
                'Vehículo (€)', min_value=0.0, value=500_000.0,
                step=10_000.0, key='cf_veh',
            )
            fl_pant = st.number_input(
                'Cargador pantógrafo cabecera (€/ud)', min_value=0.0, value=350_000.0,
                step=10_000.0, key='cf_pant',
            )
        with c2:
            fl_pist = st.number_input(
                'Cargador pistola patio (€/ud)', min_value=0.0, value=40_000.0,
                step=5_000.0, key='cf_pist',
            )
            fl_sub = st.number_input(
                'Subestación eléctrica (€)', min_value=0.0, value=300_000.0,
                step=10_000.0, key='cf_sub',
            )
        with c3:
            fl_dep = st.number_input(
                'Infra depósito (€/bus)', min_value=0.0, value=20_000.0,
                step=1_000.0, key='cf_dep',
            )
        capex_flash = CostCapexFlash(
            vehiculo_eur=fl_vehiculo,
            cargador_pantografo_cabecera_eur=fl_pant,
            cargador_pistola_patio_eur=fl_pist,
            subestacion_electrica_eur=fl_sub,
            infraestructura_deposito_eur_bus=fl_dep,
        )

        st.markdown("#### OPEX")
        c1, c2, c3 = st.columns(3)
        with c1:
            fl_en = st.number_input(
                'Energía (€/kWh)', min_value=0.0, value=0.12,
                step=0.01, key='cf_en',
            )
            fl_mant = st.number_input(
                'Mantenimiento (€/km)', min_value=0.0, value=0.18,
                step=0.01, key='cf_mant',
            )
        with c2:
            fl_bat_a = st.number_input(
                'Batería mant. anual (€/bus)', min_value=0.0, value=2_000.0,
                step=500.0, key='cf_bata',
            )
        with c3:
            fl_bat_r = st.number_input(
                'Reemplazo batería (€)', min_value=0.0, value=80_000.0,
                step=5_000.0, key='cf_batr',
            )
            fl_bat_v = st.number_input(
                'Vida útil batería (años)', min_value=1, value=8,
                step=1, key='cf_batv',
            )
        opex_flash = CostOpexFlash(
            energia_eur_kwh=fl_en,
            mantenimiento_eur_km=fl_mant,
            bateria_mantenimiento_anual_eur_bus=fl_bat_a,
            bateria_reemplazo_eur=fl_bat_r,
            bateria_vida_util_anios=fl_bat_v,
        )
else:
    with cost_tabs[2]:
        st.info("Tecnología no configurada en la página de operación")

# --- Oportunidad ---
capex_opportunity = None
opex_opportunity = None
if 'opportunity' in op_results:
    with cost_tabs[3]:
        st.markdown("#### CAPEX")
        c1, c2, c3 = st.columns(3)
        with c1:
            op_vehiculo = st.number_input(
                'Vehículo (€)', min_value=0.0, value=480_000.0,
                step=10_000.0, key='co_veh',
            )
            op_carg = st.number_input(
                'Cargador oportunidad cabecera (€/ud)', min_value=0.0, value=250_000.0,
                step=10_000.0, key='co_carg',
            )
        with c2:
            op_pist = st.number_input(
                'Cargador pistola patio (€/ud)', min_value=0.0, value=40_000.0,
                step=5_000.0, key='co_pist',
            )
            op_sub = st.number_input(
                'Subestación eléctrica (€)', min_value=0.0, value=250_000.0,
                step=10_000.0, key='co_sub',
            )
        with c3:
            op_dep_c = st.number_input(
                'Infra depósito (€/bus)', min_value=0.0, value=20_000.0,
                step=1_000.0, key='co_dep',
            )
        capex_opportunity = CostCapexOpportunity(
            vehiculo_eur=op_vehiculo,
            cargador_oportunidad_cabecera_eur=op_carg,
            cargador_pistola_patio_eur=op_pist,
            subestacion_electrica_eur=op_sub,
            infraestructura_deposito_eur_bus=op_dep_c,
        )

        st.markdown("#### OPEX")
        c1, c2, c3 = st.columns(3)
        with c1:
            op_en = st.number_input(
                'Energía (€/kWh)', min_value=0.0, value=0.12,
                step=0.01, key='co_en',
            )
            op_mant = st.number_input(
                'Mantenimiento (€/km)', min_value=0.0, value=0.18,
                step=0.01, key='co_mant',
            )
        with c2:
            op_bat_a = st.number_input(
                'Batería mant. anual (€/bus)', min_value=0.0, value=2_000.0,
                step=500.0, key='co_bata',
            )
        with c3:
            op_bat_r = st.number_input(
                'Reemplazo batería (€)', min_value=0.0, value=80_000.0,
                step=5_000.0, key='co_batr',
            )
            op_bat_v = st.number_input(
                'Vida útil batería (años)', min_value=1, value=8,
                step=1, key='co_batv',
            )
        opex_opportunity = CostOpexOpportunity(
            energia_eur_kwh=op_en,
            mantenimiento_eur_km=op_mant,
            bateria_mantenimiento_anual_eur_bus=op_bat_a,
            bateria_reemplazo_eur=op_bat_r,
            bateria_vida_util_anios=op_bat_v,
        )
else:
    with cost_tabs[3]:
        st.info("Tecnología no configurada en la página de operación")

# --- Hidrógeno ---
capex_hydrogen = None
opex_hydrogen = None
if 'hydrogen' in op_results:
    with cost_tabs[4]:
        st.markdown("#### CAPEX")
        c1, c2, c3 = st.columns(3)
        with c1:
            h_vehiculo = st.number_input(
                'Vehículo (€)', min_value=0.0, value=600_000.0,
                step=10_000.0, key='ch_veh',
            )
        with c2:
            h_estacion = st.number_input(
                'Estación de hidrógeno (€)', min_value=0.0, value=1_500_000.0,
                step=50_000.0, key='ch_est',
            )
        with c3:
            h_dep = st.number_input(
                'Infra depósito (€/bus)', min_value=0.0, value=20_000.0,
                step=1_000.0, key='ch_dep',
            )
        capex_hydrogen = CostCapexHydrogen(
            vehiculo_eur=h_vehiculo,
            estacion_hidrogeno_eur=h_estacion,
            infraestructura_deposito_eur_bus=h_dep,
        )

        st.markdown("#### OPEX")
        c1, c2 = st.columns(2)
        with c1:
            h_h2 = st.number_input(
                'Hidrógeno (€/kg)', min_value=0.0, value=6.00,
                step=0.50, key='ch_h2',
            )
        with c2:
            h_mant = st.number_input(
                'Mantenimiento (€/km)', min_value=0.0, value=0.25,
                step=0.01, key='ch_mant',
            )
        opex_hydrogen = CostOpexHydrogen(
            hidrogeno_eur_kg=h_h2,
            mantenimiento_eur_km=h_mant,
        )
else:
    with cost_tabs[4]:
        st.info("Tecnología no configurada en la página de operación")


# ─────────────────────────────────────────────────────────────────────────────
# Ejecutar cálculos de costos
# ─────────────────────────────────────────────────────────────────────────────

cost_results = calc_all_costs(
    operational_results=op_results,
    cost_general=cost_general,
    capex_diesel=capex_diesel,
    capex_overnight=capex_overnight,
    capex_flash=capex_flash,
    capex_opportunity=capex_opportunity,
    capex_hydrogen=capex_hydrogen,
    opex_diesel=opex_diesel,
    opex_overnight=opex_overnight,
    opex_flash=opex_flash,
    opex_opportunity=opex_opportunity,
    opex_hydrogen=opex_hydrogen,
)

if not cost_results:
    st.info("No se pudieron calcular costos. Verifica que hayas configurado las tecnologías.")
    st.stop()

# Guardar en session_state para la exportación
st.session_state['cost_results'] = cost_results
st.session_state['cost_general'] = cost_general

# Construir dict de inputs de costos para la exportación
_cost_inputs_export: dict = {}
if 'diesel' in cost_results:
    _cost_inputs_export['diesel'] = {'capex': capex_diesel, 'opex': opex_diesel}
if 'overnight' in cost_results:
    _cost_inputs_export['overnight'] = {'capex': capex_overnight, 'opex': opex_overnight}
if 'flash' in cost_results:
    _cost_inputs_export['flash'] = {'capex': capex_flash, 'opex': opex_flash}
if 'opportunity' in cost_results:
    _cost_inputs_export['opportunity'] = {'capex': capex_opportunity, 'opex': opex_opportunity}
if 'hydrogen' in cost_results:
    _cost_inputs_export['hydrogen'] = {'capex': capex_hydrogen, 'opex': opex_hydrogen}
st.session_state['cost_inputs'] = _cost_inputs_export


# ─────────────────────────────────────────────────────────────────────────────
# Tarjetas resumen por tecnología
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("## 📊 Resumen de costos")

cols = st.columns(len(cost_results))

for i, (key, cdata) in enumerate(cost_results.items()):
    tech_name = TECH_NAMES.get(key, key)
    color = TECH_COLORS.get(tech_name, '#666')
    icon = TECH_ICONS.get(tech_name, '🚌')
    short = TECH_SHORT.get(tech_name, tech_name)

    capex_total = cdata['capex']['total_capex']
    opex_total = cdata['opex']['total_opex_anual']
    tco_total = cdata['tco']['total_tco']
    flota = op_results[key]['flota_requerida']
    km_dia = op_results[key]['km_totales_dia']
    km_anual = km_dia * cost_general.dias_operacion_anio
    costo_km = tco_total / (km_anual * horizonte) if km_anual > 0 else 0

    with cols[i]:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid {color};">
            <div style="font-size: 28px; margin-bottom: 4px;">{icon}</div>
            <div style="font-size: 13px; font-weight: 600; color: {color}; margin-bottom: 12px;">
                {short}
            </div>
            <div style="font-size: 11px; color: #86868b; text-transform: uppercase;">CAPEX</div>
            <div style="font-size: 22px; font-weight: 700; color: #1d1d1f; margin-bottom: 8px;">
                {format_eur(capex_total)}
            </div>
            <div style="font-size: 11px; color: #86868b; text-transform: uppercase;">OPEX / año</div>
            <div style="font-size: 22px; font-weight: 700; color: #1d1d1f; margin-bottom: 8px;">
                {format_eur(opex_total)}
            </div>
            <div style="padding-top: 12px; border-top: 1px solid #e5e5e7;">
                <div style="font-size: 11px; color: #86868b; text-transform: uppercase;">TCO ({horizonte} años)</div>
                <div style="font-size: 24px; font-weight: 700; color: {color};">
                    {format_eur(tco_total)}
                </div>
            </div>
            <div style="font-size: 11px; color: #86868b; margin-top: 8px;">
                {costo_km:.2f} €/km · {flota} buses
            </div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Gráficos
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("## 📈 Análisis visual")

chart_tabs = st.tabs([
    '📊 CAPEX vs OPEX',
    '🔍 Desglose CAPEX',
    '🔍 Desglose OPEX',
    '📈 Evolución TCO',
    '💶 Costo por km',
])

# ── Tab 0: CAPEX vs OPEX barras apiladas ──
with chart_tabs[0]:
    techs = []
    capex_vals = []
    opex_vals = []
    colors = []

    for key, cdata in cost_results.items():
        tech_name = TECH_NAMES.get(key, key)
        techs.append(TECH_SHORT.get(tech_name, tech_name))
        capex_vals.append(cdata['capex']['total_capex'])
        opex_vals.append(cdata['opex']['total_opex_anual'] * horizonte)
        colors.append(TECH_COLORS.get(tech_name, '#666'))

    fig_cv = go.Figure()
    fig_cv.add_trace(go.Bar(
        name='CAPEX', x=techs, y=capex_vals,
        marker_color='#1d1d1f', opacity=0.85,
        text=[format_eur(v) for v in capex_vals],
        textposition='inside', textfont=dict(color='white', size=11),
    ))
    fig_cv.add_trace(go.Bar(
        name=f'OPEX acum. ({horizonte} años)', x=techs, y=opex_vals,
        marker_color=colors, opacity=0.85,
        text=[format_eur(v) for v in opex_vals],
        textposition='inside', textfont=dict(color='white', size=11),
    ))
    fig_cv.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        title=dict(text='CAPEX vs OPEX acumulado', font=dict(size=18, color='#1d1d1f')),
        barmode='stack',
        xaxis=dict(showgrid=False, showline=False),
        yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False, title='€'),
        margin=dict(t=60, b=40, l=40, r=20),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=450,
    )
    st.plotly_chart(fig_cv, use_container_width=True)


# ── Tab 1: Desglose CAPEX barras apiladas ──
with chart_tabs[1]:
    capex_components = [
        ('Vehículos', 'vehiculos'),
        ('Carg. cabecera', 'cargadores_cabecera'),
        ('Carg. patio', 'cargadores_patio'),
        ('Subestación', 'subestacion'),
        ('Estación H₂', 'estacion_h2'),
        ('Infra depósito', 'infra_deposito'),
    ]
    comp_colors = ["#9d52f3", '#007AFF', '#34C759', "#FF0055", "#DEDC52", '#5856D6']

    techs_short = []
    for key in cost_results:
        tn = TECH_NAMES.get(key, key)
        techs_short.append(TECH_SHORT.get(tn, tn))

    fig_capex = go.Figure()
    for idx, (label, field) in enumerate(capex_components):
        vals = [cost_results[k]['capex'][field] for k in cost_results]
        if any(v > 0 for v in vals):
            fig_capex.add_trace(go.Bar(
                name=label, x=techs_short, y=vals,
                marker_color=comp_colors[idx % len(comp_colors)],
                text=[format_eur(v) if v > 0 else '' for v in vals],
                textposition='inside', textfont=dict(color='white', size=10),
            ))
    fig_capex.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        title=dict(text='Desglose CAPEX por componente', font=dict(size=18, color='#1d1d1f')),
        barmode='stack',
        xaxis=dict(showgrid=False, showline=False),
        yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False, title='€'),
        margin=dict(t=60, b=40, l=40, r=20),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=450,
    )
    st.plotly_chart(fig_capex, use_container_width=True)


# ── Tab 2: Desglose OPEX barras apiladas ──
with chart_tabs[2]:
    opex_components = [
        ('Combustible / Energía', 'combustible_energia'),
        ('Mantenimiento', 'mantenimiento'),
        ('Batería (mant. anual)', 'bateria_anual'),
    ]
    opex_colors = ["#F01EE5", "#3082DA", '#34C759']

    fig_opex = go.Figure()
    for idx, (label, field) in enumerate(opex_components):
        vals = [cost_results[k]['opex'][field] for k in cost_results]
        if any(v > 0 for v in vals):
            fig_opex.add_trace(go.Bar(
                name=label, x=techs_short, y=vals,
                marker_color=opex_colors[idx % len(opex_colors)],
                text=[format_eur(v) if v > 0 else '' for v in vals],
                textposition='inside', textfont=dict(color='white', size=10),
            ))
    fig_opex.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        title=dict(text='Desglose OPEX anual por componente', font=dict(size=18, color='#1d1d1f')),
        barmode='stack',
        xaxis=dict(showgrid=False, showline=False),
        yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False, title='€/año'),
        margin=dict(t=60, b=40, l=40, r=20),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=450,
    )
    st.plotly_chart(fig_opex, use_container_width=True)


# ── Tab 3: Evolución temporal del TCO ──
with chart_tabs[3]:
    fig_tco = go.Figure()

    for key, cdata in cost_results.items():
        tech_name = TECH_NAMES.get(key, key)
        short = TECH_SHORT.get(tech_name, tech_name)
        color = TECH_COLORS.get(tech_name, '#666')
        anual = cdata['tco']['anual']

        anios = [e['anio'] for e in anual]
        acum = [e['acumulado'] for e in anual]

        # Identificar años de reemplazo de batería (saltos)
        reemplazo_x = [e['anio'] for e in anual if e['reemplazo_bateria'] > 0]
        reemplazo_y = [e['acumulado'] for e in anual if e['reemplazo_bateria'] > 0]

        fig_tco.add_trace(go.Scatter(
            x=anios, y=acum,
            mode='lines',
            name=short,
            line=dict(color=color, width=3),
            hovertemplate='Año %{x}<br>Acumulado: €%{y:,.0f}<extra>' + short + '</extra>',
        ))
        if reemplazo_x:
            fig_tco.add_trace(go.Scatter(
                x=reemplazo_x, y=reemplazo_y,
                mode='markers',
                name=f'{short} – reemplazo bat.',
                marker=dict(color=color, size=10, symbol='diamond'),
                showlegend=True,
                hovertemplate='Reemplazo batería año %{x}<br>Acumulado: €%{y:,.0f}<extra></extra>',
            ))

    fig_tco.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        title=dict(text=f'Costo acumulado (TCO) — horizonte {horizonte} años', font=dict(size=18, color='#1d1d1f')),
        xaxis=dict(showgrid=False, showline=False, title='Año', dtick=1),
        yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False, title='€ acumulados'),
        margin=dict(t=60, b=40, l=40, r=20),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=500,
        hovermode='x unified',
    )
    st.plotly_chart(fig_tco, use_container_width=True)


# ── Tab 4: Costo por km ──
with chart_tabs[4]:
    tech_names_short = []
    costo_km_vals = []
    costo_bus_vals = []
    bar_colors = []

    for key, cdata in cost_results.items():
        tech_name = TECH_NAMES.get(key, key)
        short = TECH_SHORT.get(tech_name, tech_name)
        flota = op_results[key]['flota_requerida']
        km_anual = op_results[key]['km_totales_dia'] * cost_general.dias_operacion_anio
        tco = cdata['tco']['total_tco']

        tech_names_short.append(short)
        costo_km_vals.append(tco / (km_anual * horizonte) if km_anual > 0 else 0)
        costo_bus_vals.append(tco / flota if flota > 0 else 0)
        bar_colors.append(TECH_COLORS.get(tech_name, '#666'))

    col1, col2 = st.columns(2)

    with col1:
        fig_ckm = go.Figure()
        fig_ckm.add_trace(go.Bar(
            x=tech_names_short, y=costo_km_vals,
            marker_color=bar_colors,
            text=[f"{v:.2f}" for v in costo_km_vals],
            textposition='outside', textfont=dict(size=13, color='#1d1d1f'),
        ))
        fig_ckm.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            title=dict(text='Costo por km (€/km)', font=dict(size=18, color='#1d1d1f')),
            xaxis=dict(showgrid=False, showline=False),
            yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False, title='€/km'),
            margin=dict(t=60, b=40, l=40, r=20),
            height=400,
            showlegend=False,
        )
        st.plotly_chart(fig_ckm, use_container_width=True)

    with col2:
        fig_cbus = go.Figure()
        fig_cbus.add_trace(go.Bar(
            x=tech_names_short, y=costo_bus_vals,
            marker_color=bar_colors,
            text=[format_eur(v) for v in costo_bus_vals],
            textposition='outside', textfont=dict(size=11, color='#1d1d1f'),
        ))
        fig_cbus.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            title=dict(text='TCO por bus (€/bus)', font=dict(size=18, color='#1d1d1f')),
            xaxis=dict(showgrid=False, showline=False),
            yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False, title='€/bus'),
            margin=dict(t=60, b=40, l=40, r=20),
            height=400,
            showlegend=False,
        )
        st.plotly_chart(fig_cbus, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tabla comparativa detallada (al final)
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("## 📋 Comparativa detallada")

rows = []
for key, cdata in cost_results.items():
    tech_name = TECH_NAMES.get(key, key)
    short = TECH_SHORT.get(tech_name, tech_name)
    capex = cdata['capex']
    opex = cdata['opex']
    tco = cdata['tco']
    flota = op_results[key]['flota_requerida']
    km_anual = op_results[key]['km_totales_dia'] * cost_general.dias_operacion_anio

    rows.append({
        'Tecnología': short,
        'Flota': flota,
        'CAPEX Vehículos (€)': capex['vehiculos'],
        'CAPEX Carg. cabecera (€)': capex['cargadores_cabecera'],
        'CAPEX Carg. patio (€)': capex['cargadores_patio'],
        'CAPEX Subestación (€)': capex['subestacion'],
        'CAPEX Est. H₂ (€)': capex['estacion_h2'],
        'CAPEX Infra depósito (€)': capex['infra_deposito'],
        'CAPEX Total (€)': capex['total_capex'],
        'OPEX Comb./Energía (€/año)': opex['combustible_energia'],
        'OPEX Mantenimiento (€/año)': opex['mantenimiento'],
        'OPEX Batería anual (€/año)': opex['bateria_anual'],
        'OPEX Total (€/año)': opex['total_opex_anual'],
        'TCO Total (€)': tco['total_tco'],
        'Costo por km (€/km)': tco['total_tco'] / (km_anual * horizonte) if km_anual > 0 else 0,
        'Costo por bus (€/bus)': tco['total_tco'] / flota if flota > 0 else 0,
    })

df_comp = pd.DataFrame(rows)

# Transponer para mejor legibilidad
df_t = df_comp.set_index('Tecnología').T
st.dataframe(
    df_t.style.format(lambda v: f"{v:,.0f}" if isinstance(v, (int, float)) and abs(v) >= 1 else f"{v:.2f}" if isinstance(v, float) else v),
    use_container_width=True,
    height=620,
)


# ─────────────────────────────────────────────────────────────────────────────
# Exportar a Excel (completo: Inputs + Operación + Costos)
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")

_excel_buf = generate_excel_report(
    operational_results=op_results,
    general_inputs=st.session_state.get('general_inputs'),
    tech_inputs=st.session_state.get('tech_inputs'),
    cost_results=cost_results,
    cost_general=cost_general,
    cost_inputs=_cost_inputs_export,
)

st.download_button(
    label='📥 Exportar reporte completo a Excel',
    data=_excel_buf,
    file_name='comparador_completo.xlsx',
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
)

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #86868b; font-size: 12px; padding: 20px;">
    Análisis de Costos – Comparador de Tecnologías de Buses · IDOM
</div>
""", unsafe_allow_html=True)
