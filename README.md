# 🚌 Planes de operación – Evaluador de tecnologías de buses

Herramienta en **Python + Streamlit** que transforma el Excel
**Planes de operación_tenologias.xlsx** en un motor de cálculo paramétrico
para comparar tecnologías de operación de buses:

- Diésel
- Eléctrico nocturno (overnight)
- Eléctrico carga de oportunidad / flash
- Hidrógeno

---

## 📋 1) Requisitos

- Python 3.10+ instalado.
- Acceso a internet (para cargar fuentes y recursos de Streamlit).

---

## 🛠️ 2) Instalación

En una terminal, dentro de la carpeta del proyecto:

```bash
python -m venv .venv

# mac / linux
source .venv/bin/activate

# windows
.venv\Scripts\activate

pip install -r requirements.txt
```

---

## ▶️ 3) Cómo usar la aplicación

1. Activa el entorno virtual (ver sección anterior).
2. Lanza la app Streamlit:

	 ```bash
	 streamlit run app.py
	 ```

3. Se abrirá el navegador con la interfaz gráfica:
	 - En la **barra lateral** ajustas los *inputs generales* de operación
		 (longitud de trazado, velocidad, headway, tiempo de servicio, % km en vacío, etc.).
	 - En las secciones de cada **tecnología** defines parámetros específicos
		 (autonomía diésel, tamaño de batería, consumos energéticos, potencias de carga,
		 eficiencia de carga, etc.).
	 - En el área central se muestran:
		 - Flota requerida por tecnología.
		 - Km/año por flota.
		 - Energía o combustible consumido.
		 - Potencias de carga necesarias (en el caso de eléctricos e hidrógeno).

---

## 🧱 4) Estructura del proyecto

- [engine.py](engine.py): motor de cálculo donde se implementa la lógica que antes estaba en el Excel.
- [app.py](app.py): interfaz Streamlit que llama a las funciones de cálculo y presenta los resultados al usuario.
- [Planes de operación_tenologias.xlsx](Planes%20de%20operaci%C3%B3n_tenologias.xlsx): archivo original de referencia sobre el que se basan las fórmulas.

Ejecutando `streamlit run app.py`, la app utiliza directamente las fórmulas de
[engine.py](engine.py) para recalcular todo en tiempo real cuando cambias los
parámetros.

---

## 📊 5) Tecnologías modeladas (resumen visual)

| Tecnología                | Energía base      | Dónde "ocurre" la recarga                           |
|--------------------------|-------------------|------------------------------------------------------|
| Diésel                   | Litros de diésel  | Surtidor convencional                                |
| Eléctrico nocturno       | kWh en batería    | Principalmente en patio (ventana nocturna)          |
| Eléctrico flash/oportunidad | kWh en batería | Cargas cortas en ruta + posible carga en patio      |
| Hidrógeno                | kg de H₂          | Estación de hidrógeno (producción/almacenamiento)   |

---

## 🧮 6) Resumen de la lógica de cálculo

De forma simplificada, el modelo sigue estos pasos principales:

- **Flota por headway**: se calcula el tiempo de ciclo ida+vuelta (incluyendo
	regulación/ES) y se aplica:
  
	$\text{Flota} = \lceil T_{ciclo} / \text{headway} \rceil$

- **Km comerciales y totales por día**:
  
	$\text{Km\_comerciales\_día} = 2 \cdot (T_{servicio} / \text{headway}) \cdot L$
  
	$\text{Km\_totales\_día} = \text{Km\_comerciales\_día} \cdot (1 + p_{vacío})$

- **Consumo de combustible/energía**:
	- *Diésel*: se multiplican los km totales por el consumo [l/km] y se verifica que
		la autonomía [km] cubre los km por bus.
	- *Eléctricos*: se usa el consumo [kWh/km] y la energía útil de batería
		(considerando $SOC_{reserva}$) para comprobar que la autonomía cubre los ciclos previstos.

- **Estrategias de carga**:
	- **Eléctrico nocturno**: se concentra la carga en una ventana nocturna,
		dimensionando la potencia de cargadores en patio para reponer la energía diaria.
	- **Flash / oportunidad**: se estima la energía que debe cargarse en cada
		parada/terminal (mini-cargas) según el tiempo disponible y la potencia de los
		cargadores en ruta; si es necesario, se complementa con carga en patio.
	- **Hidrógeno**: se calcula el consumo [kg/100 km] a partir de los km totales y
		se pueden derivar requerimientos de producción/almacenamiento (según los
		supuestos del motor).

Todos estos cálculos están implementados en clases de entrada y funciones en
[engine.py](engine.py), de forma que puedes ajustar o sustituir fácilmente
cualquier supuesto.
