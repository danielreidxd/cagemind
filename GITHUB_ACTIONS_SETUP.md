# 🔧 Configuración de GitHub Actions para Scraping

## 📋 Resumen

Se crearon 2 workflows automáticos:

| Workflow | Frecuencia | Propósito |
|----------|------------|-----------|
| `scraping-weekly.yml` | Domingos 6 AM UTC | Actualización automática semanal |
| `scraping-manual.yml` | Manual (on-demand) | Scraping extraordinario |

---

## 🔑 Secrets Requeridos en GitHub

### Paso 1: Ir a Settings del Repositorio

1. Ve a: `https://github.com/danielreidxd/cagemind/settings/secrets/actions`
2. Haz clic en **"New repository secret"**

### Paso 2: Agregar Secrets

Agrega los siguientes secrets:

| Nombre | Valor | Requerido |
|--------|-------|-----------|
| `DATABASE_URL` | `postgresql://postgres.[REF]:[PASS]@db.[REF].supabase.co:5432/postgres` | ✅ Sí |
| `DATABASE_URL_NB` | `postgresql://postgres.[REF]:[PASS]@db.[REF].supabase.co:5432/postgres` | ✅ Sí |
| `SUPABASE_URL` | `https://[REF].supabase.co` | ✅ Sí |
| `SUPABASE_KEY` | Tu service role key de Supabase | ✅ Sí |
| `RAILWAY_API_TOKEN` | Tu token de Railway API | ❌ Opcional |
| `RAILWAY_SERVICE_ID` | ID de tu servicio en Railway | ❌ Opcional |

### ¿Cómo obtener cada valor?

#### DATABASE_URL (Supabase)
1. Ve a Supabase Dashboard
2. Project Settings → Database
3. Connection string → **Direct connection** (puerto 5432)
4. Reemplaza `[YOUR-PASSWORD]` con tu contraseña

#### SUPABASE_URL y SUPABASE_KEY
1. Supabase Dashboard → Project Settings → API
2. **Project URL** → `SUPABASE_URL`
3. **service_role secret** → `SUPABASE_KEY`

#### RAILWAY_API_TOKEN (Opcional, para redeploy automático)
1. Ve a [Railway](https://railway.app/)
2. Account Settings → Tokens
3. Genera un nuevo token

#### RAILWAY_SERVICE_ID (Opcional)
1. Railway Dashboard → Tu proyecto
2. Settings → Service ID
3. Copia el ID (es un UUID)

---

## 🖐️ Cómo Usar el Scraping Manual

### Desde GitHub UI:

1. Ve a: `https://github.com/danielreidxd/cagemind/actions`
2. Selecciona el workflow **"🖐️ Scraping Manual"**
3. Haz clic en **"Run workflow"**
4. Configura:
   - **Tipo**: `completo`, `solo-eventos`, o `solo-upcoming`
   - **Redeploy**: `true` o `false`
5. Haz clic en **"Run workflow"**

### Resultado:
- El workflow se ejecutará
- Verás los logs en tiempo real
- Al finalizar, los datos se committean automáticamente
- Si activaste redeploy, Railway se actualizará

---

## 📅 Horarios del Scraping Automático

**Todos los domingos:**
- **6:00 AM UTC** (domingo)
- **2:00 AM EST** (domingo)
- **1:00 AM CST** (domingo)
- **12:00 AM PST** (domingo)

Esto asegura que los datos estén actualizados para el lunes.

---

## 🔍 Ver Logs de Ejecución

1. Ve a: `https://github.com/danielreidxd/cagemind/actions`
2. Haz clic en el workflow que quieras ver
3. Selecciona la ejecución específica
4. Verás los logs paso a paso

---

## 🛠️ Solución de Problemas

### El workflow falla en "Checkout"
- Verifica que el repo no sea privado (o usa un PAT)

### El scraping falla con error de BD
- Verifica que `DATABASE_URL` sea correcta
- Asegúrate de que Supabase permita conexiones desde GitHub Actions
  - Supabase → Project Settings → Database → Network
  - Agrega `0.0.0.0/0` temporalmente si es necesario

### El redeploy en Railway falla
- Verifica que `RAILWAY_API_TOKEN` sea válido
- Verifica que `RAILWAY_SERVICE_ID` sea correcto
- Railway API puede tener rate limiting

### Los datos no se actualizan
- Revisa los logs del workflow
- Verifica que los scripts de scraping existan en:
  - `scripts/scraping/scrape_events.py`
  - `scripts/scraping/scrape_upcoming.py`

---

## 📝 Modificar la Frecuencia

Para cambiar el día/hora del scraping automático, edita `.github/workflows/scraping-weekly.yml`:

```yaml
schedule:
  # Cambia esto:
  - cron: '0 6 * * 0'  # Domingos 6 AM UTC
  
  # Usa cron syntax: https://crontab.guru/
  # Ej: Todos los días a las 6 AM:
  # - cron: '0 6 * * *'
```

---

## ✅ Checklist de Configuración

- [ ] Ir a GitHub Repo → Settings → Secrets and variables → Actions
- [ ] Agregar `DATABASE_URL`
- [ ] Agregar `DATABASE_URL_NB`
- [ ] Agregar `SUPABASE_URL`
- [ ] Agregar `SUPABASE_KEY`
- [ ] (Opcional) Agregar `RAILWAY_API_TOKEN`
- [ ] (Opcional) Agregar `RAILWAY_SERVICE_ID`
- [ ] Probar workflow manual: Actions → 🖐️ Scraping Manual → Run workflow
- [ ] Verificar que los datos se actualicen en la BD
- [ ] (Opcional) Verificar que Railway haga redeploy

---

## 🎯 Flujo Recomendado

1. **Configura todos los secrets** en GitHub
2. **Prueba el workflow manual** primero (tipo: `completo`, redeploy: `false`)
3. **Verifica** que los datos se actualicen en Supabase
4. **Activa el redeploy** si todo funcionó
5. **Espera al domingo** para ver el automático en acción

---

## 📞 Soporte

Si algo falla:
1. Revisa los logs en GitHub Actions
2. Busca el error específico
3. Verifica que los scripts funcionen localmente
4. Asegúrate de que Supabase tenga datos para scrapear
