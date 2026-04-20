"""
Endpoints:
  GET  /                        → Health check
  GET  /fighters                → Lista de peleadores (con búsqueda)
  GET  /fighters/{name}         → Perfil detallado de un peleador
  POST /predict                 → Predicción de pelea (Sandbox)
  GET  /events                  → Eventos históricos paginados
  GET  /upcoming                → Peleas próximas con predicciones
  GET  /stats                   → Estadísticas generales de la BD
  POST /auth/login              → Autenticación JWT
  POST /auth/register           → Registro público
  GET  /auth/me                 → Info usuario autenticado
  GET  /admin/dashboard         → Panel administrador
  POST /admin/update            → Trigger scraper
  GET  /admin/update-logs       → Historial actualizaciones
  GET  /admin/analytics         → Métricas de uso
  POST /analytics/track         → Tracking público
  POST /picks                   → Votación de usuarios
  GET  /picks/{event}           → Picks del usuario
  GET  /leaderboard             → Tabla de posiciones
  GET  /odds                    → Odds de casas de apuestas
  GET  /value-bets              → Value bets calculados

"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auth import init_users_table
from backend.database import load_models, load_fighter_cache, load_fighter_stats_cache
from backend.routers import fighters, predictions, events, stats, auth, admin, analytics, picks, odds

# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="UFC Fight Predictor API",
    description="API de predicción de peleas UFC basada en Machine Learning",
    version="1.0.0",
)

# CORS — permitir requests del frontend (producción + preview + local)
ALLOWED_ORIGINS = [
    "https://cagemind.app",
    "https://www.cagemind.app",
    "https://cagemind-*.vercel.app",  # Preview deployments
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTERS
# ============================================================

app.include_router(fighters.router)
app.include_router(predictions.router)
app.include_router(events.router)
app.include_router(stats.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(analytics.router)
app.include_router(picks.router)
app.include_router(odds.router)


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup():
    """Pre-carga modelos y datos al iniciar."""
    print("Inicializando tabla users...")
    init_users_table()
    print("Cargando modelos...")
    load_models()
    print("Cargando cache de peleadores...")
    load_fighter_cache()
    load_fighter_stats_cache()
    print("API lista!")


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
async def root():
    return {
        "name": "UFC Fight Predictor API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": ["/fighters", "/fighters/{name}", "/predict", "/upcoming", "/stats"],
        "docs": "/docs"
    }