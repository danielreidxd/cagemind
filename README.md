# UFC Fight Predictor

Sistema de Predicción de Peleas UFC con Machine Learning.

## Estructura del Proyecto

```
ufc-fight-predictor/
├── config/             # Configuración global (rutas, constantes, logging)
├── data/
│   ├── scrapers/       # Scripts de scraping por fuente
│   ├── raw/            # Datos crudos descargados (HTML, JSON)
│   ├── processed/      # Datos limpios listos para DB
│   └── exports/        # CSVs exportados como respaldo
├── db/                 # Esquema SQLite y utilidades de BD
├── logs/               # Logs de ejecución de scrapers
├── ml/                 # Modelos de machine learning (Fase 4)
├── notebooks/          # Jupyter notebooks de análisis (Fase 2-3)
├── backend/            # API FastAPI (Fase 5)
├── frontend/           # React + TypeScript (Fase 6)
└── docs/               # Documentación del proyecto
```

## Fase 1 — Recolección de Datos (UFCStats.com)

### Requisitos

- Python 3.10+
- pip

### Instalación

```bash
cd ufc-fight-predictor
pip install -r requirements.txt
```

### Ejecución

El scraping se ejecuta en 3 pasos secuenciales:

```bash
# Paso 1: Scrapear lista de todos los peleadores
python -m data.scrapers.ufcstats_fighters

# Paso 2: Scrapear detalles de cada evento y pelea
python -m data.scrapers.ufcstats_events

# Paso 3: Scrapear estadísticas detalladas por pelea (round-by-round)
python -m data.scrapers.ufcstats_fight_stats

# Paso 4: Limpiar y normalizar datos, cargar a SQLite
python -m data.scrapers.pipeline
```

O ejecuta todo de una vez:

```bash
python run_phase1.py
```

### Notas Importantes

- **Rate limiting**: Los scrapers incluyen delays entre requests (1-2s) para no sobrecargar los servidores.
- **Reanudación**: Si un scraper falla a mitad, puede reanudar desde donde se quedó gracias al sistema de checkpoints.
- **Logs**: Toda la ejecución se registra en `logs/`.
- **Datos crudos**: Se guardan en `data/raw/` como respaldo antes de cualquier transformación.
- **Tiempo estimado**: El scraping completo puede tomar 4-8 horas dependiendo de la cantidad de peleadores/peleas.
