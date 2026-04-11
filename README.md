# 🥊 CageMind — MMA Fight Intelligence

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Deploy](https://img.shields.io/badge/Deploy-Production-0B0D0E?logo=vercel)](https://cagemind.app)

> **UFC Fight Prediction System powered by Machine Learning**  
> CageMind combines web scraping, data analysis, and predictive modeling to deliver statistical insights and win probability forecasts for MMA fights.

🌐 **Live Demo**: [cagemind.app](https://cagemind.app)  
📊 **Data Source**: UFC Stats • Sherdog • Official UFC Records

## ✨ Key Features

### 🔮 Smart Fight Predictions
- **ML-Powered Forecasts**: XGBoost models with Platt scaling for calibrated win probabilities
- **Confidence Metrics**: Each prediction includes reliability scores and key influencing factors
- **Head-to-Head Analysis**: Compare fighter stats, styles, and historical performance side-by-side

### 📊 Advanced Analytics
- **Fighter Profiles**: Detailed breakdowns of striking, grappling, and cardio metrics
- **Trend Detection**: Identify performance patterns across weight classes and eras
- **Event Insights**: Pre-fight statistics and post-event analysis for every UFC card

### 🔄 Automated Data Pipeline
- **Multi-Source Scraping**: Collects data from UFCStats.com, Sherdog, and official records
- **Checkpoint System**: Resume interrupted scrapes without data loss or duplicates
- **Rate Limiting & Logging**: Respectful crawling with full execution transparency

### 🗄️ Structured Data Layer
- **SQLite Database**: Optimized schema for fast queries on fighter histories and fight outcomes
- **Normalized Stats**: Round-by-round data cleaned and ready for analysis or ML training
- **Export Options**: Download processed datasets in CSV format for external use

### 🌐 Developer-Ready API
- **RESTful Endpoints**: Query fighters, events, and predictions via JSON API
- **Swagger Documentation**: Interactive API docs at `/docs` for easy integration
- **Authentication Ready**: JWT support for protected routes (configurable)

### 🎨 Modern Frontend Experience
- **React + TypeScript**: Type-safe, responsive UI built with Vite
- **Interactive Visualizations**: Charts and comparisons powered by Recharts/D3
- **Dark Mode Support**: User-preference aware design for comfortable viewing


## 🗂️ Project Structure

<details>
<summary><b>📁 Ver estructura completa del proyecto</b></summary>
cagemind/
├── 📁 config/ # Configuration & environment variables
├── data/
│ ├── 📁 scrapers/ # UFC Stats & Sherdog scrapers
│ ├── 📁 raw/ # Raw HTML/JSON downloads
│ ├── 📁 processed/ # Cleaned datasets
│ └── 📁 exports/ # CSV exports
├── 📁 db/ # SQLite schema & utilities
├── 📁 ml/ # Models, training & predictions
├── 📁 backend/ # FastAPI application
│ ├── 📁 api/ # Routes & endpoints
│ ├── 📁 core/ # Config & security
│ └── 📁 schemas/ # Pydantic models
├── frontend/ # React + TypeScript app
│ ├── 📁 src/
│ │ ├── 📁 components/
│ │ ├── 📁 pages/
│ │ ├── 📁 services/
│ │ └── utils/
│ └── 📁 public/
├── 📁 notebooks/ # Jupyter notebooks (EDA)
├── tests/ # Unit & integration tests
├── 📁 docs/ # Documentation
├── requirements.txt
├── 📄 package.json
├── run_phase1.py
── 📄 README.md
</details>

## 🛠️ Technology Stack

### 🔙 Backend & Data Engineering
| Technology | Purpose | Version |
|------------|---------|---------|
| **Python** | Core language for scraping, ML, and API | 3.10+ |
| **FastAPI** | High-performance REST API framework | 0.104+ |
| **SQLite** | Lightweight, file-based relational database | 3.x |
| **Pandas** | Data manipulation and analysis | 2.x |
| **NumPy** | Numerical computing and array operations | 1.24+ |
| **Scikit-learn** | ML utilities, preprocessing, model evaluation | 1.3+ |
| **XGBoost** | Gradient boosting for fight prediction models | 1.7+ |
| **Requests + BeautifulSoup4** | HTTP client and HTML parsing for scraping | latest |
| **lxml** | Fast XML/HTML parser for complex scraping tasks | 4.9+ |

### 🎨 Frontend
| Technology | Purpose | Version |
|------------|---------|---------|
| **React** | Component-based UI library | 18.x |
| **TypeScript** | Type-safe JavaScript development | 5.x |
| **Vite** | Fast build tool and dev server | 4.x |
| **Recharts** | Declarative charting library for data viz | 2.x |
| **Tailwind CSS** *(optional)* | Utility-first CSS framework | 3.x |

### 🚀 DevOps & Infrastructure
| Tool | Purpose |
|------|---------|
| **Vercel** | Frontend deployment with CDN and edge functions |
| **Railway / Render** | Backend API hosting with auto-deploy from GitHub |
| **GitHub Actions** | CI/CD pipelines, automated testing, and scheduled scrapes |
| **pre-commit** | Code quality hooks (linting, formatting) |

### 🧪 Testing & Quality
| Tool | Purpose |
|------|---------|
| **pytest** | Unit and integration testing for Python code |
| **Jest + React Testing Library** | Frontend component testing |
| **Black + isort** | Code formatting and import sorting |
| **Flake8 / Ruff** | Linting for PEP8 compliance |


## ⚡ Quick Start

Get the project running locally in 3 steps.

###  Prerequisites
Ensure you have the following installed:
- **Python 3.10+** (for Backend & ML)
- **Node.js 18+** (for Frontend)
- **Git**

---

### 🛠️ 1. Installation

#### Backend (Python)
```bash
# Clone the repository
git clone https://github.com/danielreidxd/cagemind.git
cd cagemind

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

cd frontend

# Install dependencies
npm install

# Database configuration
DATABASE_URL=sqlite:///./cagemind.db

# API Settings
API_KEY=your_secret_api_key
ENV=development

# Run the complete scraper pipeline (Phase 1)
python run_phase1.py

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

cd frontend
npm run dev
```

## 📊 Database Schema & Data Flow

### 🗄️ Schema Overview
CageMind uses a relational SQLite database optimized for fast lookups, statistical queries, and ML feature extraction.

| Table | Description | Key Fields |
|-------|-------------|------------|
| `fighters` | Fighter profiles & physical attributes | `id`, `name`, `nickname`, `height`, `weight`, `reach`, `stance`, `record` |
| `events` | UFC event metadata | `id`, `name`, `date`, `location`, `venue` |
| `fights` | Matchup results & metadata | `id`, `event_id`, `fighter_a_id`, `fighter_b_id`, `winner_id`, `method`, `round`, `time` |
| `fight_stats` | Round-by-round performance data | `fight_id`, `fighter_id`, `sig_strikes`, `takedowns`, `submissions`, `control_time`, `knockdowns` |
| `predictions` | Historical & live ML forecasts | `id`, `fight_id`, `fighter_a_prob`, `fighter_b_prob`, `model_version`, `confidence` |

🔗 **Relationships**: `events` → `fights` → `fighters` → `fight_stats`

> 📖 Full schema definition: [`db/schema.sql`](db/schema.sql)

### 🔄 Data Flow Pipeline

## 🔮 ML Predictions & API Usage

CageMind exposes its prediction engine via a clean REST API. Whether you're building a dashboard, a mobile app, or just experimenting with fight data, integration takes minutes.

### 🌐 Core Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/fighters` | Search & filter fighter profiles |
| `GET` | `/api/fights/{id}` | Retrieve fight details, stats & history |
| `POST` | `/api/predict` | Get ML-powered win probabilities |
| `GET` | `/api/events` | Browse past & upcoming UFC cards |
| `GET` | `/api/stats/trends` | Aggregate performance trends by weight class |

📖 Interactive Swagger UI: `https://cagemind.app/api/docs`

### 💻 Python Quick Example
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
print(f"Model confidence: {result['predictions']['fighter_a']['confidence'].upper()}")

curl -X POST "https://cagemind.app/api/predict" \
     -H "Content-Type: application/json" \
     -d '{
       "fighter_a": "Islam Makhachev",
       "fighter_b": "Charles Oliveira",
       "weight_class": "Lightweight"
     }'

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

## 🧪 Testing, CI/CD & Deployment

### ✅ Testing Strategy
CageMind includes comprehensive testing to ensure data integrity, model reliability, and API stability.

| Component | Command | Coverage Focus |
|-----------|---------|----------------|
| **Backend Unit Tests** | `pytest backend/tests/ -v` | API routes, DB queries, validation |
| **ML Pipeline Tests** | `pytest ml/tests/ -v` | Feature extraction, prediction consistency |
| **Frontend Tests** | `cd frontend && npm test` | Component rendering, API mocking, routing |
| **Integration Tests** | `pytest tests/integration/ -v` | Full flow: scrape → store → predict → serve |

📊 Generate coverage report:  
```bash
pytest --cov=backend --cov=ml --cov-report=html

# .github/workflows/ci.yml (simplified)
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

      # Build & run entire stack
docker-compose up --build

# Run in detached mode
docker-compose up -d

# View live logs
docker-compose logs -f api frontend
```

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

### How to Contribute
1. **Fork** the Project
2. **Create your Feature Branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit your Changes** (`git commit -m 'feat: add AmazingFeature'`)
4. **Push to the Branch** (`git push origin feature/AmazingFeature`)
5. **Open a Pull Request**

### Development Guidelines
- Follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for Python.
- Use [Conventional Commits](https://www.conventionalcommits.org/) for clear commit history.
- Update tests and documentation for any new feature or bug fix.

---

## 🗺️ Roadmap

Current project status and future goals:

| Status | Feature | Description |
|:------:|---------|-------------|
| ✅ | **Data Pipeline** | Scraping from UFC Stats & Sherdog with error handling |
| ✅ | **Machine Learning** | XGBoost models with calibration and feature importance |
| ✅ | **API Backend** | FastAPI REST service with Swagger documentation |
| ✅ | **Web Interface** | React + TypeScript dashboard with visualizations |
| 🔄 | **Live Predictions** | Real-time inference for upcoming UFC events |
| 📅 | **Mobile App** | React Native companion app for on-the-go stats |
| 📅 | **Advanced Metrics** | Proprietary "CageScore" ranking algorithm |

---

## 👨‍💻 Author

**Daniel Reid**
- GitHub: [@danielreidxd](https://github.com/danielreidxd)
- LinkedIn: [danielreid](https://www.linkedin.com/in/juan-daniel-galvan-moctezuma-0b1b1428a/) 

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.

---

> ⚠️ **Disclaimer**: This project is for educational and entertainment purposes only. The predictions provided by CageMind are based on historical data and statistical models; they do not guarantee future results. Do not use this software for gambling or financial decisions.


# 🥊 CageMind — Inteligencia para Peleas de MMA

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react)](https://react.dev)
[![License](https://img.shields.io/badge/Licencia-MIT-green.svg)](LICENSE)
[![Deploy](https://img.shields.io/badge/Deploy-Producción-0B0D0E?logo=vercel)](https://cagemind.app)

> **Sistema de predicción de peleas UFC impulsado por Machine Learning**  
> CageMind combina web scraping, análisis de datos y modelado predictivo para ofrecer insights estadísticos y pronósticos de probabilidad de victoria en combates de MMA.

🌐 **Demo en vivo**: [cagemind.app](https://cagemind.app)  
📊 **Fuentes de datos**: UFC Stats • Sherdog • Registros oficiales de la UFC

## ✨ Características Principales

### 🔮 Predicciones Inteligentes de Peleas
- **Predicción mediante Machine Learning**: Modelos basados en XGBoost con calibración de Platt para estimar probabilidades de victoria reales y fiables.
- **Métricas de Confianza**: Cada predicción incluye un índice de fiabilidad y destaca los factores clave que influyen en el resultado.
- **Comparativa Cara a Cara**: Análisis detallado que contrasta estadísticas de golpeo, grappling y cardio entre ambos oponentes.

### 📊 Analítica Avanzada
- **Perfiles de Luchadores**: Desglose exhaustivo de métricas físicas y de rendimiento (alcance, alcance efectivo, defensa de derribos, etc.).
- **Detección de Tendencias**: Identificación de patrones de rendimiento a lo largo del tiempo y por categorías de peso.
- **Insights de Eventos**: Resumen pre-combate y análisis post-evento para cada tarjeta de la UFC.

### 🔄 Pipeline de Datos Automatizado
- **Recolección Multi-Fuente**: Obtención automática de datos desde UFCStats.com, Sherdog y registros oficiales.
- **Sistema de Checkpoints**: Capacidad de reanudar el proceso de recolección si se interrumpe, evitando duplicados y pérdidas.
- **Rate Limiting y Logs**: Rastreo responsable de los sitios fuente con registros completos de ejecución para auditoría.

### 🗄️ Capa de Datos Estructurada
- **Base de Datos SQLite**: Esquema optimizado para consultas rápidas sobre historiales de luchadores y resultados de combates.
- **Estadísticas Normalizadas**: Datos limpios y estandarizados (golpes significativos, tiempos de control, sumisiones) listos para análisis.
- **Exportación**: Opciones para descargar conjuntos de datos procesados en formato CSV.

### 🌐 API RESTful para Desarrolladores
- **Endpoints JSON**: Consulta luchadores, eventos y predicciones directamente vía HTTP.
- **Documentación Interactiva**: Explora la API fácilmente usando Swagger UI (disponible en `/docs`).
- **Seguridad**: Soporte para autenticación JWT y validación de datos de entrada para proteger el servicio.

### 🎨 Interfaz de Usuario Moderna
- **React + TypeScript**: Interfaz rápida, responsiva y con seguridad de tipos en el desarrollo.
- **Visualizaciones Interactivas**: Gráficos dinámicos para comparar el rendimiento de los atletas de forma visual.
- **Modo Oscuro**: Diseño que respeta las preferencias del sistema del usuario para una visualización cómoda.

## ⚡ Inicio Rápido

Pon el proyecto en marcha en tu entorno local en 3 pasos.

### 🔧 Prerrequisitos
Asegúrate de tener instalados:
- **Python 3.10+** (para Backend y ML)
- **Node.js 18+** (para Frontend)
- **Git**

---

### 🛠️ 1. Instalación

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

cd frontend

# Instalar dependencias
npm install

# Configuración de base de datos
DATABASE_URL=sqlite:///./cagemind.db

# Configuración de API
API_KEY=tu_clave_secreta
ENV=development

# Ejecutar el pipeline completo de scraping (Fase 1)
python run_phase1.py

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

cd frontend
npm run dev
```
## 📊 Esquema de Base de Datos y Flujo de Datos

### 🗄️ Visión General del Esquema
CageMind utiliza una base de datos relacional SQLite optimizada para consultas rápidas, análisis estadísticos y extracción de características para ML.

| Tabla | Descripción | Campos Clave |
|-------|-------------|--------------|
| `fighters` | Perfiles y atributos físicos de luchadores | `id`, `name`, `nickname`, `height`, `weight`, `reach`, `stance`, `record` |
| `events` | Metadatos de eventos de la UFC | `id`, `name`, `date`, `location`, `venue` |
| `fights` | Resultados y metadatos de combates | `id`, `event_id`, `fighter_a_id`, `fighter_b_id`, `winner_id`, `method`, `round`, `time` |
| `fight_stats` | Datos de rendimiento round por round | `fight_id`, `fighter_id`, `sig_strikes`, `takedowns`, `submissions`, `control_time`, `knockdowns` |
| `predictions` | Pronósticos históricos y en vivo del ML | `id`, `fight_id`, `fighter_a_prob`, `fighter_b_prob`, `model_version`, `confidence` |

🔗 **Relaciones**: `events` → `fights` → `fighters` → `fight_stats`

> 📖 Definición completa del esquema: [`db/schema.sql`](db/schema.sql)

### 🔄 Flujo del Pipeline de Datos

## 🔮 Predicciones ML y Uso de la API

CageMind expone su motor de predicción mediante una API REST limpia y documentada. Ya sea que estés construyendo un dashboard, una app móvil o simplemente experimentando con datos de peleas, la integración toma minutos.

### 🌐 Endpoints Principales
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/fighters` | Buscar y filtrar perfiles de luchadores |
| `GET` | `/api/fights/{id}` | Obtener detalles, estadísticas e historial de un combate |
| `POST` | `/api/predict` | Obtener probabilidades de victoria impulsadas por ML |
| `GET` | `/api/events` | Explorar tarjetas de la UFC pasadas y próximas |
| `GET` | `/api/stats/trends` | Tendencias agregadas de rendimiento por categoría de peso |

📖 Documentación interactiva Swagger: `https://cagemind.app/api/docs`

### 💻 Ejemplo Rápido en Python
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
print(f"Prob. victoria Pereira: {result['predictions']['fighter_a']['win_probability']:.1%}")
print(f"Confianza del modelo: {result['predictions']['fighter_a']['confidence'].upper()}")

curl -X POST "https://cagemind.app/api/predict" \
     -H "Content-Type: application/json" \
     -d '{
       "fighter_a": "Islam Makhachev",
       "fighter_b": "Charles Oliveira",
       "weight_class": "Lightweight"
     }'

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

## 🧪 Pruebas, CI/CD y Despliegue

### ✅ Estrategia de Pruebas
CageMind incluye un conjunto de pruebas automatizadas para garantizar la integridad de los datos, la fiabilidad del modelo y la estabilidad de la API.

| Componente | Comando | Enfoque de Cobertura |
|------------|---------|----------------------|
| **Pruebas Unitarias (Backend)** | `pytest backend/tests/ -v` | Rutas API, consultas DB, validación de esquemas |
| **Pruebas del Pipeline ML** | `pytest ml/tests/ -v` | Extracción de features, consistencia de inferencia |
| **Pruebas Frontend** | `cd frontend && npm test` | Renderizado de componentes, mocking de API, navegación |
| **Pruebas de Integración** | `pytest tests/integration/ -v` | Flujo completo: scrape → almacenar → predecir → servir |

📊 Generar reporte de cobertura:  
```bash
pytest --cov=backend --cov=ml --cov-report=html

# .github/workflows/ci.yml (simplificado)
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

# Construir y levantar todo el stack
docker-compose up --build

# Ejecutar en modo detached
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f api frontend

```

## 🤝 Cómo Contribuir

Las contribuciones son lo que hacen de la comunidad open-source un lugar increíble para aprender, inspirar y crear. ¡Cualquier aporte que hagas es **muy apreciado**!

### Pasos para Contribuir
1. **Haz un Fork** del Proyecto
2. **Crea tu Rama de Feature** (`git checkout -b feature/AmazingFeature`)
3. **Commit tus Cambios** (`git commit -m 'feat: add AmazingFeature'`)
4. **Push a la Rama** (`git push origin feature/AmazingFeature`)
5. **Abre un Pull Request**

### Guías de Desarrollo
- Sigue la guía de estilo [PEP 8](https://www.python.org/dev/peps/pep-0008/) para Python.
- Usa [Conventional Commits](https://www.conventionalcommits.org/) para un historial de commits claro.
- Actualiza pruebas y documentación para cualquier nueva funcionalidad o corrección de bugs.

---

## 🗺️ Roadmap

Estado actual del proyecto y metas futuras:

| Estado | Funcionalidad | Descripción |
|:------:|--------------|-------------|
| ✅ | **Pipeline de Datos** | Scraping desde UFC Stats y Sherdog con manejo de errores |
| ✅ | **Machine Learning** | Modelos XGBoost con calibración e importancia de features |
| ✅ | **API Backend** | Servicio REST FastAPI con documentación Swagger |
| ✅ | **Interfaz Web** | Dashboard en React + TypeScript con visualizaciones |
| 🔄 | **Predicciones en Vivo** | Inferencia en tiempo real para eventos próximos de la UFC |
| 📅 | **App Móvil** | App complementaria en React Native para stats en movimiento |
| 📅 | **Métricas Avanzadas** | Algoritmo propietario de ranking "CageScore" |

---

## 👨‍💻 Autor

**Daniel Reid**
- GitHub: [@danielreidxd](https://github.com/danielreidxd)
- LinkedIn: [danielreid](https://www.linkedin.com/in/juan-daniel-galvan-moctezuma-0b1b1428a/)

---

## 📄 Licencia

Distribuido bajo la Licencia MIT. Consulta [`LICENSE`](LICENSE) para más información.

---

> ⚠️ **Descargo de responsabilidad**: Este proyecto es únicamente con fines educativos y de entretenimiento. Las predicciones proporcionadas por CageMind se basan en datos históricos y modelos estadísticos; no garantizan resultados futuros. No utilices este software para apuestas o decisiones financieras.

<p align="right">(<a href="#readme-top">volver arriba</a>)</p>

<p align="right">(<a href="#readme-top">back to top</a>)</p>
