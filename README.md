# Planes de operación – Herramienta en Python

Este proyecto convierte el Excel **Planes de operación_tenologias.xlsx** en una herramienta paramétrica.

## 1) Instalación

```bash
python -m venv .venv
# source .venv/bin/activate  # mac/linux
 .venv\Scripts\activate   # windows
pip install -r requirements.txt
```

## 2) Ejecutar la app

```bash
streamlit run app.py
```

## 3) Estructura

- `engine.py`: motor de cálculo (fórmulas y lógica).
- `app.py`: interfaz Streamlit para modificar inputs y comparar tecnologías.

## 4) Notas de modelo

- La **flota por headway** se calcula como `ceil(T_ciclo / headway)`.
- Los **km/día** se calculan con `2 * (T_servicio/headway) * L`.
- En **eléctrico nocturno**, se agrega restricción por autonomía diaria (sin cargas en ruta).
- En **flash/oportunidad**, se estiman “mini-cargas” necesarias para cubrir los km por bus.

Puedes adaptar o reemplazar cualquier supuestos en `engine.py`.
