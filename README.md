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
