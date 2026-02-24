#!/bin/bash

# Instalar dependencias
pip install -r /home/site/wwwroot/requirements.txt

# Iniciar Streamlit
python -m streamlit run /home/site/wwwroot/app.py \
    --server.port 8000 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
