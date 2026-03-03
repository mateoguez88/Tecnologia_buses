# -*- coding: utf-8 -*-
"""App Streamlit para comparar tecnologías de operación.

Ejecuta:
  streamlit run app.py
"""

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from engine import (
    GeneralInputs, DieselInputs, ElectricOvernightInputs,
    ElectricFlashInputs, ElectricOpportunityInputs, HydrogenInputs,
    run_all
)
from utils import TECH_COLORS, TECH_ICONS, inject_css, generate_excel_report

# ─────────────────────────────────────────────────────────────────────────────
# Configuración y estilos
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title='Tecnologías de Buses',
    page_icon='🚌',
    layout='wide',
    initial_sidebar_state='expanded'
)

inject_css()
# ─────────────────────────────────────────────────────────────────────────────
# Sidebar - Inputs
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Parámetros")
    st.caption("Configura los inputs de operación")
    
    st.markdown("---")
    st.markdown("### Ruta")
    
    km_trazado = st.number_input(
        'Longitud por sentido (km)', 
        min_value=0.1, value=23.0, step=0.5,
        help="Kilómetros del trazado en un sentido"
    )
    n_estaciones = st.number_input(
        'Número de estaciones',
        min_value=2, value=max(2, round(23.0 / 0.5)), step=1,
        help="Estaciones totales de la ruta (incluye las 2 cabeceras). "
             "Regla orientativa: ~1 estación cada 500 m"
    )
    velocidad = st.number_input(
        'Velocidad comercial (km/h)', 
        min_value=1.0, value=25.0, step=1.0
    )
    
    st.markdown("### Operación")
    
    headway = st.number_input(
        'Headway (min)', 
        min_value=1.0, value=10.0, step=1.0,
        help="Frecuencia entre buses"
    )
    t_serv = st.number_input(
        'Tiempo de servicio (min)', 
        min_value=10.0, value=990.0, step=10.0,
        help="Ventana operativa diaria"
    )
    tes = st.number_input(
        'Regulación en terminal (min)', 
        min_value=0.0, value=5.0, step=0.5
    )
    km_vacio = st.slider(
        'Km en vacío (%)', 
        min_value=0, max_value=20, value=5,
        help="Porcentaje adicional de km no comerciales"
    ) / 100.0

    g = GeneralInputs(
        km_trazado_sentido=km_trazado,
        velocidad_kmh=velocidad,
        headway_min=headway,
        tiempo_servicio_min=t_serv,
        tiempo_entre_servicios_min=tes,
        km_vacio_frac=km_vacio,
        n_estaciones=n_estaciones,
    )

# ─────────────────────────────────────────────────────────────────────────────
# Header principal
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("# 🚌 Comparador de Tecnologías")
st.markdown("Análisis operativo y energético para flotas de buses")

st.markdown("---")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("⏱️ Tiempo ida", f"{g.tiempo_ida_min():.0f} min")
with col2:
    st.metric("🔄 Ciclo completo", f"{g.tiempo_ciclo_min():.0f} min")
with col3:
    st.metric("🚌 Flota mínima", f"{g.flota_por_headway()} buses")
with col4:
    st.metric("📍 Km comerciales", f"{g.km_comerciales_dia():,.0f}")
with col5:
    st.metric("📊 Km totales", f"{g.km_totales_dia():,.0f}")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Inputs por tecnología
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("## Configuración por tecnología")

tech_tabs = st.tabs(['⛽ Diesel', '🔋 Nocturna', '⚡ Flash', '🔌 Oportunidad', '💧 Hidrógeno'])

with tech_tabs[0]:
    col1, col2 = st.columns(2)
    with col1:
        consumo = st.number_input('Consumo (L/km)', min_value=0.01, value=0.44, step=0.01, key='d_cons')
    with col2:
        autonomia = st.number_input('Autonomía (km)', min_value=50.0, value=600.0, step=50.0, key='d_aut')
    diesel = DieselInputs(consumo_litros_km=consumo, autonomia_km=autonomia)

with tech_tabs[1]:
    col1, col2, col3 = st.columns(3)
    with col1:
        bateria = st.number_input('Batería (kWh)', min_value=50.0, value=350.0, step=10.0, key='on_bat')
        c_kwhkm = st.number_input('Consumo (kWh/km)', min_value=0.1, value=1.2, step=0.05, key='on_cons')
    with col2:
        soc = st.number_input('SOC reserva', min_value=0.0, max_value=0.5, value=0.20, step=0.01, key='on_soc')
        eta = st.number_input('Eficiencia carga', min_value=0.5, max_value=1.0, value=0.90, step=0.01, key='on_eta')
    with col3:
        carg_kw = st.number_input('Cargador (kW)', min_value=10.0, value=150.0, step=10.0, key='on_carg')
        ventana = st.number_input('Ventana carga (h)', min_value=1.0, value=6.0, step=0.5, key='on_vent')
    overnight = ElectricOvernightInputs(
        bateria_kwh=bateria, consumo_kwh_km=c_kwhkm, soc_reserva_frac=soc,
        cargador_kw=carg_kw, eficiencia_carga=eta, ventana_carga_h=ventana
    )

with tech_tabs[2]:
    col1, col2, col3 = st.columns(3)
    with col1:
        bateria_f = st.number_input('Batería (kWh)', min_value=50.0, value=350.0, step=10.0, key='fl_bat')
        c_kwhkm_f = st.number_input('Consumo (kWh/km)', min_value=0.1, value=1.2, step=0.05, key='fl_cons')
        soc_f = st.number_input('SOC reserva', min_value=0.0, max_value=0.5, value=0.20, step=0.01, key='fl_soc')
    with col2:
        eta_f = st.number_input('Eficiencia', min_value=0.5, max_value=1.0, value=0.90, step=0.01, key='fl_eta')
        carg_ruta = st.number_input('Cargador ruta (kW)', min_value=10.0, value=600.0, step=50.0, key='fl_ruta')
        t_carga_cab_f = st.number_input('Carga cabecera (min)', min_value=0.1, value=3.0, step=0.5, key='fl_tcarga_cab',
                                         help="Tiempo de carga en terminales (cabecera)")
    with col3:
        t_carga_traz_f_s = st.number_input('Carga trazado (s)', min_value=1.0, value=10.0, step=1.0, key='fl_tcarga_traz',
                                            help="Tiempo de carga en paradas intermedias (segundos)")
        t_reg_f = st.number_input('Tiempo regulación (min)', min_value=0.5, value=5.0, step=0.5, key='fl_reg',
                                   help="Tiempo en terminal entre servicios")
        carg_patio = st.number_input('Cargador patio (kW)', min_value=10.0, value=150.0, step=10.0, key='fl_patio')
        ventana_f = st.number_input('Ventana nocturna (h)', min_value=1.0, value=6.0, step=0.5, key='fl_vent')
    
    # Puntos de carga: automático vs manual
    st.markdown("**Puntos de carga en ruta**")
    modo_carg_f = st.radio("", ["Optimizar", "Definir manualmente"], key='fl_carg_cab_modo', horizontal=True,
                           help="'Optimizar' encuentra la combinación mínima de puntos (cabecera + trazado) "
                                "para mantener la flota en el mínimo. 'Definir manualmente' permite fijar los valores.")
    n_cab_f = None
    n_traz_f = None
    if modo_carg_f == "Definir manualmente":
        mc1, mc2 = st.columns(2)
        with mc1:
            n_cab_f = st.number_input('Puntos cabecera (0-2)', min_value=0, max_value=2, value=2, step=1, key='fl_n_cab',
                                       help="Puntos de carga en terminales (máx 2, uno por cabecera)")
        with mc2:
            n_traz_f = st.number_input('Puntos trazado', min_value=0, max_value=g.max_puntos_trazado, value=0, step=1, key='fl_n_traz',
                                        help=f"Puntos de carga en paradas intermedias (máx {g.max_puntos_trazado} = {n_estaciones} estaciones − 2 cabeceras)")
    
    flash = ElectricFlashInputs(
        bateria_kwh=bateria_f, consumo_kwh_km=c_kwhkm_f, soc_reserva_frac=soc_f,
        eficiencia_carga=eta_f, cargador_ruta_kw=carg_ruta,
        tiempo_carga_cabecera_min=t_carga_cab_f,
        tiempo_carga_trazado_min=t_carga_traz_f_s / 60.0,
        tiempo_regulacion_min=t_reg_f,
        cargador_patio_kw=carg_patio, ventana_carga_h=ventana_f,
        n_puntos_cabecera_override=n_cab_f,
        n_puntos_trazado_override=n_traz_f,
    )

with tech_tabs[3]:
    col1, col2, col3 = st.columns(3)
    with col1:
        bateria_o = st.number_input('Batería (kWh)', min_value=50.0, value=350.0, step=10.0, key='op_bat')
        c_kwhkm_o = st.number_input('Consumo (kWh/km)', min_value=0.1, value=1.2, step=0.05, key='op_cons')
        soc_o = st.number_input('SOC reserva', min_value=0.0, max_value=0.5, value=0.20, step=0.01, key='op_soc')
    with col2:
        eta_o = st.number_input('Eficiencia', min_value=0.5, max_value=1.0, value=0.90, step=0.01, key='op_eta')
        carg_ruta_o = st.number_input('Cargador ruta (kW)', min_value=10.0, value=200.0, step=10.0, key='op_ruta')
        t_carga_cab_o = st.number_input('Carga cabecera (min)', min_value=0.1, value=10.0, step=0.5, key='op_tcarga_cab',
                                         help="Tiempo de carga en terminales (cabecera). Se limita al tiempo de regulación.")
    with col3:
        t_carga_traz_o_s = st.number_input('Carga trazado (s)', min_value=1.0, value=10.0, step=1.0, key='op_tcarga_traz',
                                            help="Tiempo de carga en paradas intermedias (segundos)")
        t_reg_o = st.number_input('Tiempo regulación (min)', min_value=0.5, value=10.0, step=0.5, key='op_reg',
                                   help="Tiempo en terminal entre servicios")
        carg_patio_o = st.number_input('Cargador patio (kW)', min_value=10.0, value=150.0, step=10.0, key='op_patio')
        ventana_o = st.number_input('Ventana nocturna (h)', min_value=1.0, value=6.0, step=0.5, key='op_vent')
    
    # Modo de cálculo: optimizar flota vs restricción de mini-cargas
    st.markdown("**Modo de cálculo**")
    modo_o = st.radio("", ["Optimizar flota", "Restringir mini-cargas"], key='op_modo', horizontal=True,
                      help="'Optimizar flota' añade buses si se necesitan más mini-cargas que ciclos. 'Restringir' limita las mini-cargas y calcula la flota necesaria.")
    max_mc_o = None
    if modo_o == "Restringir mini-cargas":
        max_mc_o = st.number_input('Máx. mini-cargas/bus', min_value=0, value=2, step=1, key='op_max_mc')
    
    # Puntos de carga: automático vs manual
    st.markdown("**Puntos de carga en ruta**")
    modo_carg_o = st.radio("", ["Optimizar", "Definir manualmente"], key='op_carg_cab_modo', horizontal=True,
                           help="'Optimizar' encuentra la combinación mínima de puntos (cabecera + trazado) "
                                "para mantener la flota en el mínimo. 'Definir manualmente' permite fijar los valores.")
    n_cab_o = None
    n_traz_o = None
    if modo_carg_o == "Definir manualmente":
        mc1o, mc2o = st.columns(2)
        with mc1o:
            n_cab_o = st.number_input('Puntos cabecera (0-2)', min_value=0, max_value=2, value=2, step=1, key='op_n_cab',
                                       help="Puntos de carga en terminales (máx 2, uno por cabecera)")
        with mc2o:
            n_traz_o = st.number_input('Puntos trazado', min_value=0, max_value=g.max_puntos_trazado, value=0, step=1, key='op_n_traz',
                                        help=f"Puntos de carga en paradas intermedias (máx {g.max_puntos_trazado} = {n_estaciones} estaciones − 2 cabeceras)")
    
    opp = ElectricOpportunityInputs(
        bateria_kwh=bateria_o, consumo_kwh_km=c_kwhkm_o, soc_reserva_frac=soc_o,
        eficiencia_carga=eta_o, cargador_ruta_kw=carg_ruta_o,
        tiempo_carga_cabecera_min=t_carga_cab_o,
        tiempo_carga_trazado_min=t_carga_traz_o_s / 60.0,
        tiempo_regulacion_min=t_reg_o,
        cargador_patio_kw=carg_patio_o, ventana_carga_h=ventana_o,
        max_mini_cargas_restriccion=max_mc_o,
        n_puntos_cabecera_override=n_cab_o,
        n_puntos_trazado_override=n_traz_o,
    )

with tech_tabs[4]:
    col1, col2 = st.columns(2)
    with col1:
        aut_h = st.number_input('Autonomía (km)', min_value=50.0, value=500.0, step=50.0, key='h2_aut')
    with col2:
        cons_h = st.number_input('Consumo H₂ (kg/km)', min_value=0.01, value=0.10, step=0.01, key='h2_cons')
    hydro = HydrogenInputs(autonomia_km=aut_h, consumo_h2_kg_km=cons_h)

# ─────────────────────────────────────────────────────────────────────────────
# Ejecutar cálculos
# ─────────────────────────────────────────────────────────────────────────────

results = run_all(g, diesel=diesel, overnight=overnight, flash=flash, opportunity=opp, hydrogen=hydro)

# Guardar en session_state para compartir con la página de costos
st.session_state['operational_results'] = results
st.session_state['general_inputs'] = g
st.session_state['tech_inputs'] = {
    'diesel': diesel, 'overnight': overnight, 'flash': flash,
    'opportunity': opp, 'hydrogen': hydro,
}

st.markdown("---")
st.markdown("## 📊 Resultados")

# ─────────────────────────────────────────────────────────────────────────────
# Tarjetas de resumen por tecnología (mejoradas)
# ─────────────────────────────────────────────────────────────────────────────

cols = st.columns(5)

for i, (key, data) in enumerate(results.items()):
    tech_name = data['tecnologia']
    color = TECH_COLORS.get(tech_name, '#666')
    icon = TECH_ICONS.get(tech_name, '🚌')
    ciclos = data.get('ciclos_por_bus', '-')
    es_viable = data.get('es_viable', True)
    mini_cargas = data.get('mini_cargas_por_bus', 0)
    
    # Información adicional según tecnología
    extra_info = ""
    if 'autonomia_usable_km' in data:
        extra_info = f"Aut: {data['autonomia_usable_km']:.0f} km"
    elif 'autonomia_km' in data:
        extra_info = f"Aut: {data['autonomia_km']:.0f} km"
    
    # Indicador de viabilidad
    viabilidad_icon = "✅" if es_viable else "⚠️"
    viabilidad_color = "#34C759" if es_viable else "#FF9500"
    
    with cols[i]:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid {color};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="font-size: 28px;">{icon}</div>
                <div style="font-size: 14px; color: {viabilidad_color};">{viabilidad_icon}</div>
            </div>
            <div style="font-size: 13px; font-weight: 600; color: {color}; margin-bottom: 8px;">
                {tech_name.replace('Eléctrico - ', '')}
            </div>
            <div style="font-size: 36px; font-weight: 700; color: #1d1d1f;">
                {data['flota_requerida']}
            </div>
            <div style="font-size: 11px; color: #86868b; text-transform: uppercase; margin-bottom: 12px;">
                Buses
            </div>
            <div style="display: flex; justify-content: space-around; padding-top: 12px; border-top: 1px solid #e5e5e7;">
                <div style="text-align: center;">
                    <div style="font-size: 18px; font-weight: 600; color: #1d1d1f;">{ciclos}</div>
                    <div style="font-size: 9px; color: #86868b;">Ciclos</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 18px; font-weight: 600; color: #1d1d1f;">{mini_cargas if mini_cargas > 0 else '-'}</div>
                    <div style="font-size: 9px; color: #86868b;">Mini-cargas</div>
                </div>
            </div>
            <div style="font-size: 11px; color: #86868b; margin-top: 8px; text-align: center;">
                {extra_info}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN COMPARATIVO - Solo analítica, sin recomendaciones
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("## 📊 Resumen Comparativo")

# Calcular indicadores clave
def get_key_metrics(results):
    metrics = []
    for key, data in results.items():
        # Determinar string de repostaje según tecnología
        if 'combustible_total_l' in data:
            # Diesel
            repostaje_str = f"{data['combustible_total_l']:,.0f} L"
        elif 'h2_total_kg' in data:
            # Hidrógeno
            repostaje_str = f"{data['h2_total_kg']:,.0f} kg H₂"
        elif 'energia_total_dia_kwh' in data:
            # Eléctrico
            repostaje_str = f"{data['energia_total_dia_kwh']:,.0f} kWh"
        elif 'energia_total_patio_kwh' in data:
            repostaje_str = f"{data['energia_total_patio_kwh']:,.0f} kWh"
        else:
            repostaje_str = "-"
        
        m = {
            'tecnologia': data['tecnologia'],
            'flota': data['flota_requerida'],
            'flota_headway': data.get('flota_headway', data['flota_requerida']),
            'cargadores_total': data.get('cargadores_patio', 0) + data.get('n_cargadores_cabecera', 0),
            'potencia_total_kw': data.get('potencia_total_instalada_kw', 
                                          data.get('potencia_instalada_patio_kw', 0) + 
                                          data.get('potencia_instalada_cabecera_kw', 0)),
            'energia_dia_kwh': data.get('energia_total_dia_kwh', data.get('energia_total_patio_kwh', 0)),
            'mini_cargas': data.get('mini_cargas_por_bus', 0),
            'ciclos': data.get('ciclos_por_bus', 0),
            'autonomia_usable': data.get('autonomia_usable_km', data.get('autonomia_km', 0)),
            'autonomia_efectiva': data.get('autonomia_efectiva_km', data.get('autonomia_usable_km', data.get('autonomia_km', 0))),
            'km_por_bus': data.get('km_por_bus_tot', 0),
            'repostaje_str': repostaje_str,
        }
        metrics.append(m)
    return metrics

key_metrics = get_key_metrics(results)

# Tabla resumen con datos de repostaje
st.markdown("### Métricas principales")

df_exec = pd.DataFrame([
    {
        'Tecnología': m['tecnologia'].replace('Eléctrico - ', ''),
        'Flota': m['flota'],
        'Ciclos/bus': m['ciclos'],
        'Mini-cargas': m['mini_cargas'] if m['mini_cargas'] > 0 else '-',
        'Km/bus/día': f"{m['km_por_bus']:,.0f}",
        'Repostaje/día': m['repostaje_str'],
    }
    for m in key_metrics
])
st.dataframe(df_exec, use_container_width=True, hide_index=True)

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Gráficos comparativos detallados
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("## 📈 Análisis detallado")

chart_tabs = st.tabs(['🚌 Flota y operación', '⚡ Energía y potencia', '🔋 Infraestructura', '📋 Datos completos', '🔍 Detalle Flash/Oportunidad'])

df_results = pd.DataFrame([v for v in results.values()])
df_results['color'] = df_results['tecnologia'].map(TECH_COLORS)

with chart_tabs[0]:
    col1, col2 = st.columns(2)
    
    with col1:
        fig_fleet = go.Figure()
        for _, row in df_results.iterrows():
            fig_fleet.add_trace(go.Bar(
                x=[row['tecnologia'].replace('Eléctrico - ', '')],
                y=[row['flota_requerida']],
                marker_color=row['color'],
                text=[row['flota_requerida']],
                textposition='outside',
                textfont=dict(size=14, color='#1d1d1f')
            ))
        fig_fleet.update_layout(
            title=dict(text='Flota requerida', font=dict(size=18, color='#1d1d1f')),
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, showline=False),
            yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False, title='Buses'),
            margin=dict(t=60, b=40, l=40, r=20),
            height=400
        )
        st.plotly_chart(fig_fleet, use_container_width=True)
    
    with col2:
        fig_km = go.Figure()
        for _, row in df_results.iterrows():
            fig_km.add_trace(go.Bar(
                x=[row['tecnologia'].replace('Eléctrico - ', '')],
                y=[row.get('km_por_bus_tot', 0)],
                marker_color=row['color'],
                text=[f"{row.get('km_por_bus_tot', 0):,.0f}"],
                textposition='outside',
                textfont=dict(size=12, color='#1d1d1f')
            ))
        fig_km.update_layout(
            title=dict(text='Km por bus/día', font=dict(size=18, color='#1d1d1f')),
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, showline=False),
            yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False, title='Km'),
            margin=dict(t=60, b=40, l=40, r=20),
            height=400
        )
        st.plotly_chart(fig_km, use_container_width=True)
    
    # Gráfico adicional: Ciclos y Mini-cargas
    col3, col4 = st.columns(2)
    
    with col3:
        fig_ciclos = go.Figure()
        techs = []
        ciclos_data = []
        mini_cargas_data = []
        colors = []
        for _, row in df_results.iterrows():
            techs.append(row['tecnologia'].replace('Eléctrico - ', ''))
            ciclos_data.append(row.get('ciclos_por_bus', 0))
            mini_cargas_data.append(row.get('mini_cargas_por_bus', 0))
            colors.append(row['color'])
        
        fig_ciclos.add_trace(go.Bar(
            name='Ciclos/bus', x=techs, y=ciclos_data,
            marker_color=colors, opacity=0.8,
            text=ciclos_data, textposition='outside'
        ))
        fig_ciclos.update_layout(
            title=dict(text='Ciclos por bus/día', font=dict(size=18, color='#1d1d1f')),
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, showline=False),
            yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False),
            margin=dict(t=60, b=40, l=40, r=20),
            height=350
        )
        st.plotly_chart(fig_ciclos, use_container_width=True)
    
    with col4:
        # Solo mostrar mini-cargas para tecnologías que las usan
        mini_data = [(t, m) for t, m in zip(techs, mini_cargas_data) if m > 0]
        if mini_data:
            fig_mini = go.Figure()
            fig_mini.add_trace(go.Bar(
                x=[d[0] for d in mini_data],
                y=[d[1] for d in mini_data],
                marker_color=['#007AFF' if 'flash' in d[0].lower() else '#5856D6' for d in mini_data],
                text=[d[1] for d in mini_data],
                textposition='outside'
            ))
            fig_mini.update_layout(
                title=dict(text='Mini-cargas por bus/día', font=dict(size=18, color='#1d1d1f')),
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, showline=False),
                yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False),
                margin=dict(t=60, b=40, l=40, r=20),
                height=350
            )
            st.plotly_chart(fig_mini, use_container_width=True)
        else:
            st.info("No hay tecnologías con mini-cargas configuradas")

with chart_tabs[1]:
    electric_techs = ['overnight', 'flash', 'opportunity']
    electric_data = {k: v for k, v in results.items() if k in electric_techs}
    
    if electric_data:
        col1, col2 = st.columns(2)
        
        with col1:
            # Energía total (patio + cabecera)
            fig_energy = go.Figure()
            techs = []
            energia_patio = []
            energia_ruta = []
            for key, data in electric_data.items():
                techs.append(data['tecnologia'].replace('Eléctrico - ', ''))
                energia_patio.append(data.get('energia_total_patio_kwh', 0))
                energia_ruta.append(data.get('energia_total_ruta_kwh', 0))
            
            fig_energy.add_trace(go.Bar(
                name='Patio (nocturna)', x=techs, y=energia_patio,
                marker_color='#34C759',
                text=[f"{e:,.0f}" for e in energia_patio],
                textposition='inside'
            ))
            fig_energy.add_trace(go.Bar(
                name='Ruta (cab+traz)', x=techs, y=energia_ruta,
                marker_color='#FF9500',
                text=[f"{e:,.0f}" for e in energia_ruta],
                textposition='inside'
            ))
            fig_energy.update_layout(
                title=dict(text='Energía diaria requerida (kWh)', font=dict(size=18, color='#1d1d1f')),
                barmode='stack',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, showline=False),
                yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False),
                margin=dict(t=60, b=40, l=40, r=20),
                height=400,
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            st.plotly_chart(fig_energy, use_container_width=True)
        
        with col2:
            fig_power = go.Figure()
            techs = []
            patio_power = []
            cabecera_power = []
            for key, data in electric_data.items():
                techs.append(data['tecnologia'].replace('Eléctrico - ', ''))
                patio_power.append(data.get('potencia_instalada_patio_kw', 0))
                cabecera_power.append(data.get('potencia_instalada_cabecera_kw', 0))
            
            fig_power.add_trace(go.Bar(
                name='Patio', x=techs, y=patio_power,
                marker_color='#34C759',
                text=[f"{p:,.0f}" for p in patio_power],
                textposition='inside'
            ))
            fig_power.add_trace(go.Bar(
                name='Cabecera', x=techs, y=cabecera_power,
                marker_color='#007AFF',
                text=[f"{p:,.0f}" for p in cabecera_power],
                textposition='inside'
            ))
            fig_power.update_layout(
                title=dict(text='Potencia instalada (kW)', font=dict(size=18, color='#1d1d1f')),
                barmode='stack',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, showline=False),
                yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False),
                margin=dict(t=60, b=40, l=40, r=20),
                height=400,
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            st.plotly_chart(fig_power, use_container_width=True)
        
        # Energía por bus - comparación más clara
        col3, col4 = st.columns(2)
        
        with col3:
            fig_cons = go.Figure()
            for key, data in electric_data.items():
                tech_name = data['tecnologia'].replace('Eléctrico - ', '')
                consumo = data.get('energia_consumida_por_bus_kwh', data.get('km_por_bus_tot', 0) * 1.2)
                fig_cons.add_trace(go.Bar(
                    x=[tech_name],
                    y=[consumo],
                    marker_color=TECH_COLORS.get(data['tecnologia'], '#666'),
                    text=[f"{consumo:,.0f}"],
                    textposition='outside'
                ))
            fig_cons.update_layout(
                title=dict(text='Consumo por bus/día (kWh)', font=dict(size=18, color='#1d1d1f')),
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, showline=False),
                yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False),
                margin=dict(t=60, b=40, l=40, r=20),
                height=350
            )
            st.plotly_chart(fig_cons, use_container_width=True)
        
        with col4:
            # Ratio energía recuperada en ruta vs consumo
            fig_ratio = go.Figure()
            for key, data in electric_data.items():
                tech_name = data['tecnologia'].replace('Eléctrico - ', '')
                consumo = data.get('energia_consumida_por_bus_kwh', 0)
                recuperada = data.get('energia_mini_cargas_por_bus_kwh', 0)
                if consumo > 0:
                    ratio = (recuperada / consumo) * 100
                else:
                    ratio = 0
                fig_ratio.add_trace(go.Bar(
                    x=[tech_name],
                    y=[ratio],
                    marker_color=TECH_COLORS.get(data['tecnologia'], '#666'),
                    text=[f"{ratio:.0f}%"],
                    textposition='outside'
                ))
            fig_ratio.update_layout(
                title=dict(text='% Energía recuperada en ruta', font=dict(size=18, color='#1d1d1f')),
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, showline=False),
                yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False, range=[0, 105]),
                margin=dict(t=60, b=40, l=40, r=20),
                height=350
            )
            st.plotly_chart(fig_ratio, use_container_width=True)

with chart_tabs[2]:
    col1, col2 = st.columns(2)
    
    with col1:
        charger_data = []
        for key, data in results.items():
            tech = data['tecnologia'].replace('Eléctrico - ', '')
            if 'cargadores_patio' in data:
                charger_data.append({'Tecnología': tech, 'Tipo': 'Patio', 'Cantidad': data['cargadores_patio']})
            if 'n_cargadores_cabecera' in data and data['n_cargadores_cabecera'] > 0:
                charger_data.append({'Tecnología': tech, 'Tipo': 'Cabecera', 'Cantidad': data['n_cargadores_cabecera']})
            if 'n_cargadores_trazado' in data and data['n_cargadores_trazado'] > 0:
                charger_data.append({'Tecnología': tech, 'Tipo': 'Trazado', 'Cantidad': data['n_cargadores_trazado']})
        
        if charger_data:
            df_chargers = pd.DataFrame(charger_data)
            fig_chargers = px.bar(
                df_chargers, x='Tecnología', y='Cantidad', color='Tipo',
                barmode='group', color_discrete_map={'Patio': '#34C759', 'Cabecera': '#FF9500', 'Trazado': '#5AC8FA'},
                text='Cantidad'
            )
            fig_chargers.update_layout(
                title=dict(text='Cargadores requeridos', font=dict(size=18, color='#1d1d1f')),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, showline=False),
                yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False),
                margin=dict(t=60, b=40, l=40, r=20),
                height=400,
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            fig_chargers.update_traces(textposition='outside')
            st.plotly_chart(fig_chargers, use_container_width=True)
    
    with col2:
        autonomy_data = []
        for key, data in results.items():
            tech = data['tecnologia'].replace('Eléctrico - ', '')
            if 'autonomia_usable_km' in data:
                autonomy_data.append({
                    'Tecnología': tech,
                    'Autonomía usable': data['autonomia_usable_km'],
                    'Km por bus': data.get('km_por_bus_tot', 0)
                })
            elif 'autonomia_km' in data:
                autonomy_data.append({
                    'Tecnología': tech,
                    'Autonomía usable': data['autonomia_km'],
                    'Km por bus': data.get('km_por_bus_tot', 0)
                })
        
        if autonomy_data:
            df_aut = pd.DataFrame(autonomy_data)
            fig_aut = go.Figure()
            fig_aut.add_trace(go.Bar(
                name='Autonomía', x=df_aut['Tecnología'], y=df_aut['Autonomía usable'],
                marker_color='#34C759', opacity=0.7
            ))
            fig_aut.add_trace(go.Scatter(
                name='Km requeridos', x=df_aut['Tecnología'], y=df_aut['Km por bus'],
                mode='markers+lines',
                marker=dict(size=12, color='#FF3B30'),
                line=dict(color='#FF3B30', width=2, dash='dot')
            ))
            fig_aut.update_layout(
                title=dict(text='Autonomía vs Km requeridos', font=dict(size=18, color='#1d1d1f')),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, showline=False),
                yaxis=dict(showgrid=True, gridcolor='#e5e5e7', showline=False, title='Km'),
                margin=dict(t=60, b=40, l=40, r=20),
                height=400,
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            st.plotly_chart(fig_aut, use_container_width=True)

with chart_tabs[3]:
    st.markdown("### Datos detallados por tecnología")
    
    df_display = df_results.copy()
    df_display = df_display.drop(columns=['color'], errors='ignore')
    
    column_names = {
        'tecnologia': 'Tecnología',
        'flota_headway': 'Flota (headway)',
        'flota_km': 'Flota (km)',
        'flota_requerida': 'Flota requerida',
        'km_comerciales_dia': 'Km comerciales/día',
        'km_totales_dia': 'Km totales/día',
        'km_por_bus_com': 'Km/bus (com)',
        'km_por_bus_tot': 'Km/bus (tot)',
        'autonomia_km': 'Autonomía (km)',
        'autonomia_total_km': 'Autonomía total (km)',
        'autonomia_usable_km': 'Autonomía usable (km)',
        'combustible_total_l': 'Diesel total (L)',
        'combustible_por_bus_l': 'Diesel/bus (L)',
        'h2_total_kg': 'H₂ total (kg)',
        'h2_por_bus_kg': 'H₂/bus (kg)',
        'cargadores_patio': 'Cargadores patio',
        'n_cargadores_cabecera': 'Cargadores cabecera',
        'n_cargadores_por_terminal': 'Cargadores/terminal',
        'potencia_instalada_patio_kw': 'Potencia patio (kW)',
        'potencia_instalada_cabecera_kw': 'Potencia cabecera (kW)',
        'potencia_total_instalada_kw': 'Potencia total (kW)',
        'energia_total_patio_kwh': 'Energía patio (kWh)',
        'energia_total_ruta_kwh': 'Energía ruta (kWh)',
        'energia_total_dia_kwh': 'Energía total día (kWh)',
        'ciclos_por_bus': 'Ciclos/bus',
        'cargas_cab_por_bus': 'Cargas cabecera/bus',
        'cargas_traz_por_bus': 'Cargas trazado/bus',
        'es_viable': 'Viable',
        'km_faltantes': 'Km faltantes',
        'km_recuperados_por_carga_cabecera': 'Km/carga cabecera',
        'km_recuperados_por_carga_trazado': 'Km/carga trazado',
        'n_puntos_cabecera': 'Puntos cabecera',
        'n_puntos_trazado': 'Puntos trazado',
        'n_cargadores_trazado': 'Cargadores trazado',
        'cargadores_por_punto_cabecera': 'Carg./punto cabecera',
        'cargadores_por_punto_trazado': 'Carg./punto trazado',
        'tiempo_carga_cabecera_min': 'T. carga cabecera (min)',
        'tiempo_carga_trazado_min': 'T. carga trazado (min)',
        'potencia_instalada_trazado_kw': 'Potencia trazado (kW)',
    }
    
    df_display = df_display.rename(columns=column_names)
    df_transposed = df_display.set_index('Tecnología').T
    
    st.dataframe(
        df_transposed.style.format(precision=1, na_rep='-'),
        use_container_width=True,
        height=700
    )

# Nueva pestaña: Detalle Flash y Oportunidad
with chart_tabs[4]:
    st.markdown("### 🔍 Análisis detallado de carga en ruta")
    st.markdown("*Comparativa entre tecnologías Flash y Oportunidad*")
    
    flash_data = results.get('flash', {})
    opp_data = results.get('opportunity', {})
    
    if flash_data or opp_data:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### ⚡ Carga Flash")
            if flash_data:
                flota_add = flash_data['flota_requerida'] - flash_data['flota_headway']
                cargas_ciclo_f = flash_data.get('cargas_por_ciclo', 1)
                n_cab_f = flash_data.get('n_puntos_cabecera', 0)
                n_traz_f = flash_data.get('n_puntos_trazado', 0)
                c_cab_f = flash_data.get('cargas_cab_por_bus', 0)
                c_traz_f = flash_data.get('cargas_traz_por_bus', 0)
                
                st.markdown(f"""
                | Parámetro | Valor |
                |-----------|-------|
                | **Flota base (headway)** | {flash_data['flota_headway']} buses |
                | **Flota optimizada** | {flash_data['flota_requerida']} buses {"(+" + str(flota_add) + " por energía)" if flota_add > 0 else ""} |
                | **Ciclos por bus** | {flash_data['ciclos_por_bus']} |
                | **Puntos cabecera / trazado** | {n_cab_f} / {n_traz_f} |
                | **Cargas cab / traz por bus** | {c_cab_f} / {c_traz_f} |
                | **Mini-cargas totales/bus** | {flash_data['mini_cargas_por_bus']} (máx. {cargas_ciclo_f * flash_data['ciclos_por_bus']}) |
                | **Km recup./carga cabecera** | {flash_data.get('km_recuperados_por_carga_cabecera', 0):.1f} km |
                | **Km recup./carga trazado** | {flash_data.get('km_recuperados_por_carga_trazado', 0):.1f} km |
                | **Autonomía usable** | {flash_data['autonomia_usable_km']:.1f} km |
                | **Autonomía efectiva** | {flash_data.get('autonomia_efectiva_km', flash_data['autonomia_usable_km']):.1f} km |
                | **Km por bus/día** | {flash_data['km_por_bus_tot']:.1f} km |
                | **Tiempo regulación** | {flash_data.get('tiempo_regulacion_min', 5):.1f} min |
                | **Tiempo carga cabecera** | {flash_data.get('tiempo_carga_cabecera_min', 0):.1f} min |
                | **Tiempo carga trazado** | {flash_data.get('tiempo_carga_trazado_min', 0) * 60:.0f} s |
                """)
                
                st.markdown("**Infraestructura de carga:**")
                cppc_f = flash_data.get('cargadores_por_punto_cabecera', 0)
                cppt_f = flash_data.get('cargadores_por_punto_trazado', 0)
                n_carg_cab_f = flash_data.get('n_cargadores_cabecera', 0)
                n_carg_traz_f = flash_data.get('n_cargadores_trazado', 0)
                total_ruta_f = n_carg_cab_f + n_carg_traz_f
                pot_cab_f = flash_data.get('potencia_instalada_cabecera_kw', 0)
                pot_traz_f = flash_data.get('potencia_instalada_trazado_kw', 0)
                st.markdown(f"""
                | Ubicación | Puntos | Carg./punto | Cargadores | Potencia |
                |-----------|--------|-------------|------------|----------|
                | Cabecera | {n_cab_f} | {cppc_f} | {n_carg_cab_f} | {pot_cab_f:,.0f} kW |
                | Trazado | {n_traz_f} | {cppt_f} | {n_carg_traz_f} | {pot_traz_f:,.0f} kW |
                | Patio | - | - | {flash_data['cargadores_patio']} | {flash_data['potencia_instalada_patio_kw']:,.0f} kW |
                | **TOTAL** | | | **{total_ruta_f + flash_data['cargadores_patio']}** | **{flash_data.get('potencia_total_instalada_kw', 0):,.0f} kW** |
                """)
                
                st.markdown("**Balance energético diario:**")
                st.markdown(f"""
                - Consumo total flota: {flash_data.get('energia_consumida_por_bus_kwh', 0) * flash_data['flota_requerida']:,.0f} kWh
                - Energía en ruta: {flash_data.get('energia_total_ruta_kwh', 0):,.0f} kWh
                - Energía en patio: {flash_data['energia_total_patio_kwh']:,.0f} kWh
                - **Total diario**: {flash_data.get('energia_total_dia_kwh', 0):,.0f} kWh
                """)
            else:
                st.info("No hay datos de carga Flash")
        
        with col2:
            st.markdown("#### 🔌 Carga por Oportunidad")
            if opp_data:
                flota_add = opp_data['flota_requerida'] - opp_data['flota_headway']
                cargas_ciclo_o = opp_data.get('cargas_por_ciclo', 1)
                n_cab_o = opp_data.get('n_puntos_cabecera', 0)
                n_traz_o = opp_data.get('n_puntos_trazado', 0)
                c_cab_o = opp_data.get('cargas_cab_por_bus', 0)
                c_traz_o = opp_data.get('cargas_traz_por_bus', 0)
                
                st.markdown(f"""
                | Parámetro | Valor |
                |-----------|-------|
                | **Flota base (headway)** | {opp_data['flota_headway']} buses |
                | **Flota optimizada** | {opp_data['flota_requerida']} buses {"(+" + str(flota_add) + " por energía)" if flota_add > 0 else ""} |
                | **Ciclos por bus** | {opp_data['ciclos_por_bus']} |
                | **Puntos cabecera / trazado** | {n_cab_o} / {n_traz_o} |
                | **Cargas cab / traz por bus** | {c_cab_o} / {c_traz_o} |
                | **Mini-cargas totales/bus** | {opp_data['mini_cargas_por_bus']} (máx. {cargas_ciclo_o * opp_data['ciclos_por_bus']}) |
                | **Tiempo regulación** | {opp_data.get('tiempo_regulacion_min', 10):.1f} min |
                | **Tiempo carga cabecera** | {opp_data.get('tiempo_carga_cabecera_min', 0):.1f} min |
                | **Tiempo carga trazado** | {opp_data.get('tiempo_carga_trazado_min', 0) * 60:.0f} s |
                | **Km recup./carga cabecera** | {opp_data.get('km_recuperados_por_carga_cabecera', 0):.1f} km |
                | **Km recup./carga trazado** | {opp_data.get('km_recuperados_por_carga_trazado', 0):.1f} km |
                | **Autonomía usable** | {opp_data['autonomia_usable_km']:.1f} km |
                | **Autonomía efectiva** | {opp_data.get('autonomia_efectiva_km', opp_data['autonomia_usable_km']):.1f} km |
                | **Km por bus/día** | {opp_data['km_por_bus_tot']:.1f} km |
                """)
                
                st.markdown("**Infraestructura de carga:**")
                cppc_o = opp_data.get('cargadores_por_punto_cabecera', 0)
                cppt_o = opp_data.get('cargadores_por_punto_trazado', 0)
                n_carg_cab_o = opp_data.get('n_cargadores_cabecera', 0)
                n_carg_traz_o = opp_data.get('n_cargadores_trazado', 0)
                total_ruta_o = n_carg_cab_o + n_carg_traz_o
                pot_cab_o = opp_data.get('potencia_instalada_cabecera_kw', 0)
                pot_traz_o = opp_data.get('potencia_instalada_trazado_kw', 0)
                st.markdown(f"""
                | Ubicación | Puntos | Carg./punto | Cargadores | Potencia |
                |-----------|--------|-------------|------------|----------|
                | Cabecera | {n_cab_o} | {cppc_o} | {n_carg_cab_o} | {pot_cab_o:,.0f} kW |
                | Trazado | {n_traz_o} | {cppt_o} | {n_carg_traz_o} | {pot_traz_o:,.0f} kW |
                | Patio | - | - | {opp_data['cargadores_patio']} | {opp_data['potencia_instalada_patio_kw']:,.0f} kW |
                | **TOTAL** | | | **{total_ruta_o + opp_data['cargadores_patio']}** | **{opp_data.get('potencia_total_instalada_kw', 0):,.0f} kW** |
                """)
                
                st.markdown("**Balance energético diario:**")
                st.markdown(f"""
                - Consumo total flota: {opp_data.get('energia_consumida_por_bus_kwh', 0) * opp_data['flota_requerida']:,.0f} kWh
                - Energía en ruta: {opp_data.get('energia_total_ruta_kwh', 0):,.0f} kWh
                - Energía en patio: {opp_data['energia_total_patio_kwh']:,.0f} kWh
                - **Total diario**: {opp_data.get('energia_total_dia_kwh', 0):,.0f} kWh
                """)
            else:
                st.info("No hay datos de carga por Oportunidad")
        
        # Comparativa visual
        st.markdown("---")
        st.markdown("### Comparativa Flash vs Oportunidad")
        
        if flash_data and opp_data:
            comp_col1, comp_col2, comp_col3 = st.columns(3)
            
            with comp_col1:
                # Diferencia de flota
                diff_flota = opp_data['flota_requerida'] - flash_data['flota_requerida']
                st.metric("Diferencia de flota", f"{abs(diff_flota)} buses", 
                         delta=f"Flash: {flash_data['flota_requerida']} | Opp: {opp_data['flota_requerida']}")
            
            with comp_col2:
                # Diferencia de potencia
                pot_flash = flash_data.get('potencia_total_instalada_kw', 0)
                pot_opp = opp_data.get('potencia_total_instalada_kw', 0)
                diff_pot = abs(pot_opp - pot_flash)
                st.metric("Diferencia potencia", f"{diff_pot:,.0f} kW",
                         delta=f"Flash: {pot_flash:,.0f} | Opp: {pot_opp:,.0f}")
            
            with comp_col3:
                # Diferencia de cargadores
                carg_flash = flash_data.get('n_cargadores_ruta', 0) + flash_data['cargadores_patio']
                carg_opp = opp_data.get('n_cargadores_ruta', 0) + opp_data['cargadores_patio']
                diff_carg = abs(carg_opp - carg_flash)
                st.metric("Diferencia cargadores", f"{diff_carg}",
                         delta=f"Flash: {carg_flash} | Opp: {carg_opp}")
            
            # Tabla de diferencias clave
            st.markdown("#### Diferencias clave")
            diff_df = pd.DataFrame([
                {
                    'Aspecto': 'Puntos cabecera / trazado',
                    'Flash': f"{flash_data.get('n_puntos_cabecera', 0)} / {flash_data.get('n_puntos_trazado', 0)}",
                    'Oportunidad': f"{opp_data.get('n_puntos_cabecera', 0)} / {opp_data.get('n_puntos_trazado', 0)}",
                    'Implicación': 'Cabecera: terminales (máx 2). Trazado: paradas intermedias.'
                },
                {
                    'Aspecto': 'Potencia por cargador',
                    'Flash': f"{flash.cargador_ruta_kw} kW",
                    'Oportunidad': f"{opp.cargador_ruta_kw} kW",
                    'Implicación': 'Flash requiere infraestructura eléctrica más robusta'
                },
                {
                    'Aspecto': 'Tiempo carga cabecera',
                    'Flash': f"{flash_data.get('tiempo_carga_cabecera_min', 0):.1f} min",
                    'Oportunidad': f"{opp_data.get('tiempo_carga_cabecera_min', 0):.1f} min",
                    'Implicación': 'Oportunidad usa regulación para cargar más tiempo'
                },
                {
                    'Aspecto': 'Tiempo carga trazado',
                    'Flash': f"{flash_data.get('tiempo_carga_trazado_min', 0) * 60:.0f} s",
                    'Oportunidad': f"{opp_data.get('tiempo_carga_trazado_min', 0) * 60:.0f} s",
                    'Implicación': 'Carga ultrarrápida en paradas intermedias'
                },
                {
                    'Aspecto': 'Mini-cargas por bus',
                    'Flash': f"{flash_data['mini_cargas_por_bus']} (cab: {flash_data.get('cargas_cab_por_bus', 0)}, traz: {flash_data.get('cargas_traz_por_bus', 0)})",
                    'Oportunidad': f"{opp_data['mini_cargas_por_bus']} (cab: {opp_data.get('cargas_cab_por_bus', 0)}, traz: {opp_data.get('cargas_traz_por_bus', 0)})",
                    'Implicación': 'Distribución de cargas entre cabecera y trazado'
                },
            ])
            st.dataframe(diff_df, use_container_width=True, hide_index=True)
    else:
        st.info("Configure las tecnologías Flash y/o Oportunidad para ver el análisis detallado")

# ─────────────────────────────────────────────────────────────────────────────
# Exportar a Excel
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")

_excel_buf = generate_excel_report(
    operational_results=results,
    general_inputs=g,
    tech_inputs=st.session_state.get('tech_inputs'),
)

st.download_button(
    label='📥 Exportar resultados operativos a Excel',
    data=_excel_buf,
    file_name='comparador_operacion.xlsx',
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
)

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #86868b; font-size: 12px; padding: 20px;">
    Comparador de Tecnologías de Buses · IDOM<br>
    <span style="font-size: 11px;">Navega a <b>💰 Costos</b> en el menú lateral para el análisis económico</span>
</div>
""", unsafe_allow_html=True)
