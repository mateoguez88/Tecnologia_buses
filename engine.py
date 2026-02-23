# -*- coding: utf-8 -*-
"""Motor de cálculo para planes de operación por tecnología.

Este motor replica la lógica del Excel 'Planes de operación_tenologias.xlsx'
(con ajustes para que sea paramétrico y reutilizable).

Convenciones:
- Longitud L es por sentido (km).
- Headway h (min).
- Tiempo de servicio T (min) es el tiempo con despacho a headway constante.
- Tiempo entre servicios (TES) es la regulación/tiempo en terminal por sentido (min).
- % km en vacío (p_vacio) es fracción del km comercial (p.ej., 0.05 = 5%).
- Para eléctricos: SOC_reserva es fracción no utilizable (p.ej., 0.20).
- Eficiencia de carga eta es fracción neta (p.ej., 0.90).

"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import math
from typing import Dict, Any


# -------------------------
# Utilidades generales
# -------------------------

def ceil(x: float) -> int:
    return int(math.ceil(x))


def floor(x: float) -> int:
    return int(math.floor(x))


@dataclass
class GeneralInputs:
    km_trazado_sentido: float = 23.0
    velocidad_kmh: float = 25.0
    headway_min: float = 10.0
    tiempo_servicio_min: float = 990.0
    tiempo_entre_servicios_min: float = 5.0  # layover/regulación por terminal
    km_vacio_frac: float = 0.05

    def tiempo_ida_min(self) -> float:
        return (self.km_trazado_sentido / self.velocidad_kmh) * 60.0

    def tiempo_ida_mas_es_min(self) -> float:
        return self.tiempo_ida_min() + self.tiempo_entre_servicios_min

    def tiempo_ciclo_min(self) -> float:
        # En el Excel: tiempo ida+vuelta = 2*(tiempo ida + ES)
        return 2.0 * self.tiempo_ida_mas_es_min()

    def flota_por_headway(self) -> int:
        return ceil(self.tiempo_ciclo_min() / self.headway_min)

    def salidas_por_sentido(self) -> int:
        # Excel usa T/h sin +1
        return int(self.tiempo_servicio_min / self.headway_min)

    def km_comerciales_dia(self) -> float:
        return 2.0 * self.salidas_por_sentido() * self.km_trazado_sentido

    def km_totales_dia(self) -> float:
        return self.km_comerciales_dia() * (1.0 + self.km_vacio_frac)


# -------------------------
# Tecnologías
# -------------------------

@dataclass
class DieselInputs:
    consumo_litros_km: float = 0.10
    autonomia_km: float = 600.0


@dataclass
class ElectricOvernightInputs:
    bateria_kwh: float = 350.0
    consumo_kwh_km: float = 1.2
    soc_reserva_frac: float = 0.20
    cargador_kw: float = 150.0
    eficiencia_carga: float = 0.90
    ventana_carga_h: float = 6.0


@dataclass
class ElectricFlashInputs:
    bateria_kwh: float = 350.0
    consumo_kwh_km: float = 1.2
    soc_reserva_frac: float = 0.20
    eficiencia_carga: float = 0.90
    cargador_ruta_kw: float = 600.0
    tiempo_carga_ruta_min: float = 3.0
    tiempo_regulacion_min: float = 5.0  # Tiempo en terminal (regulación)
    # Carga nocturna (si aplica) para completar SOC
    cargador_patio_kw: float = 150.0
    ventana_carga_h: float = 6.0
    # Modo de cálculo: None=optimizar flota, int=restricción máx. mini-cargas
    max_mini_cargas_restriccion: int = None


@dataclass
class ElectricOpportunityInputs:
    bateria_kwh: float = 350.0
    consumo_kwh_km: float = 1.2
    soc_reserva_frac: float = 0.20
    eficiencia_carga: float = 0.90
    cargador_ruta_kw: float = 200.0
    tiempo_carga_ruta_min: float = 10.0
    tiempo_regulacion_min: float = 10.0  # Tiempo en terminal (regulación)
    cargador_patio_kw: float = 150.0
    ventana_carga_h: float = 6.0
    # Modo de cálculo: None=optimizar flota, int=restricción máx. mini-cargas
    max_mini_cargas_restriccion: int = None


@dataclass
class HydrogenInputs:
    autonomia_km: float = 500.0
    consumo_h2_kg_km: float = 0.10  # kg H2 por km


# -------------------------
# Cálculos por tecnología
# -------------------------


def calc_diesel(g: GeneralInputs, d: DieselInputs) -> Dict[str, Any]:
    fleet_hw = g.flota_por_headway()
    km_com = g.km_comerciales_dia()
    km_tot = g.km_totales_dia()

    # Flota por autonomía (similar a carga nocturna)
    fleet_km = ceil(km_tot / d.autonomia_km)
    fleet_req = max(fleet_hw, fleet_km)

    km_por_bus_com = km_com / fleet_req
    km_por_bus_tot = km_tot / fleet_req

    # Ciclos por bus
    km_ciclo = 2.0 * g.km_trazado_sentido
    ciclos = ceil(km_por_bus_tot / km_ciclo)

    litros_flota = km_com * d.consumo_litros_km
    litros_por_bus = km_por_bus_com * d.consumo_litros_km

    return {
        'tecnologia': 'Diesel',
        'flota_headway': fleet_hw,
        'flota_km': fleet_km,
        'flota_requerida': fleet_req,
        'autonomia_km': d.autonomia_km,
        'km_comerciales_dia': km_com,
        'km_totales_dia': km_tot,
        'km_por_bus_com': km_por_bus_com,
        'km_por_bus_tot': km_por_bus_tot,
        'ciclos_por_bus': ciclos,
        'combustible_total_l': litros_flota,
        'combustible_por_bus_l': litros_por_bus,
    }


def _autonomia_total_km(bateria_kwh: float, consumo_kwh_km: float) -> float:
    return bateria_kwh / consumo_kwh_km


def _autonomia_usable_km(bateria_kwh: float, consumo_kwh_km: float, soc_reserva: float) -> float:
    return (1.0 - soc_reserva) * _autonomia_total_km(bateria_kwh, consumo_kwh_km)


def _energia_recarga_full_kwh(bateria_kwh: float, soc_reserva: float, eta: float) -> float:
    # Energía desde la red para subir de SOC_reserva a 100%
    return (bateria_kwh * (1.0 - soc_reserva)) / eta


def calc_electric_overnight(g: GeneralInputs, e: ElectricOvernightInputs) -> Dict[str, Any]:
    fleet_hw = g.flota_por_headway()
    km_com = g.km_comerciales_dia()
    km_tot = g.km_totales_dia()

    aut_total = _autonomia_total_km(e.bateria_kwh, e.consumo_kwh_km)
    aut_usable = _autonomia_usable_km(e.bateria_kwh, e.consumo_kwh_km, e.soc_reserva_frac)

    # Flota por autonomía diaria (como en tu Excel)
    fleet_km = ceil(km_tot / aut_usable)
    fleet_req = max(fleet_hw, fleet_km)

    # km por bus (con flota requerida)
    km_por_bus_com = km_com / fleet_req
    km_por_bus_tot = km_tot / fleet_req

    # Ciclos por bus
    km_ciclo = 2.0 * g.km_trazado_sentido
    ciclos = ceil(km_por_bus_tot / km_ciclo)

    # Energía real consumida por bus (según km recorridos)
    energia_consumida_por_bus_kwh = km_por_bus_tot * e.consumo_kwh_km
    # Energía desde la red para recargar lo consumido
    energia_recarga_por_bus_kwh = energia_consumida_por_bus_kwh / e.eficiencia_carga
    tiempo_carga_h = energia_recarga_por_bus_kwh / e.cargador_kw

    # Cargadores en patio: buses * tiempo de carga / ventana
    n_cargadores = ceil((fleet_req * tiempo_carga_h) / e.ventana_carga_h)

    energia_total_patio_kwh = fleet_req * energia_recarga_por_bus_kwh
    potencia_promedio_patio_kw = energia_total_patio_kwh / e.ventana_carga_h
    potencia_instalada_patio_kw = n_cargadores * e.cargador_kw

    return {
        'tecnologia': 'Eléctrico - Carga nocturna',
        'flota_headway': fleet_hw,
        'flota_km': fleet_km,
        'flota_requerida': fleet_req,
        'km_comerciales_dia': km_com,
        'km_totales_dia': km_tot,
        'km_por_bus_com': km_por_bus_com,
        'km_por_bus_tot': km_por_bus_tot,
        'ciclos_por_bus': ciclos,
        'autonomia_total_km': aut_total,
        'autonomia_usable_km': aut_usable,
        'energia_consumida_por_bus_kwh': energia_consumida_por_bus_kwh,
        'energia_recarga_por_bus_kwh': energia_recarga_por_bus_kwh,
        'tiempo_carga_por_bus_h': tiempo_carga_h,
        'cargadores_patio': n_cargadores,
        'energia_total_patio_kwh': energia_total_patio_kwh,
        'potencia_promedio_patio_kw': potencia_promedio_patio_kw,
        'potencia_instalada_patio_kw': potencia_instalada_patio_kw,
    }


def _km_por_bus_requeridos(g: GeneralInputs, flota: int) -> float:
    return g.km_totales_dia() / flota


def _mini_charge_km(power_kw: float, minutes: float, consumo_kwh_km: float, eta: float) -> float:
    """Km recuperados por una mini-carga (energía neta entregada a batería)."""
    e_kwh = power_kw * (minutes / 60.0)
    e_neta = e_kwh * eta
    return e_neta / consumo_kwh_km


def _calcular_flota_optimizada(
    km_totales_dia: float,
    km_ciclo: float,
    aut_usable_km: float,
    km_por_mini_carga: float,
    flota_minima_headway: int,
    max_mini_cargas_restriccion: int = None
) -> tuple[int, int, int]:
    """
    Calcula la flota óptima considerando mini-cargas.
    
    Modos:
    - max_mini_cargas_restriccion=None: Optimizar flota (añadir buses si mini-cargas > ciclos)
    - max_mini_cargas_restriccion=N: Calcular flota necesaria con máximo N mini-cargas/bus
    
    Retorna: (flota_requerida, ciclos_por_bus, mini_cargas_por_bus)
    """
    # Empezar con flota mínima por headway
    flota = flota_minima_headway
    
    while True:
        km_por_bus = km_totales_dia / flota
        ciclos = ceil(km_por_bus / km_ciclo)
        
        # Determinar máx. mini-cargas permitidas
        if max_mini_cargas_restriccion is not None:
            # Modo restricción: usuario limita las mini-cargas
            max_mini = min(max_mini_cargas_restriccion, ciclos)
        else:
            # Modo optimización: máximo 1 mini-carga por ciclo
            max_mini = ciclos
        
        # Máxima autonomía con mini-cargas permitidas
        km_max_con_minicargas = aut_usable_km + (max_mini * km_por_mini_carga)
        
        if km_max_con_minicargas >= km_por_bus:
            # Viable con esta flota
            km_faltantes = max(0.0, km_por_bus - aut_usable_km)
            mini_cargas = ceil(km_faltantes / km_por_mini_carga) if km_faltantes > 0 else 0
            mini_cargas = min(mini_cargas, max_mini)
            return flota, ciclos, mini_cargas
        else:
            # Necesita más flota
            flota += 1
            # Límite de seguridad
            if flota > flota_minima_headway * 10:
                km_faltantes = max(0.0, km_por_bus - aut_usable_km)
                mini_cargas = min(max_mini, ceil(km_faltantes / km_por_mini_carga) if km_faltantes > 0 else 0)
                return flota, ciclos, mini_cargas


def calc_electric_flash(g: GeneralInputs, e: ElectricFlashInputs) -> Dict[str, Any]:
    """
    Carga Flash: cargas ultrarrápidas (>400kW) en cabecera de muy corta duración (2-5 min).
    
    Lógica de optimización:
    - 1 cargador en cabecera
    - Cada bus hace 1 mini-carga por ciclo (máximo)
    - Si mini-cargas necesarias > ciclos → añadir bus (que también hace mini-cargas)
    """
    fleet_hw = g.flota_por_headway()
    km_com = g.km_comerciales_dia()
    km_tot = g.km_totales_dia()

    aut_total = _autonomia_total_km(e.bateria_kwh, e.consumo_kwh_km)
    aut_usable = _autonomia_usable_km(e.bateria_kwh, e.consumo_kwh_km, e.soc_reserva_frac)

    km_ciclo = 2.0 * g.km_trazado_sentido

    # Km recuperados por mini-carga
    km_recupera = _mini_charge_km(
        e.cargador_ruta_kw, e.tiempo_carga_ruta_min, 
        e.consumo_kwh_km, e.eficiencia_carga
    )
    
    # Calcular flota optimizada (con o sin restricción de mini-cargas)
    fleet_req, ciclos, mini_cargas = _calcular_flota_optimizada(
        km_tot, km_ciclo, aut_usable, km_recupera, fleet_hw, e.max_mini_cargas_restriccion
    )
    
    km_por_bus_com = km_com / fleet_req
    km_por_bus_tot = km_tot / fleet_req
    km_faltantes = max(0.0, km_por_bus_tot - aut_usable)
    
    # Cargadores en cabecera: 1 cargador (según especificación)
    n_cargadores_cabecera = 1 if mini_cargas > 0 else 0
    potencia_instalada_cabecera_kw = n_cargadores_cabecera * e.cargador_ruta_kw

    # Energía consumida vs recuperada en mini-cargas
    energia_consumida_por_bus_kwh = km_por_bus_tot * e.consumo_kwh_km
    energia_por_mini = e.cargador_ruta_kw * (e.tiempo_carga_ruta_min / 60.0) * e.eficiencia_carga
    energia_mini_cargas_kwh = mini_cargas * energia_por_mini
    
    # Carga nocturna: diferencia entre consumo y lo recuperado en ruta
    energia_pendiente_kwh = max(0.0, energia_consumida_por_bus_kwh - energia_mini_cargas_kwh)
    energia_recarga_patio_por_bus_kwh = energia_pendiente_kwh / e.eficiencia_carga
    tiempo_carga_patio_h = energia_recarga_patio_por_bus_kwh / e.cargador_patio_kw if energia_recarga_patio_por_bus_kwh > 0 else 0
    cargadores_patio = ceil((fleet_req * tiempo_carga_patio_h) / e.ventana_carga_h) if tiempo_carga_patio_h > 0 else 0
    energia_total_patio_kwh = fleet_req * energia_recarga_patio_por_bus_kwh
    potencia_instalada_patio_kw = cargadores_patio * e.cargador_patio_kw
    
    # Energía total diaria (red)
    energia_total_cabecera_kwh = fleet_req * mini_cargas * e.cargador_ruta_kw * (e.tiempo_carga_ruta_min / 60.0)
    energia_total_dia_kwh = energia_total_patio_kwh + energia_total_cabecera_kwh
    
    # Potencia total instalada
    potencia_total_instalada_kw = potencia_instalada_patio_kw + potencia_instalada_cabecera_kw
    
    # Autonomía efectiva con mini-cargas
    autonomia_efectiva_km = aut_usable + (mini_cargas * km_recupera)

    return {
        'tecnologia': 'Eléctrico - Carga flash',
        'flota_headway': fleet_hw,
        'flota_requerida': fleet_req,
        'km_comerciales_dia': km_com,
        'km_totales_dia': km_tot,
        'km_por_bus_com': km_por_bus_com,
        'km_por_bus_tot': km_por_bus_tot,
        'ciclos_por_bus': ciclos,
        'autonomia_total_km': aut_total,
        'autonomia_usable_km': aut_usable,
        'autonomia_efectiva_km': autonomia_efectiva_km,
        'km_faltantes': km_faltantes,
        'km_recuperados_por_mini': km_recupera,
        'mini_cargas_por_bus': mini_cargas,
        'tiempo_regulacion_min': e.tiempo_regulacion_min,
        'n_cargadores_cabecera': n_cargadores_cabecera,
        'potencia_instalada_cabecera_kw': potencia_instalada_cabecera_kw,
        'cargadores_patio': cargadores_patio,
        'energia_consumida_por_bus_kwh': energia_consumida_por_bus_kwh,
        'energia_mini_cargas_por_bus_kwh': energia_mini_cargas_kwh,
        'energia_total_patio_kwh': energia_total_patio_kwh,
        'energia_total_cabecera_kwh': energia_total_cabecera_kwh,
        'energia_total_dia_kwh': energia_total_dia_kwh,
        'potencia_instalada_patio_kw': potencia_instalada_patio_kw,
        'potencia_total_instalada_kw': potencia_total_instalada_kw,
    }


def calc_electric_opportunity(g: GeneralInputs, e: ElectricOpportunityInputs) -> Dict[str, Any]:
    """
    Carga por Oportunidad: cargas de potencia media (150-300kW) durante regulación (5-15 min).
    
    Lógica de optimización:
    - Carga durante el tiempo de regulación en terminal
    - Cada bus hace 1 mini-carga por ciclo (máximo)
    - Si mini-cargas necesarias > ciclos → añadir bus (que también hace mini-cargas)
    """
    fleet_hw = g.flota_por_headway()
    km_com = g.km_comerciales_dia()
    km_tot = g.km_totales_dia()

    aut_total = _autonomia_total_km(e.bateria_kwh, e.consumo_kwh_km)
    aut_usable = _autonomia_usable_km(e.bateria_kwh, e.consumo_kwh_km, e.soc_reserva_frac)

    km_ciclo = 2.0 * g.km_trazado_sentido

    # Tiempo de carga efectivo: mínimo entre tiempo disponible y tiempo de carga deseado
    tiempo_carga_efectivo = min(e.tiempo_carga_ruta_min, e.tiempo_regulacion_min)
    
    # Km recuperados por mini-carga
    km_recupera = _mini_charge_km(
        e.cargador_ruta_kw, tiempo_carga_efectivo, 
        e.consumo_kwh_km, e.eficiencia_carga
    )
    
    # Calcular flota optimizada (con o sin restricción de mini-cargas)
    fleet_req, ciclos, mini_cargas = _calcular_flota_optimizada(
        km_tot, km_ciclo, aut_usable, km_recupera, fleet_hw, e.max_mini_cargas_restriccion
    )
    
    km_por_bus_com = km_com / fleet_req
    km_por_bus_tot = km_tot / fleet_req
    km_faltantes = max(0.0, km_por_bus_tot - aut_usable)
    
    # Cargadores en cabecera: depende de buses simultáneos
    buses_simultaneos = ceil(tiempo_carga_efectivo / g.headway_min) if mini_cargas > 0 else 0
    n_cargadores_cabecera = max(1, buses_simultaneos) if mini_cargas > 0 else 0
    potencia_instalada_cabecera_kw = n_cargadores_cabecera * e.cargador_ruta_kw

    # Energía consumida vs recuperada
    energia_consumida_por_bus_kwh = km_por_bus_tot * e.consumo_kwh_km
    energia_por_mini = e.cargador_ruta_kw * (tiempo_carga_efectivo / 60.0) * e.eficiencia_carga
    energia_mini_cargas_kwh = mini_cargas * energia_por_mini
    
    # Carga nocturna
    energia_pendiente_kwh = max(0.0, energia_consumida_por_bus_kwh - energia_mini_cargas_kwh)
    energia_recarga_patio_por_bus_kwh = energia_pendiente_kwh / e.eficiencia_carga
    tiempo_carga_patio_h = energia_recarga_patio_por_bus_kwh / e.cargador_patio_kw if energia_recarga_patio_por_bus_kwh > 0 else 0
    cargadores_patio = ceil((fleet_req * tiempo_carga_patio_h) / e.ventana_carga_h) if tiempo_carga_patio_h > 0 else 0
    energia_total_patio_kwh = fleet_req * energia_recarga_patio_por_bus_kwh
    potencia_instalada_patio_kw = cargadores_patio * e.cargador_patio_kw
    
    # Energía total diaria
    energia_total_cabecera_kwh = fleet_req * mini_cargas * e.cargador_ruta_kw * (tiempo_carga_efectivo / 60.0)
    energia_total_dia_kwh = energia_total_patio_kwh + energia_total_cabecera_kwh
    
    # Potencia total instalada
    potencia_total_instalada_kw = potencia_instalada_patio_kw + potencia_instalada_cabecera_kw
    
    # Autonomía efectiva con mini-cargas
    autonomia_efectiva_km = aut_usable + (mini_cargas * km_recupera)

    return {
        'tecnologia': 'Eléctrico - Carga por oportunidad',
        'flota_headway': fleet_hw,
        'flota_requerida': fleet_req,
        'km_comerciales_dia': km_com,
        'km_totales_dia': km_tot,
        'km_por_bus_com': km_por_bus_com,
        'km_por_bus_tot': km_por_bus_tot,
        'ciclos_por_bus': ciclos,
        'autonomia_total_km': aut_total,
        'autonomia_usable_km': aut_usable,
        'autonomia_efectiva_km': autonomia_efectiva_km,
        'km_faltantes': km_faltantes,
        'km_recuperados_por_mini': km_recupera,
        'mini_cargas_por_bus': mini_cargas,
        'tiempo_regulacion_min': e.tiempo_regulacion_min,
        'tiempo_carga_efectivo_min': tiempo_carga_efectivo,
        'n_cargadores_cabecera': n_cargadores_cabecera,
        'potencia_instalada_cabecera_kw': potencia_instalada_cabecera_kw,
        'cargadores_patio': cargadores_patio,
        'energia_consumida_por_bus_kwh': energia_consumida_por_bus_kwh,
        'energia_mini_cargas_por_bus_kwh': energia_mini_cargas_kwh,
        'energia_total_patio_kwh': energia_total_patio_kwh,
        'energia_total_cabecera_kwh': energia_total_cabecera_kwh,
        'energia_total_dia_kwh': energia_total_dia_kwh,
        'potencia_instalada_patio_kw': potencia_instalada_patio_kw,
        'potencia_total_instalada_kw': potencia_total_instalada_kw,
    }


def calc_hydrogen(g: GeneralInputs, h: HydrogenInputs) -> Dict[str, Any]:
    fleet_hw = g.flota_por_headway()
    km_com = g.km_comerciales_dia()
    km_tot = g.km_totales_dia()

    # Flota por autonomía (similar a diesel)
    fleet_km = ceil(km_tot / h.autonomia_km)
    fleet_req = max(fleet_hw, fleet_km)

    km_por_bus_com = km_com / fleet_req
    km_por_bus_tot = km_tot / fleet_req

    # Ciclos por bus
    km_ciclo = 2.0 * g.km_trazado_sentido
    ciclos = ceil(km_por_bus_tot / km_ciclo)

    # Consumo de H2
    h2_total_kg = km_com * h.consumo_h2_kg_km
    h2_por_bus_kg = km_por_bus_com * h.consumo_h2_kg_km

    return {
        'tecnologia': 'Hidrógeno',
        'flota_headway': fleet_hw,
        'flota_km': fleet_km,
        'flota_requerida': fleet_req,
        'autonomia_km': h.autonomia_km,
        'km_comerciales_dia': km_com,
        'km_totales_dia': km_tot,
        'km_por_bus_com': km_por_bus_com,
        'km_por_bus_tot': km_por_bus_tot,
        'ciclos_por_bus': ciclos,
        'h2_total_kg': h2_total_kg,
        'h2_por_bus_kg': h2_por_bus_kg,
    }


def run_all(
    general: GeneralInputs,
    diesel: DieselInputs | None = None,
    overnight: ElectricOvernightInputs | None = None,
    flash: ElectricFlashInputs | None = None,
    opportunity: ElectricOpportunityInputs | None = None,
    hydrogen: HydrogenInputs | None = None,
) -> Dict[str, Dict[str, Any]]:
    """Ejecuta todas las tecnologías y retorna un dict de resultados."""

    out: Dict[str, Dict[str, Any]] = {}
    if diesel is not None:
        out['diesel'] = calc_diesel(general, diesel)
    if overnight is not None:
        out['overnight'] = calc_electric_overnight(general, overnight)
    if flash is not None:
        out['flash'] = calc_electric_flash(general, flash)
    if opportunity is not None:
        out['opportunity'] = calc_electric_opportunity(general, opportunity)
    if hydrogen is not None:
        out['hydrogen'] = calc_hydrogen(general, hydrogen)
    return out


# =========================================================================
# MÓDULO DE COSTOS — CAPEX / OPEX / TCO
# =========================================================================

@dataclass
class CostGeneralInputs:
    """Parámetros financieros generales."""
    horizonte_anios: int = 15
    dias_operacion_anio: int = 365


@dataclass
class CostCapexDiesel:
    vehiculo_eur: float = 250_000.0
    infraestructura_deposito_eur_bus: float = 15_000.0


@dataclass
class CostCapexOvernight:
    vehiculo_eur: float = 450_000.0
    cargador_pistola_eur: float = 40_000.0
    subestacion_electrica_eur: float = 200_000.0
    infraestructura_deposito_eur_bus: float = 20_000.0


@dataclass
class CostCapexFlash:
    vehiculo_eur: float = 500_000.0
    cargador_pantografo_cabecera_eur: float = 350_000.0
    cargador_pistola_patio_eur: float = 40_000.0
    subestacion_electrica_eur: float = 300_000.0
    infraestructura_deposito_eur_bus: float = 20_000.0


@dataclass
class CostCapexOpportunity:
    vehiculo_eur: float = 480_000.0
    cargador_oportunidad_cabecera_eur: float = 250_000.0
    cargador_pistola_patio_eur: float = 40_000.0
    subestacion_electrica_eur: float = 250_000.0
    infraestructura_deposito_eur_bus: float = 20_000.0


@dataclass
class CostCapexHydrogen:
    vehiculo_eur: float = 600_000.0
    estacion_hidrogeno_eur: float = 1_500_000.0
    infraestructura_deposito_eur_bus: float = 20_000.0


@dataclass
class CostOpexDiesel:
    combustible_eur_litro: float = 1.50
    mantenimiento_eur_km: float = 0.30


@dataclass
class CostOpexOvernight:
    energia_eur_kwh: float = 0.12
    mantenimiento_eur_km: float = 0.18
    bateria_mantenimiento_anual_eur_bus: float = 2_000.0
    bateria_reemplazo_eur: float = 80_000.0
    bateria_vida_util_anios: int = 8


@dataclass
class CostOpexFlash:
    energia_eur_kwh: float = 0.12
    mantenimiento_eur_km: float = 0.18
    bateria_mantenimiento_anual_eur_bus: float = 2_000.0
    bateria_reemplazo_eur: float = 80_000.0
    bateria_vida_util_anios: int = 8


@dataclass
class CostOpexOpportunity:
    energia_eur_kwh: float = 0.12
    mantenimiento_eur_km: float = 0.18
    bateria_mantenimiento_anual_eur_bus: float = 2_000.0
    bateria_reemplazo_eur: float = 80_000.0
    bateria_vida_util_anios: int = 8


@dataclass
class CostOpexHydrogen:
    hidrogeno_eur_kg: float = 6.00
    mantenimiento_eur_km: float = 0.25


# ─────────────────────────────────────────────────────────────────────────────
# Funciones de cálculo de costos
# ─────────────────────────────────────────────────────────────────────────────


def calc_capex_diesel(op: Dict[str, Any], c: CostCapexDiesel) -> Dict[str, Any]:
    flota = op['flota_requerida']
    vehiculos = flota * c.vehiculo_eur
    deposito = flota * c.infraestructura_deposito_eur_bus
    total = vehiculos + deposito
    return {
        'vehiculos': vehiculos,
        'cargadores_cabecera': 0.0,
        'cargadores_patio': 0.0,
        'subestacion': 0.0,
        'estacion_h2': 0.0,
        'infra_deposito': deposito,
        'total_capex': total,
    }


def calc_capex_overnight(op: Dict[str, Any], c: CostCapexOvernight) -> Dict[str, Any]:
    flota = op['flota_requerida']
    n_cargadores_patio = op.get('cargadores_patio', 0)
    vehiculos = flota * c.vehiculo_eur
    cargadores = n_cargadores_patio * c.cargador_pistola_eur
    subestacion = c.subestacion_electrica_eur
    deposito = flota * c.infraestructura_deposito_eur_bus
    total = vehiculos + cargadores + subestacion + deposito
    return {
        'vehiculos': vehiculos,
        'cargadores_cabecera': 0.0,
        'cargadores_patio': cargadores,
        'subestacion': subestacion,
        'estacion_h2': 0.0,
        'infra_deposito': deposito,
        'total_capex': total,
    }


def calc_capex_flash(op: Dict[str, Any], c: CostCapexFlash) -> Dict[str, Any]:
    flota = op['flota_requerida']
    n_cab = op.get('n_cargadores_cabecera', 0)
    n_patio = op.get('cargadores_patio', 0)
    vehiculos = flota * c.vehiculo_eur
    cargadores_cab = n_cab * c.cargador_pantografo_cabecera_eur
    cargadores_pat = n_patio * c.cargador_pistola_patio_eur
    subestacion = c.subestacion_electrica_eur
    deposito = flota * c.infraestructura_deposito_eur_bus
    total = vehiculos + cargadores_cab + cargadores_pat + subestacion + deposito
    return {
        'vehiculos': vehiculos,
        'cargadores_cabecera': cargadores_cab,
        'cargadores_patio': cargadores_pat,
        'subestacion': subestacion,
        'estacion_h2': 0.0,
        'infra_deposito': deposito,
        'total_capex': total,
    }


def calc_capex_opportunity(op: Dict[str, Any], c: CostCapexOpportunity) -> Dict[str, Any]:
    flota = op['flota_requerida']
    n_cab = op.get('n_cargadores_cabecera', 0)
    n_patio = op.get('cargadores_patio', 0)
    vehiculos = flota * c.vehiculo_eur
    cargadores_cab = n_cab * c.cargador_oportunidad_cabecera_eur
    cargadores_pat = n_patio * c.cargador_pistola_patio_eur
    subestacion = c.subestacion_electrica_eur
    deposito = flota * c.infraestructura_deposito_eur_bus
    total = vehiculos + cargadores_cab + cargadores_pat + subestacion + deposito
    return {
        'vehiculos': vehiculos,
        'cargadores_cabecera': cargadores_cab,
        'cargadores_patio': cargadores_pat,
        'subestacion': subestacion,
        'estacion_h2': 0.0,
        'infra_deposito': deposito,
        'total_capex': total,
    }


def calc_capex_hydrogen(op: Dict[str, Any], c: CostCapexHydrogen) -> Dict[str, Any]:
    flota = op['flota_requerida']
    vehiculos = flota * c.vehiculo_eur
    estacion = c.estacion_hidrogeno_eur
    deposito = flota * c.infraestructura_deposito_eur_bus
    total = vehiculos + estacion + deposito
    return {
        'vehiculos': vehiculos,
        'cargadores_cabecera': 0.0,
        'cargadores_patio': 0.0,
        'subestacion': 0.0,
        'estacion_h2': estacion,
        'infra_deposito': deposito,
        'total_capex': total,
    }


def calc_opex_anual_diesel(
    op: Dict[str, Any], c: CostOpexDiesel, dias: int
) -> Dict[str, Any]:
    combustible_dia = op['combustible_total_l'] * c.combustible_eur_litro
    mantenimiento_dia = op['km_totales_dia'] * c.mantenimiento_eur_km
    combustible_anual = combustible_dia * dias
    mantenimiento_anual = mantenimiento_dia * dias
    total = combustible_anual + mantenimiento_anual
    return {
        'combustible_energia': combustible_anual,
        'mantenimiento': mantenimiento_anual,
        'bateria_anual': 0.0,
        'total_opex_anual': total,
    }


def calc_opex_anual_overnight(
    op: Dict[str, Any], c: CostOpexOvernight, dias: int
) -> Dict[str, Any]:
    flota = op['flota_requerida']
    energia_dia = op.get('energia_total_patio_kwh', 0) * c.energia_eur_kwh
    mantenimiento_dia = op['km_totales_dia'] * c.mantenimiento_eur_km
    energia_anual = energia_dia * dias
    mantenimiento_anual = mantenimiento_dia * dias
    bateria_anual = flota * c.bateria_mantenimiento_anual_eur_bus
    total = energia_anual + mantenimiento_anual + bateria_anual
    return {
        'combustible_energia': energia_anual,
        'mantenimiento': mantenimiento_anual,
        'bateria_anual': bateria_anual,
        'total_opex_anual': total,
    }


def calc_opex_anual_flash(
    op: Dict[str, Any], c: CostOpexFlash, dias: int
) -> Dict[str, Any]:
    flota = op['flota_requerida']
    energia_dia = op.get('energia_total_dia_kwh', 0) * c.energia_eur_kwh
    mantenimiento_dia = op['km_totales_dia'] * c.mantenimiento_eur_km
    energia_anual = energia_dia * dias
    mantenimiento_anual = mantenimiento_dia * dias
    bateria_anual = flota * c.bateria_mantenimiento_anual_eur_bus
    total = energia_anual + mantenimiento_anual + bateria_anual
    return {
        'combustible_energia': energia_anual,
        'mantenimiento': mantenimiento_anual,
        'bateria_anual': bateria_anual,
        'total_opex_anual': total,
    }


def calc_opex_anual_opportunity(
    op: Dict[str, Any], c: CostOpexOpportunity, dias: int
) -> Dict[str, Any]:
    flota = op['flota_requerida']
    energia_dia = op.get('energia_total_dia_kwh', 0) * c.energia_eur_kwh
    mantenimiento_dia = op['km_totales_dia'] * c.mantenimiento_eur_km
    energia_anual = energia_dia * dias
    mantenimiento_anual = mantenimiento_dia * dias
    bateria_anual = flota * c.bateria_mantenimiento_anual_eur_bus
    total = energia_anual + mantenimiento_anual + bateria_anual
    return {
        'combustible_energia': energia_anual,
        'mantenimiento': mantenimiento_anual,
        'bateria_anual': bateria_anual,
        'total_opex_anual': total,
    }


def calc_opex_anual_hydrogen(
    op: Dict[str, Any], c: CostOpexHydrogen, dias: int
) -> Dict[str, Any]:
    h2_dia = op['h2_total_kg'] * c.hidrogeno_eur_kg
    mantenimiento_dia = op['km_totales_dia'] * c.mantenimiento_eur_km
    h2_anual = h2_dia * dias
    mantenimiento_anual = mantenimiento_dia * dias
    total = h2_anual + mantenimiento_anual
    return {
        'combustible_energia': h2_anual,
        'mantenimiento': mantenimiento_anual,
        'bateria_anual': 0.0,
        'total_opex_anual': total,
    }


def calc_tco(
    capex: Dict[str, Any],
    opex_anual: Dict[str, Any],
    horizonte: int,
    flota: int,
    reemplazo_eur: float = 0.0,
    vida_util_bat: int = 0,
) -> Dict[str, Any]:
    """Calcula el TCO año a año.

    Retorna:
        anual: lista de dicts con desglose por año (0 = CAPEX, 1..n = OPEX).
        total_tco: suma total.
    """
    anual = []
    acumulado = 0.0

    for y in range(horizonte + 1):
        entry: Dict[str, Any] = {'anio': y}
        if y == 0:
            entry['capex'] = capex['total_capex']
            entry['opex'] = 0.0
            entry['reemplazo_bateria'] = 0.0
            entry['total_anio'] = capex['total_capex']
        else:
            entry['capex'] = 0.0
            entry['opex'] = opex_anual['total_opex_anual']
            # Reemplazo de batería en los años correspondientes
            reemplazo = 0.0
            if vida_util_bat > 0 and reemplazo_eur > 0 and y % vida_util_bat == 0 and y < horizonte:
                reemplazo = flota * reemplazo_eur
            entry['reemplazo_bateria'] = reemplazo
            entry['total_anio'] = entry['opex'] + reemplazo
        acumulado += entry['total_anio']
        entry['acumulado'] = acumulado
        anual.append(entry)

    return {
        'anual': anual,
        'total_tco': acumulado,
    }


def calc_all_costs(
    operational_results: Dict[str, Dict[str, Any]],
    cost_general: CostGeneralInputs,
    capex_diesel: CostCapexDiesel | None = None,
    capex_overnight: CostCapexOvernight | None = None,
    capex_flash: CostCapexFlash | None = None,
    capex_opportunity: CostCapexOpportunity | None = None,
    capex_hydrogen: CostCapexHydrogen | None = None,
    opex_diesel: CostOpexDiesel | None = None,
    opex_overnight: CostOpexOvernight | None = None,
    opex_flash: CostOpexFlash | None = None,
    opex_opportunity: CostOpexOpportunity | None = None,
    opex_hydrogen: CostOpexHydrogen | None = None,
) -> Dict[str, Dict[str, Any]]:
    """Calcula CAPEX, OPEX anual y TCO para todas las tecnologías disponibles."""
    dias = cost_general.dias_operacion_anio
    horizonte = cost_general.horizonte_anios
    out: Dict[str, Dict[str, Any]] = {}

    # --- Diesel ---
    if 'diesel' in operational_results and capex_diesel and opex_diesel:
        op = operational_results['diesel']
        capex = calc_capex_diesel(op, capex_diesel)
        opex = calc_opex_anual_diesel(op, opex_diesel, dias)
        tco = calc_tco(capex, opex, horizonte, op['flota_requerida'])
        out['diesel'] = {'capex': capex, 'opex': opex, 'tco': tco}

    # --- Overnight ---
    if 'overnight' in operational_results and capex_overnight and opex_overnight:
        op = operational_results['overnight']
        capex = calc_capex_overnight(op, capex_overnight)
        opex = calc_opex_anual_overnight(op, opex_overnight, dias)
        tco = calc_tco(
            capex, opex, horizonte, op['flota_requerida'],
            opex_overnight.bateria_reemplazo_eur,
            opex_overnight.bateria_vida_util_anios,
        )
        out['overnight'] = {'capex': capex, 'opex': opex, 'tco': tco}

    # --- Flash ---
    if 'flash' in operational_results and capex_flash and opex_flash:
        op = operational_results['flash']
        capex = calc_capex_flash(op, capex_flash)
        opex = calc_opex_anual_flash(op, opex_flash, dias)
        tco = calc_tco(
            capex, opex, horizonte, op['flota_requerida'],
            opex_flash.bateria_reemplazo_eur,
            opex_flash.bateria_vida_util_anios,
        )
        out['flash'] = {'capex': capex, 'opex': opex, 'tco': tco}

    # --- Opportunity ---
    if 'opportunity' in operational_results and capex_opportunity and opex_opportunity:
        op = operational_results['opportunity']
        capex = calc_capex_opportunity(op, capex_opportunity)
        opex = calc_opex_anual_opportunity(op, opex_opportunity, dias)
        tco = calc_tco(
            capex, opex, horizonte, op['flota_requerida'],
            opex_opportunity.bateria_reemplazo_eur,
            opex_opportunity.bateria_vida_util_anios,
        )
        out['opportunity'] = {'capex': capex, 'opex': opex, 'tco': tco}

    # --- Hydrogen ---
    if 'hydrogen' in operational_results and capex_hydrogen and opex_hydrogen:
        op = operational_results['hydrogen']
        capex = calc_capex_hydrogen(op, capex_hydrogen)
        opex = calc_opex_anual_hydrogen(op, opex_hydrogen, dias)
        tco = calc_tco(capex, opex, horizonte, op['flota_requerida'])
        out['hydrogen'] = {'capex': capex, 'opex': opex, 'tco': tco}

    return out
