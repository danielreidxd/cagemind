# 📚 Guía de Migración a PostgreSQL/Supabase

Esta guía documenta el proceso completo de migración de SQLite a PostgreSQL con Supabase para el UFC Fight Predictor.

---

## 📋 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Prerrequisitos](#prerrequisitos)
3. [Proceso de Migración](#proceso-de-migración)
4. [Archivos Creados/Modificados](#archivos-creadosmodificados)
5. [Solución de Problemas](#solución-de-problemas)
6. [Referencias](#referencias)

---

## 🎯 Resumen Ejecutivo

### ¿Qué se migró?

**Tablas principales (6) - Ya existían en Supabase:**
- ✅ `organizations` - Organizaciones de MMA
- ✅ `fighters` - Perfiles de luchadores
- ✅ `events` - Eventos UFC
- ✅ `fights` - Resultados de peleas
- ✅ `fight_stats` - Estadísticas por round
- ✅ `data_quality` - Metadatos de calidad

**Tablas adicionales (5) - Nuevas en Supabase:**
- ✅ `users` - Autenticación de usuarios
- ✅ `analytics_events` - Tracking de eventos
- ✅ `update_logs` - Logs de actualizaciones
- ✅ `picks` - Votaciones de usuarios
- ✅ `sherdog_features` - Datos pre-UFC

### Cambios en el Código

**Archivos modificados para compatibilidad PostgreSQL:**
- `backend/services/predictions.py` - Placeholders dinámicos
- `backend/routers/analytics.py` - Funciones de fecha
- `backend/routers/admin.py` - `last_insert_rowid()` → `LASTVAL()`
- `db/connection.py` - Mejora en creación de admin
- `scripts/scraping/update_data.py` - Ya era compatible

**Nuevos archivos:**
- `db/schema_postgresql.sql` - Schema completo PostgreSQL
- `scripts/migrate_all_to_supabase.py` - Migración completa
- `scripts/migrate_remaining_tables_to_supabase.py` - Migración parcial
- `.env.example` - Plantilla de configuración

---

## 🔧 Prerrequisitos

### 1. Tener una cuenta de Supabase

1. Ve a [supabase.com](https://supabase.com)
2. Crea una cuenta gratuita
3. Crea un nuevo proyecto
4. Guarda las credenciales:
   - Project URL: `https://xxxxx.supabase.co`
   - API Key: `eyJhbG...`

### 2. Instalar dependencias

```bash
pip install psycopg2-binary python-dotenv
```

### 3. Configurar variables de entorno

Copia `.env.example` a `.env` y completa:

```bash
# .env
DATABASE_URL=postgresql://postgres:tu_password@host.supabase.com:6543/postgres?sslmode=require
SUPABASE_URL=https://tu_proyecto.supabase.co
SUPABASE_KEY=tu_key
JWT_SECRET=tu_secreto_seguro
ADMIN_PASSWORD=tu_password_admin
```

---

## 🚀 Proceso de Migración

### Paso 1: Ejecutar Schema PostgreSQL

El schema ya está creado en `db/schema_postgresql.sql`. Supabase crea las tablas automáticamente, pero puedes verificarlo:

```sql
-- En el SQL Editor de Supabase
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
```

Deberías ver las 11 tablas.

### Paso 2: Migrar Datos

#### Opción A: Migración Completa (Recomendada)

Migra TODAS las tablas desde SQLite local:

```bash
python scripts/migrate_all_to_supabase.py
```

**¿Qué hace este script?**
- Lee todas las tablas de SQLite
- Inserta/actualiza en PostgreSQL con `ON CONFLICT`
- Resetea secuencias (SERIAL)
- Verifica la migración

#### Opción B: Migración Parcial

Si solo faltan las tablas adicionales:

```bash
python scripts/migrate_remaining_tables_to_supabase.py
```

**Tablas que migra:**
- `users`
- `analytics_events`
- `update_logs`
- `picks`
- `sherdog_features`

### Paso 3: Verificar Migración

El script muestra un reporte final:

```
VERIFICACIÓN DE MIGRACIÓN
✓ organizations: 1 registros
✓ fighters: 650 registros
✓ events: 320 registros
✓ fights: 4500 registros
✓ fight_stats: 45000 registros
✓ data_quality: 4500 registros
✓ users: 15 registros
✓ analytics_events: 1200 registros
✓ update_logs: 8 registros
✓ picks: 45 registros
✓ sherdog_features: 200 registros
```

### Paso 4: Configurar Railway

1. Ve a tu proyecto en Railway
2. Variables → Añadir variable:

```
DATABASE_URL=postgresql://postgres:tu_password@host.supabase.com:6543/postgres?sslmode=require
JWT_SECRET=tu_secreto_seguro
ADMIN_PASSWORD=tu_password_admin
ODDS_API_KEY=tu_api_key (opcional)
```

3. Redeploy automático

### Paso 5: Probar en Producción

```bash
# Testear endpoint de health
curl https://tu-api.up.railway.app/

# Testear autenticación
curl -X POST https://tu-api.up.railway.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "tu_password"}'

# Testear predicciones
curl -X POST https://tu-api.up.railway.app/predict \
  -H "Content-Type: application/json" \
  -d '{"fighter_a": "Alex Pereira", "fighter_b": "Magomed Ankalaev"}'
```

---

## 📁 Archivos Creados/Modificados

### Nuevos Archivos

| Archivo | Propósito |
|---------|-----------|
| `db/schema_postgresql.sql` | Schema completo para PostgreSQL (11 tablas) |
| `scripts/migrate_all_to_supabase.py` | Script de migración completa |
| `scripts/migrate_remaining_tables_to_supabase.py` | Migración de tablas faltantes |
| `.env.example` | Plantilla de configuración |
| `docs/MIGRACION_POSTGRESQL.md` | Esta documentación |

### Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `backend/services/predictions.py` | Imports `param()` de `db.db_helpers` |
| `backend/routers/analytics.py` | `STRFTIME()` → `EXTRACT()` para PostgreSQL |
| `backend/routers/admin.py` | `last_insert_rowid()` → `LASTVAL()`, `SUBSTR` → `SUBSTRING` |
| `db/connection.py` | Mejora en `init_users_table()` con `RETURNING id` |
| `upload_to_supabase.py` | Marcado como deprecado |

### Archivos que NO se modificaron (ya eran compatibles)

- `db/db_helpers.py` - Ya tenía funciones helper
- `db/connection.py` - Ya tenía `is_postgresql()`
- `backend/auth.py` - Ya tenía `_param_placeholder()`
- `backend/routers/auth.py` - Ya usaba placeholders dinámicos
- `backend/routers/picks.py` - Ya usaba placeholders dinámicos
- `scripts/scraping/update_data.py` - Ya importaba `param()`

---

## 🐛 Solución de Problemas

### Error: "DATABASE_URL no configurada"

**Solución:**
```bash
# Verifica que .env exista
ls -la .env

# Verifica que DATABASE_URL esté definida
grep DATABASE_URL .env
```

### Error: "relation does not exist"

**Causa:** Las tablas no existen en Supabase.

**Solución:**
1. Ejecuta el schema en Supabase SQL Editor
2. O usa el script de migración que crea las tablas automáticamente

### Error: "duplicate key value violates unique constraint"

**Causa:** Intentas insertar datos que ya existen.

**Solución:**
- Los scripts ya usan `ON CONFLICT DO UPDATE`
- Si el error persiste, verifica que no haya datos duplicados en SQLite

### Error: "sequence does not exist"

**Causa:** Las secuencias SERIAL no se crearon correctamente.

**Solución:**
```sql
-- En Supabase SQL Editor, recrea las secuencias:
CREATE SEQUENCE IF NOT EXISTS users_id_seq;
CREATE SEQUENCE IF NOT EXISTS analytics_events_id_seq;
CREATE SEQUENCE IF NOT EXISTS update_logs_id_seq;
CREATE SEQUENCE IF NOT EXISTS picks_id_seq;
CREATE SEQUENCE IF NOT EXISTS sherdog_features_id_seq;
CREATE SEQUENCE IF NOT EXISTS fight_stats_stat_id_seq;

-- Asocia las secuencias a las columnas:
ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq');
-- (repetir para cada tabla)
```

### Error: "function strftime() does not exist"

**Causa:** `STRFTIME()` es específico de SQLite.

**Solución:**
- El código ya fue corregido para usar `EXTRACT()` en PostgreSQL
- Actualiza tu código con los cambios de `backend/routers/analytics.py`

### Frontend no conecta al backend

**Verifica:**
1. `frontend/src/config.ts` tenga la URL correcta de Railway
2. CORS esté habilitado en el backend
3. Variables de entorno en Vercel estén configuradas

---

## 📊 Referencias

### Enlaces Útiles

- [Supabase Docs](https://supabase.com/docs)
- [PostgreSQL vs SQLite](https://www.postgresql.org/docs/current/)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/)

### Comandos Útiles

```bash
# Verificar conexión a Supabase
psql postgresql://postgres:password@host.supabase.com:6543/postgres

# Listar tablas
\dt

# Ver schema de una tabla
\d users

# Contar registros
SELECT COUNT(*) FROM fighters;

# Ver últimas inserciones
SELECT * FROM users ORDER BY created_at DESC LIMIT 10;
```

---

## ✅ Checklist Final

- [ ] Schema PostgreSQL creado en Supabase
- [ ] Todas las tablas migradas
- [ ] Secuencias reseteadas correctamente
- [ ] Variables de entorno en Railway configuradas
- [ ] Variables de entorno en Vercel configuradas
- [ ] Tests de endpoints realizados
- [ ] Login de admin funciona
- [ ] Predicciones funcionan
- [ ] Analytics se están registrando
- [ ] Frontend conecta al backend

---

## 🎉 ¡Migración Completada!

Si llegaste hasta aquí, tu aplicación ahora usa 100% PostgreSQL con Supabase.

**Próximos pasos recomendados:**
1. Configurar backups automáticos en Supabase
2. Habilitar Point-in-Time Recovery
3. Monitorear uso de base de datos
4. Optimizar queries con índices adicionales si es necesario

---

**¿Problemas?** Revisa los logs en Railway y Supabase para debugging.
