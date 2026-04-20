# 🔧 Resumen de Fixes Aplicados - CageMind API

## Problema Reportado
> El frontend en producción se ve pero está vacío, sin información de la base de datos. El auth.user de Supabase funciona directo en el front, pero el backend no está haciendo las consultas correctamente.

---

## 📋 Diagnóstico Realizado

Se identificaron **5 problemas críticos**:

### ❌ 1. CORS mal configurado
- Solo permitía `https://cagemind.app`
- Bloqueaba dominios `www.cagemind.app` y previews de Vercel

### ❌ 2. Conexión PostgreSQL sin SSL correcto
- La URL de Supabase requiere `sslmode=require`
- El código no manejaba SSL explícitamente en `psycopg2.connect()`

### ❌ 3. SQL placeholders incompatibles con PostgreSQL
- Los routers usaban `?` (estilo SQLite)
- PostgreSQL requiere `%s` como placeholder
- Esto causaba errores de sintaxis SQL silenciosos

### ❌ 4. Frontend sin URL de API configurada
- `frontend/.env.local` no tenía `VITE_API_BASE_URL`
- El frontend en producción no sabía dónde conectar

### ❌ 5. Falta documentación de deployment
- No había guía clara de variables de entorno para Railway

---

## ✅ Fixes Aplicados

### 1. CORS Multi-Origen
**Archivo:** `backend/app.py`

```python
ALLOWED_ORIGINS = [
    "https://cagemind.app",
    "https://www.cagemind.app",
    "https://cagemind-*.vercel.app",  # Preview deployments
    "http://localhost:3000",
    "http://localhost:5173",
]
```

### 2. SSL en Conexión PostgreSQL
**Archivo:** `backend/database.py`

```python
def get_db():
    if DATABASE_URL.startswith("postgresql"):
        import psycopg2
        if "sslmode=" not in DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL + "?sslmode=require")
        else:
            conn = psycopg2.connect(DATABASE_URL)
        return conn
    # ... SQLite fallback
```

### 3. SQL Placeholders Correctos
**Archivos modificados:**
- `backend/routers/fighters.py`
- `backend/routers/stats.py`
- `backend/routers/events.py`
- `backend/services/fighters.py`

**Patrón aplicado:**
```python
from db.db_helpers import param

p = param()  # Retorna "%s" para PostgreSQL, "?" para SQLite
conn.execute(f"SELECT * FROM table WHERE col = {p}", (value,))
```

### 4. Frontend API URL Configurada
**Archivos modificados:**
- `frontend/.env.local` - Agregado `VITE_API_BASE_URL`
- `frontend/src/config.ts` - Agregado logging para debug
- `frontend/.env.example` - Documentación actualizada

```bash
# frontend/.env.local
VITE_API_BASE_URL=https://web-production-2bc52.up.railway.app
```

### 5. Documentación de Deployment
**Archivos creados:**
- `DEPLOYMENT_RAILWAY.md` - Guía completa de deployment
- `scripts/test_db_connection.py` - Script de test de conexión

---

## 🚀 Pasos para Desplegar los Fixes

### Paso 1: Push a GitHub
```bash
cd C:\Users\PC PRIDE WHITE WOLF\proyectos\ufc-fight-predictor
git add .
git commit -m "fix: corrección de conexión PostgreSQL y CORS"
git push origin main
```

### Paso 2: Verificar Variables en Railway
En el dashboard de Railway, asegura que estas variables existan:

```bash
# Usa la conexión DIRECTA (puerto 5432), NO el pooler (puerto 6543)
DATABASE_URL=postgresql://postgres.[TU-PROJECT-REF]:[TU-CONTRASEÑA]@db.[TU-PROJECT-REF].supabase.co:5432/postgres
DATABASE_URL_NB=postgresql://postgres.[TU-PROJECT-REF]:[TU-CONTRASEÑA]@db.[TU-PROJECT-REF].supabase.co:5432/postgres
JWT_SECRET=tu-secret-key-seguro
ADMIN_PASSWORD=tu-admin-password
SUPABASE_URL=https://[TU-PROJECT-REF].supabase.co
SUPABASE_KEY=tu-anon-key
```

### Paso 3: Rebuild del Frontend en Vercel
En Vercel, ve a tu proyecto y haz **Redeploy** para que tome el nuevo `.env.local`.

O ejecuta localmente:
```bash
cd frontend
npm run build
git add .
git commit -m "build: rebuild frontend con API_URL configurada"
git push origin main
```

### Paso 4: Verificar Logs
**En Railway:**
1. Ve a tu proyecto
2. Click en "Deployments" → deployment más reciente
3. "View Logs"

Busca:
- `Cargando cache de peleadores...` ✅
- `API lista!` ✅
- Sin errores de conexión a BD

**En Vercel (frontend):**
1. Ve a tu proyecto
2. Click en el deployment
3. "View Build Logs"

---

## 🧪 Tests de Verificación

### Test 1: Health Check de la API
```bash
curl https://tu-api.up.railway.app/
```

Esperado:
```json
{
  "name": "UFC Fight Predictor API",
  "version": "1.0.0",
  "status": "online"
}
```

### Test 2: Endpoint de Fighters
```bash
curl https://tu-api.up.railway.app/fighters?limit=5
```

Esperado: Lista de peleadores con datos

### Test 3: Endpoint de Stats
```bash
curl https://tu-api.up.railway.app/stats
```

Esperado:
```json
{
  "database": {
    "fighters": 500,
    "events": 100,
    "fights": 2000,
    "fight_stats": 15000
  },
  ...
}
```

### Test 4: Script de Test Local
```bash
# Desde la raíz del proyecto
python scripts/test_db_connection.py
```

---

## 🔍 Debug Continuo

### Si el frontend sigue vacío:

1. **Abre DevTools del navegador** (F12)
2. **Ve a la pestaña "Console"**
3. Busca errores como:
   - `Access to fetch blocked by CORS policy` → Fix 1 no aplicado
   - `Failed to fetch` → URL de API incorrecta
   - `404 Not Found` → Endpoint no existe o mal construido

4. **Ve a la pestaña "Network"**
5. Recarga la página
6. Busca requests a `/api/fighters` o `/api/stats`
7. Inspecciona:
   - **Status Code**: ¿200, 404, 500?
   - **Response**: ¿Qué devuelve el backend?
   - **Request URL**: ¿Es la correcta?

### Si la API falla en Railway:

1. **Revisa los logs en Railway**
2. **Ejecuta el script de test:**
   ```bash
   # SSH a Railway o localmente con las mismas vars
   python scripts/test_db_connection.py
   ```

3. **Verifica que el modelo ML existe:**
   ```bash
   ls ml/models/ufc_predictor_models.pkl
   ```

---

## 📁 Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `backend/app.py` | CORS multi-origen |
| `backend/database.py` | SSL en conexión PostgreSQL |
| `backend/routers/fighters.py` | SQL placeholders correctos |
| `backend/routers/stats.py` | SQL placeholders correctos |
| `backend/routers/events.py` | SQL placeholders correctos |
| `backend/services/fighters.py` | SQL placeholders correctos |
| `frontend/.env.local` | Agregado VITE_API_BASE_URL |
| `frontend/src/config.ts` | Logging para debug |
| `frontend/.env.example` | Documentación actualizada |

## 📄 Archivos Creados

| Archivo | Propósito |
|---------|-----------|
| `DEPLOYMENT_RAILWAY.md` | Guía de deployment en Railway |
| `scripts/test_db_connection.py` | Test de conexión a BD |
| `FIXES_RESUMEN.md` | Este archivo |

---

## ⚠️ Importante: Seguridad

### Credenciales Expuestas
Tu archivo `.env` actual tiene credenciales reales de Supabase. **NUNCA** hagas commit de este archivo a GitHub.

```bash
# Verifica que .env esté en .gitignore
cat .gitignore | grep "\.env"
```

### JWT Secret
El `JWT_SECRET` actual es un placeholder. Cambialo en Railway por uno único:

```bash
# Genera uno nuevo
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 📞 Soporte

Si después de aplicar todos los fixes el problema persiste:

1. **Comparte los errores de consola del navegador** (F12 → Console)
2. **Comparte los logs de Railway** (Deployments → View Logs)
3. **Ejecuta el script de test** y comparte el output
