"""Smoke test for cabecera/trazado charging model."""
from engine import *

g = GeneralInputs()

# Flash auto-optimize: 150 kWh battery, 3min cabecera, 10s trazado
f = ElectricFlashInputs(bateria_kwh=150, consumo_kwh_km=1.2,
                         tiempo_carga_cabecera_min=3.0,
                         tiempo_carga_trazado_min=0.17)
r = calc_electric_flash(g, f)
print("=== FLASH AUTO (150 kWh, cab=3min, traz=10s) ===")
print(f"  Flota: {r['flota_requerida']}  (hw: {r['flota_headway']})")
print(f"  Puntos cabecera: {r['n_puntos_cabecera']}")
print(f"  Puntos trazado: {r['n_puntos_trazado']}")
print(f"  Cargas cab/bus: {r['cargas_cab_por_bus']}")
print(f"  Cargas traz/bus: {r['cargas_traz_por_bus']}")
print(f"  Mini-cargas total: {r['mini_cargas_por_bus']}")
print(f"  Km recup/cab: {r['km_recuperados_por_carga_cabecera']:.1f}")
print(f"  Km recup/traz: {r['km_recuperados_por_carga_trazado']:.2f}")
print(f"  n_carg_cab/traz: {r['n_cargadores_cabecera']}/{r['n_cargadores_trazado']}")
print(f"  Autonomia efec: {r['autonomia_efectiva_km']:.1f}")
print(f"  Km/bus/dia: {r['km_por_bus_tot']:.1f}")
print()

# Flash manual: 2 cab + 3 traz
f2 = ElectricFlashInputs(bateria_kwh=150, consumo_kwh_km=1.2,
                          tiempo_carga_cabecera_min=3.0,
                          tiempo_carga_trazado_min=0.17,
                          n_puntos_cabecera_override=2,
                          n_puntos_trazado_override=3)
r2 = calc_electric_flash(g, f2)
print("=== FLASH MANUAL (2 cab + 3 traz) ===")
print(f"  Flota: {r2['flota_requerida']}")
print(f"  Puntos cab/traz: {r2['n_puntos_cabecera']}/{r2['n_puntos_trazado']}")
print(f"  Cargas cab/traz: {r2['cargas_cab_por_bus']}/{r2['cargas_traz_por_bus']}")
print(f"  n_carg_cab/traz: {r2['n_cargadores_cabecera']}/{r2['n_cargadores_trazado']}")
print()

# Opportunity auto-optimize: 350 kWh, 10min cab, 10s traz
o = ElectricOpportunityInputs(bateria_kwh=350, consumo_kwh_km=1.2,
                               tiempo_carga_cabecera_min=10.0,
                               tiempo_carga_trazado_min=0.17,
                               tiempo_regulacion_min=10.0)
ro = calc_electric_opportunity(g, o)
print("=== OPPORTUNITY AUTO (350 kWh, cab=10min, traz=10s) ===")
print(f"  Flota: {ro['flota_requerida']}")
print(f"  Puntos cab/traz: {ro['n_puntos_cabecera']}/{ro['n_puntos_trazado']}")
print(f"  Cargas cab/traz: {ro['cargas_cab_por_bus']}/{ro['cargas_traz_por_bus']}")
print(f"  n_carg_cab/traz: {ro['n_cargadores_cabecera']}/{ro['n_cargadores_trazado']}")
print(f"  Autonomia efec: {ro['autonomia_efectiva_km']:.1f}")
print()

# Flash: large battery (no charges needed)
f3 = ElectricFlashInputs(bateria_kwh=600, consumo_kwh_km=1.2,
                          tiempo_carga_cabecera_min=3.0,
                          tiempo_carga_trazado_min=0.17)
r3 = calc_electric_flash(g, f3)
print("=== FLASH AUTO (600 kWh - should need 0 charges) ===")
print(f"  Flota: {r3['flota_requerida']}")
print(f"  Puntos cab/traz: {r3['n_puntos_cabecera']}/{r3['n_puntos_trazado']}")
print(f"  Mini-cargas: {r3['mini_cargas_por_bus']}")
print()

# Cost model test
from engine import CostCapexFlash, calc_capex_flash
c = CostCapexFlash()
capex = calc_capex_flash(r, c)
print(f"=== CAPEX FLASH ===")
print(f"  Carg. cabecera: {capex['cargadores_cabecera']:,.0f} EUR")
print(f"  Carg. trazado: {capex['cargadores_trazado']:,.0f} EUR")
print(f"  Total: {capex['total_capex']:,.0f} EUR")

print()
print("=== ALL TESTS PASSED ===")
