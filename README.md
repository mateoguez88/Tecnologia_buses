# 🚌 Evaluador de Tecnologías de Buses

Herramienta interactiva en **Python + Streamlit** para el análisis comparativo
de tecnologías de operación de flotas de buses urbanos. Cubre tanto el
**dimensionamiento operacional** como el **análisis financiero completo**
(CAPEX, OPEX, TCO).

Tecnologías soportadas:

| Tecnología | Energía | Recarga |
|---|---|---|
| ⛽ Diésel | Litros de diésel | Surtidor convencional |
| 🔋 Eléctrico nocturno (overnight) | kWh en batería | Patio – ventana nocturna |
| ⚡ Eléctrico flash | kWh en batería | Mini-cargas en ruta + patio |
| 🔌 Eléctrico oportunidad | kWh en batería | Cargas en cabecera + patio |
| 💧 Hidrógeno (FCEV) | kg de H₂ | Estación de hidrógeno |

---

## 📋 1) Requisitos

- Python 3.10+
- Acceso a internet (fuentes tipográficas y recursos de Streamlit)

---

## 🛠️ 2) Instalación

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Dependencias principales: `streamlit`, `pandas`, `plotly`, `openpyxl`.

---

## ▶️ 3) Uso

```bash
streamlit run app.py
```

La aplicación tiene **dos páginas** con navegación automática en el menú lateral:

### Página 🚌 Operación (`app.py`)

- **Barra lateral**: inputs generales de ruta (longitud, velocidad, headway,
  tiempo de servicio, % km en vacío, etc.) y parámetros por tecnología
  (autonomía, batería, consumos, potencias de carga, eficiencia).
- **Área central**:
  - Tarjetas resumen: flota requerida, km/día, energía consumida.
  - Tabla de métricas principales con ciclos, mini-cargas y repostaje.
  - Gráficos interactivos: flota y operación, energía y potencia,
    infraestructura de carga, detalle flash/oportunidad.
- **📥 Exportar a Excel**: descarga `comparador_operacion.xlsx` con hojas
  de *Inputs* y *Operación*.

### Página 💰 Costos (`pages/2_💰_Costos.py`)

- **Barra lateral**: horizonte del proyecto (años) y días de operación/año.
- **Tabs por tecnología**: parámetros CAPEX (vehículo, cargadores,
  subestación, estación H₂, infraestructura depósito) y OPEX
  (combustible/energía, mantenimiento/km, batería).
- **Área central**:
  - Tarjetas resumen: CAPEX, OPEX/año, TCO, €/km por tecnología.
  - Gráficos: CAPEX vs OPEX, desglose CAPEX y OPEX por componente,
    evolución temporal del TCO (con marcadores de reemplazo de batería),
    costo por km y TCO por bus.
  - Tabla comparativa transpuesta con desglose completo.
- **📥 Exportar a Excel**: descarga `comparador_completo.xlsx` con hojas
  de *Inputs*, *Operación* y *Costos* (formateado con colores y estilos).

---

## 🧱 4) Estructura del proyecto

```
.
├── app.py                      # Página principal: análisis operacional
├── engine.py                   # Motor de cálculo (operación + costos)
├── utils.py                    # Estilos, constantes, exportación Excel
├── requirements.txt            # Dependencias Python
├── pages/
│   └── 2_💰_Costos.py          # Página de análisis financiero
└── Planes de operación_tenologias.xlsx  # Excel de referencia
```

| Archivo | Descripción |
|---|---|
| **engine.py** | Dataclasses de entrada + funciones puras de cálculo. Módulo operacional (`calc_diesel`, `calc_electric_*`, `calc_hydrogen`, `run_all`) y módulo de costos (`calc_capex_*`, `calc_opex_anual_*`, `calc_tco`, `calc_all_costs`). |
| **app.py** | Página Streamlit de operación. Guarda resultados en `st.session_state` para compartirlos con la página de costos. |
| **pages/2_💰_Costos.py** | Análisis económico: CAPEX, OPEX, TCO con visualizaciones interactivas. |
| **utils.py** | Constantes de colores/iconos, CSS global, helpers de formato y **generador de reportes Excel** con openpyxl (hojas formateadas con colores por tecnología, bordes, freeze panes). |

---

## 🧮 5) Lógica de cálculo

### Operación

- **Flota por headway**:
  `Flota = ⌈ T_ciclo / headway ⌉`

- **Km/día**:
  `Km_com = 2 × (T_servicio / headway) × L`
  `Km_tot = Km_com × (1 + p_vacío)`

- **Consumo**: diésel [L/km], eléctricos [kWh/km] con SOC reserva,
  hidrógeno [kg/km].

- **Estrategias de carga**:
  - *Nocturna*: ventana nocturna en patio, dimensiona potencia instalada.
  - *Flash / oportunidad*: mini-cargas en ruta (pantógrafo/conector) +
    complemento en patio.
  - *Hidrógeno*: consumo directo desde estación.

### Costos

- **CAPEX**: vehículos × flota + cargadores + subestación + infraestructura.
- **OPEX anual**: (combustible/energía + mantenimiento/km + batería) × días/año.
- **TCO**: CAPEX (año 0) + Σ OPEX (años 1..n) + reemplazos de batería
  periódicos.
- **€/km** y **€/bus** derivados del TCO total.

Todos los cálculos están implementados como funciones puras en `engine.py`,
fácilmente ajustables y testeables.
