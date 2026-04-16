# 🥊 CageMind — Inteligencia de Peleas MMA

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Deploy](https://img.shields.io/badge/Deploy-Production-0B0D0E?logo=vercel)](https://cagemind.app)

> **Sistema de Predicción de Peleas UFC impulsado por Machine Learning**  
> CageMind combina web scraping, análisis de datos y modelado predictivo para ofrecer insights estadísticos y pronósticos de probabilidad de victoria en peleas de MMA.

🌐 **Demo en Vivo**: [cagemind.app](https://cagemind.app)  
📊 **Fuente de Datos**: UFC Stats • Sherdog • Registros Oficiales de la UFC  
🌎 *[Read in English](README.md)*

---

## ✨ Características Principales

### 🔮 Predicciones Inteligentes de Peleas
- **Pronósticos con ML**: Modelos XGBoost con Platt scaling para probabilidades de victoria calibradas
- **Métricas de Confianza**: Cada predicción incluye puntajes de confiabilidad y factores clave influyentes
- **Análisis Head-to-Head**: Compara estadísticas, estilos y rendimiento histórico de luchadores lado a lado

### 📊 Analítica Avanzada
- **Perfiles de Luchadores**: Desgloses detallados de métricas de striking, grappling y cardio
- **Detección de Tendencias**: Identifica patrones de rendimiento por categorías de peso y eras
- **Insights de Eventos**: Estadísticas pre-pelea y análisis post-evento para cada cartelera de la UFC

### 🔄 Pipeline de Datos Automatizado
- **Scraping Multi-Fuente**: Recopila datos de UFCStats.com, Sherdog y registros oficiales
- **Sistema de Checkpoints**: Reanuda scrapings interrumpidos sin pérdida de datos ni duplicados
- **Rate Limiting & Logging**: Crawling respetuoso con transparencia total de ejecución

### 🗄️ Capa de Datos Estructurada
- **Base de Datos SQLite**: Esquema optimizado para consultas rápidas en historiales de luchadores y resultados
- **Estadísticas Normalizadas**: Datos ronda por ronda limpios y listos para análisis o entrenamiento de ML
- **Opciones de Exportación**: Descarga datasets procesados en formato CSV para uso externo

### 🌐 API Lista para Desarrolladores
- **Endpoints RESTful**: Consulta luchadores, eventos y predicciones vía API JSON
- **Documentación Swagger**: Docs interactivas de la API en `/docs` para integración sencilla
- **Autenticación Lista**: Soporte JWT para rutas protegidas (configurable)

### 🎨 Experiencia de Frontend Moderna
- **React + TypeScript**: UI responsiva y tipada construida con Vite
- **Visualizaciones Interactivas**: Gráficos y comparativas potenciadas por Recharts/D3
- **Soporte para Modo Oscuro**: Diseño consciente de las preferencias del usuario para una visualización cómoda

---

## 🗂️ Estructura del Proyecto
<details>
<summary><b>📁 Ver estructura completa del proyecto</b></summary>
cagemind/
├── .github/
│ └── workflows/ # Pipelines de CI/CD (GitHub Actions)
├── config/ # Configuración y variables de entorno
│ ├── init.py
│ └── settings.py
├── data/
│ ├── init.py
│ ├── checkpoints/ # Checkpoints para scrapers resumibles
│ ├── exports/ # Exportaciones CSV
│ ├── raw/ # Descargas HTML/JSON en crudo
│ └── scrapers/ # Scrapers de UFC Stats y Sherdog
├── db/ # Esquema SQLite y utilidades
│ ├── init.py
│ ├── schema.py
│ └── ufc_predictor.db # Base de datos SQLite
├── ml/ # Modelos, entrenamiento y predicciones
│ ├── calibration/ # Platt scaling y calibración de modelos
│ ├── models/ # Modelos entrenados (.pkl, .json)
│ ├── results/ # Métricas y logs de entrenamiento
│ └── semana1/ # Notebooks/análisis por iteración
├── backend/ # Aplicación FastAPI
│ ├── init.py
│ ├── app.py # Punto de entrada FastAPI
│ ├── auth.py # Lógica de autenticación JWT
│ ├── config.py # Configuración específica del backend
│ ├── database.py # Conexión a BD y gestión de sesiones
│ ├── schemas.py # Modelos Pydantic (consolidado)
│ ├── routers/ # Endpoints de API modularizados
│ │ ├── init.py
│ │ ├── admin.py
│ │ ├── analytics.py
│ │ ├── auth.py
│ │ ├── events.py
│ │ ├── fighters.py
│ │ ├── odds.py
│ │ ├── picks.py
│ │ ├── predictions.py
│ │ └── stats.py
│ └── services/ # Capa de lógica de negocio
│ ├── init.py
│ ├── explainability.py
│ ├── fighters.py
│ ├── odds.py
│ └── predictions.py
├── frontend/ # App React + TypeScript (Vite)
│ ├── index.html
│ ├── package.json
│ ├── package-lock.json
│ ├── postcss.config.js
│ ├── tailwind.config.js
│ ├── tsconfig.json
│ ├── tsconfig.node.json
│ ├── vercel.json # Configuración de deploy para Vercel
│ ├── vite.config.ts
│ ├── public/
│ └── src/
│ ├── App.tsx
│ ├── main.tsx
│ ├── index.css
│ ├── config.ts
│ ├── vite-env.d.ts
│ ├── components/
│ ├── contexts/ # Providers de React Context
│ ├── hooks/ # Custom React hooks
│ ├── pages/
│ ├── services/ # Servicios cliente de API
│ ├── types/ # Interfaces de TypeScript
│ └── utils/
├── notebooks/
│ ├── 01_distribucion_peso.png
│ ├── 02_distribucion_stance.png
│ ├── ... (más visualizaciones)
│ └── deep/
├── scripts/ # Scripts utilitarios
│ ├── scraping/ # Scripts de scraping standalone
│ └── training/ # Scripts de entrenamiento ML
├── .gitignore
├── Procfile # Configuración de deploy (Railway/Heroku)
├── nixpacks.toml # Configuración de build para Nixpacks
├── requirements.txt
├── runtime.txt # Fijación de versión de Python
├── upload_to_supabase.py # Script para Supabase
└── README.md
└── Readme.es.md
</details>

---

## 📺 Demos del Proyecto

### 🔮 Inteligencia Predictiva en Acción
![Image](https://github.com/user-attachments/assets/37e89934-bdb4-4251-ba75-fbc879204e42)

<br />

| 🔍 SandBox | 📊 soon |
| :---: | :---: |
| ![Image](https://github.com/user-attachments/assets/32279e9c-850d-4dbd-9c29-ad5b21917588) | ![Image](https://github.com/user-attachments/assets/e82ea534-b8ca-4a51-bd43-e132174d25aa) |

---

## 🧠 Modelos de Machine Learning

CageMind utiliza un enfoque de ensemble multi-modelo para predecir diferentes facetas de una pelea. Cada modelo está optimizado para su tarea específica, superando significativamente las probabilidades aleatorias base.

### 📊 Rendimiento de Modelos y Benchmarks

| Modelo | Algoritmo | Accuracy | Benchmark |
| :--- | :--- | :--- | :--- |
| **Ganador (Win/Loss)** | XGBoost | **64.8%** | 65-70% (Oddsmakers) |
| **Método de Victoria** | Reg. Logística | **51.2%** | 33.3% (Aleatorio) |
| **Finish vs. Decisión** | Random Forest | **59.9%** | 50.0% (Aleatorio) |
| **Predicción de Round** | XGBoost | **44.5%** | 25.0% (Aleatorio) |

### 🛠️ Estrategia de Modelado
- **XGBoost (Ganador y Round):** Aprovecha el gradient boosting para manejar relaciones no lineales entre estadísticas de luchadores (ej. ventaja de alcance vs. precisión de takedowns).
- **Regresión Logística (Método):** Proporciona probabilidades bien calibradas para resultados categóricos (KO/TKO, Sumisión, Decisión).
- **Random Forest (Duración):** Excelente para capturar importancia de características y determinar si el estilo de matchup lleva a un finish.

---

## 🛠️ Stack Tecnológico

### 🔙 Backend e Ingeniería de Datos
| Tecnología | Propósito | Versión |
|------------|-----------|---------|
| **Python** | Lenguaje principal para scraping, ML y API | 3.10+ |
| **FastAPI** | Framework REST API de alto rendimiento | 0.104+ |
| **Supabase/PostgreSQL** | Base de datos relacional ligera basada en archivos | 3.x |
| **Pandas** | Manipulación y análisis de datos | 2.x |
| **NumPy** | Cómputo numérico y operaciones con arrays | 1.24+ |
| **Scikit-learn** | Utilidades de ML, preprocesamiento, evaluación de modelos | 1.3+ |
| **XGBoost** | Gradient boosting para modelos de predicción de peleas | 1.7+ |
| **Requests + BeautifulSoup4** | Cliente HTTP y parsing HTML para scraping | latest |
| **lxml** | Parser rápido de XML/HTML para tareas complejas de scraping | 4.9+ |

### 🎨 Frontend
| Tecnología | Propósito | Versión |
|------------|-----------|---------|
| **React** | Librería de UI basada en componentes | 18.x |
| **TypeScript** | Desarrollo JavaScript con tipado seguro | 5.x |
| **Vite** | Herramienta de build rápida y servidor de desarrollo | 4.x |
| **Recharts** | Librería de gráficos declarativa para visualización de datos | 2.x |
| **Tailwind CSS** *(opcional)* | Framework CSS utility-first | 3.x |

### 🚀 DevOps e Infraestructura
| Herramienta | Propósito |
|-------------|-----------|
| **Vercel** | Deploy de frontend con CDN y edge functions |
| **Railway / Render** | Hosting de API backend con auto-deploy desde GitHub |
| **GitHub Actions** | Pipelines de CI/CD, testing automatizado y scrapings programados |
| **pre-commit** | Hooks de calidad de código (linting, formatting) |

### 🧪 Testing y Calidad
| Herramienta | Propósito |
|-------------|-----------|
| **pytest** | Testing unitario e integración para código Python |
| **Jest + React Testing Library** | Testing de componentes frontend |
| **Black + isort** | Formateo de código y ordenamiento de imports |
| **Flake8 / Ruff** | Linting para cumplimiento de PEP8 |

---

## ⚡ Inicio Rápido

Ejecuta el proyecto localmente en 3 pasos.

### 🔧 Prerrequisitos
Asegúrate de tener instalados:
- **Python 3.10+** (para Backend y ML)
- **Node.js 18+** (para Frontend)
- **Git**

---

### 🛠️ Paso 1: Instalación

#### Backend (Python)
```bash
# Clonar el repositorio
git clone https://github.com/danielreidxd/cagemind.git
cd cagemind

# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```
Frontend (React)
```bash
cd frontend

# Instalar dependencias
npm install
```
⚙️ Paso 2: Configuración
Crea un archivo .env en el directorio raíz:
```bash
# Configuración de base de datos
DATABASE_URL=sqlite:///./cagemind.db

# Configuración de API
API_KEY=your_secret_api_key
ENV=development
```

🚀 Paso 3: Ejecutar la Aplicación
A) Ejecutar el Pipeline de Datos (Scraping)
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
✅ API: http://localhost:8000 | 📚 Docs: http://localhost:8000/docs
C) Iniciar el Frontend
```bash
cd frontend
npm run dev
```
✅ App: http://localhost:5173
📊 Esquema de Base de Datos y Flujo de Datos
🗄️ Visión General del Esquema
Estructura de la Base de Datos

| Tabla | Descripción | Campos Clave |
|---|---|---|
| `fighters` | Perfiles de luchadores y atributos físicos | `id`, `name`, `nickname`, `height`, `weight`, `reach`, `stance`, `record` |
| `events` | Metadatos de eventos de la UFC | `id`, `name`, `date`, `location`, `venue` |
| `fights` | Resultados de los combates y metadatos | `id`, `event_id`, `fighter_a_id`, `fighter_b_id`, `winner_id`, `method`, `round`, `time` |
| `fight_stats` | Datos de rendimiento por asalto | `fight_id`, `fighter_id`, `sig_strikes`, `takedowns`, `submissions`, `control_time` |
| `predictions` | Pronósticos de ML (Machine Learning) | `id`, `fight_id`, `fighter_a_prob`, `fighter_b_prob`, `model_version`, `confidence` |

🔗 Relaciones: events → fights → fighters → fight_stats
📖 Esquema completo: db/schema.sql

```mermaid
graph TD
    A["[UFC Stats / Sherdog]"] -->|Scraping Paralelo + Rate Limiting| B["[HTML/JSON Crudo]"]
    B -->|Limpieza y Validación| C["[Datos Normalizados]"]
    C -->|Inserción Masiva con Transacciones| D[("Base de Datos SQLite")]

    D --> E{ }
        E --- E1[ ]
        E --- E2[ ]
        E --- E3[ ]

    E1 --> F["[Capa API REST]"]
        E2 --> G["[Feature Store para ML]"]
        E3 --> H["[Consultas del Frontend]"]

    style E fill:none,stroke:none
    style E1 fill:none,stroke:none
    style E2 fill:none,stroke:none
    style E3 fill:none,stroke:none
```

🔮 Predicciones de ML y Uso de la API
🌐 Endpoints Principales
Documentación de la API
| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/fighters` | Buscar y filtrar perfiles de luchadores |
| `GET` | `/api/fights/{id}` | Obtener detalles de pelea, stats e historial |
| `POST` | `/api/predict` | Obtener probabilidades de victoria con ML |
| `GET` | `/api/events` | Explorar carteleras de UFC pasadas y futuras |
| `GET` | `/api/stats/trends` | Tendencias de rendimiento agregadas por categoría de peso |

📖 Swagger UI: https://cagemind.app/api/docs
💻 Ejemplo en Python
```python
import requests

API_BASE = "https://cagemind.app/api"

response = requests.post(
    f"{API_BASE}/predict",
    json={
        "fighter_a": "Alex Pereira",
        "fighter_b": "Magomed Ankalaev",
        "weight_class": "Light Heavyweight"
    }
)

result = response.json()
print(f"Pereira win prob: {result['predictions']['fighter_a']['win_probability']:.1%}")
print(f"Confidence: {result['predictions']['fighter_a']['confidence'].upper()}")
```

🌐 Ejemplo en cURL
```bash
curl -X POST "https://cagemind.app/api/predict" \
     -H "Content-Type: application/json" \
     -d '{
       "fighter_a": "Islam Makhachev",
       "fighter_b": "Charles Oliveira",
       "weight_class": "Lightweight"
     }'
```
📤 Respuesta de Ejemplo
```bash
{
  "fight_id": "ufc-294-pereira-vs-ankalaev",
  "predictions": {
    "fighter_a": {
      "name": "Alex Pereira",
      "win_probability": 0.58,
      "confidence": "high",
      "key_advantages": ["striking_power", "takedown_defense"]
    },
    "fighter_b": {
      "name": "Magomed Ankalaev",
      "win_probability": 0.42,
      "confidence": "high",
      "key_advantages": ["wrestling_volume", "cardio"]
    }
  },
  "model_version": "xgboost_v2.3",
  "features_used": 47,
  "generated_at": "2026-04-11T14:22:00Z"
}
```

🧪 Testing, CI/CD y Deployment
✅ Estrategia de Testing
Testing y Aseguramiento de Calidad
| Componente | Comando | Cobertura |
|---|---|---|
| Tests Unitarios Backend | `pytest backend/tests/ -v` | Rutas de API, consultas a BD |
| Tests de Pipeline ML | `pytest ml/tests/ -v` | Extracción de features, inferencia |
| Tests de Frontend | `cd frontend && npm test` | Componentes, routing |
| Tests de Integración | `pytest tests/integration/ -v` | Flujo completo: scrape → predict |

📊 Reporte de cobertura:
```bash
pytest --cov=backend --cov=ml --cov-report=html
```

🔄 Pipeline de CI/CD (GitHub Actions)
```yaml
# .github/workflows/ci.yml
name: CI/CD
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.10' }
      - run: pip install -r requirements.txt
      - run: pytest --cov=backend --cov=ml

```

🚀 Deployment
Deployment e Infraestructura
| Servicio | Rol | URL |
|---|---|---|
| Frontend | Vercel (Edge React) | `https://cagemind.app` |
| Backend API | Railway/Render | `https://api.cagemind.app` |
| Base de Datos | SQLite/PostgreSQL | Adjunto al backend |

🐳 Docker Local
```bash
docker-compose up --build    # Build y ejecutar
docker-compose up -d         # Modo detached
docker-compose logs -f       # Ver logs
```

🤝 Contribuciones
¡Las contribuciones son muy apreciadas! Si tienes una sugerencia que haría esto mejor, por favor haz fork del repo y crea un pull request.
Cómo Contribuir
Haz Fork del Proyecto
Crea tu Rama de Feature

```bash
   git checkout -b feature/AmazingFeature
```

Haz Commit de tus Cambios
```bash
    git commit -m 'feat: add AmazingFeature'
```

Haz Push a la Rama

```bash
        git push origin feature/AmazingFeature
```

Abre un Pull Request
📋 Guías
Para mantener la calidad del proyecto, por favor sigue estos estándares:
Python: Sigue las guías de estilo PEP 8.
Commits: Usa Conventional Commits (ej. feat:, fix:, docs:).
Calidad: Siempre actualiza tests y documentación para nuevas features o cambios significativos.

🗺️ Roadmap
| Estado | Feature | Descripción |
| :---: | --- | --- |
| ✅ | Data Pipeline | Scraping desde UFC Stats y Sherdog |
| ✅ | Machine Learning | Modelos XGBoost con calibración |
| ✅ | API Backend | Servicio REST FastAPI + Swagger |
| ✅ | Web Interface | Dashboard con React + TypeScript |
| 🔄 | Live Predictions | Inferencia en tiempo real para eventos próximos |
| 📅 | Mobile App | App complementaria con React Native |
| 📅 | Advanced Metrics | Algoritmo propietario "CageScore" |
