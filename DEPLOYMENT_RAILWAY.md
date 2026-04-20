# 🚀 Deployment en Railway

## Variables de Entorno Requeridas en Railway

Para que tu backend funcione correctamente en Railway, debes configurar las siguientes variables de entorno en el dashboard de Railway:

### 🔑 Variables Obligatorias

```bash
# Database (Supabase PostgreSQL)
# ⚠️ IMPORTANTE: Usa la conexión DIRECTA (puerto 5432), NO el pooler (puerto 6543)
# Obtén tu contraseña de Supabase → Project Settings → Database
DATABASE_URL=postgresql://postgres.[TU-PROJECT-REF]:[TU-CONTRASEÑA]@db.[TU-PROJECT-REF].supabase.co:5432/postgres
DATABASE_URL_NB=postgresql://postgres.[TU-PROJECT-REF]:[TU-CONTRASEÑA]@db.[TU-PROJECT-REF].supabase.co:5432/postgres

# Autenticación JWT
JWT_SECRET=tu-secret-key-muy-seguro-y-largo  # ¡Cambia ESTO en producción!

# Contraseña de Admin
ADMIN_PASSWORD=tu-admin-password-segura

# Supabase (opcional, para algunas funcionalidades)
SUPABASE_URL=https://[TU-PROJECT-REF].supabase.co
SUPABASE_KEY=tu-anon-key-o-service-role-key
```

### 📝 Cómo configurar en Railway

1. Ve a tu proyecto en [Railway](https://railway.app/)
2. Haz clic en tu servicio
3. Ve a la pestaña **"Variables"**
4. Agrega cada variable una por una
5. Haz **Deploy** para aplicar los cambios

---

## 🔍 Verificar que la API está funcionando

### Health Check

Visita: `https://tu-api.up.railway.app/`

Deberías ver:
```json
{
  "name": "UFC Fight Predictor API",
  "version": "1.0.0",
  "status": "online",
  "endpoints": ["/fighters", "/fighters/{name}", "/predict", "/upcoming", "/stats"],
  "docs": "/docs"
}
```

### Documentación Swagger

Visita: `https://tu-api.up.railway.app/docs`

### Probar endpoint de fighters

Visita: `https://tu-api.up.railway.app/fighters?limit=5`

Deberías ver una lista de peleadores si la BD está conectada correctamente.

---

## 🐛 Debug de Problemas Comunes

### Error: "Connection refused" o "SSL required"

**Causa:** La URL de la base de datos no tiene `sslmode=require`

**Solución:** Asegúrate de que `DATABASE_URL` termine con `?sslmode=require`

```
postgresql://usuario:password@host:6543/postgres?sslmode=require
```

### Error: "No module named 'backend.config'"

**Causa:** El Python path no está configurado correctamente

**Solución:** Railway debería detectar automáticamente el `requirements.txt`, pero verifica que:
- El archivo `requirements.txt` está en la raíz del proyecto
- El archivo `nixpacks.toml` o `Procfile` está configurado

### Error: CORS en el frontend

**Síntoma:** El frontend dice "Network Error" o las peticiones fallan

**Solución:** Verifica que en `backend/app.py` los orígenes CORS incluyan tu dominio de Vercel:

```python
ALLOWED_ORIGINS = [
    "https://cagemind.app",
    "https://www.cagemind.app",
    "https://cagemind-*.vercel.app",
    "http://localhost:3000",
    "http://localhost:5173",
]
```

### Error: 404 en /api/fighters desde el frontend

**Causa:** El frontend está apuntando a la URL incorrecta

**Solución:** Verifica `frontend/.env.local`:

```bash
VITE_API_BASE_URL=https://tu-api-real.up.railway.app
```

¡Importante! Después de cambiar `.env.local`, debes **rebuild** del frontend:

```bash
cd frontend
npm run build
```

---

## 📊 Logs en Railway

Para ver los logs y debuggear errores:

1. Ve a tu proyecto en Railway
2. Haz clic en **"Deployments"**
3. Selecciona el deployment más reciente
4. Haz clic en **"View Logs"**

Busca errores como:
- `Error connecting to database`
- `ModuleNotFoundError`
- `Address already in use`

---

## 🔁 Redeploy después de cambios

Railway hace **auto-deploy** cuando haces push a GitHub.

Si necesitas forzar un redeploy:

1. Ve a Railway → Tu proyecto
2. Haz clic en **"Deployments"**
3. Haz clic en **"Redeploy"** en el deployment más reciente

---

## 🧪 Test Local antes de Deploy

Antes de subir a Railway, prueba localmente:

```bash
# Backend
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Frontend (en otra terminal)
cd frontend
npm run dev
```

Visita `http://localhost:8000/docs` para probar la API local.
