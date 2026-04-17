

-- ============================================================
-- 1. ORGANIZACIONES
-- ============================================================
CREATE TABLE IF NOT EXISTS organizations (
    org_id          VARCHAR(50) PRIMARY KEY,
    name            VARCHAR(255) NOT NULL UNIQUE,
    country         VARCHAR(100),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insertar UFC como organización por defecto
INSERT INTO organizations (org_id, name, country)
VALUES ('ufc', 'UFC', 'USA')
ON CONFLICT (org_id) DO NOTHING;

-- Índices
CREATE INDEX IF NOT EXISTS idx_organizations_name ON organizations(name);

-- ============================================================
-- 2. PELEADORES (FIGHTERS)
-- ============================================================
CREATE TABLE IF NOT EXISTS fighters (
    fighter_id      VARCHAR(50) PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    nickname        VARCHAR(100),
    dob             VARCHAR(50),                    -- Fecha de nacimiento (texto: 'Mon DD, YYYY')
    height_inches   REAL,                           -- Altura en pulgadas
    weight_lbs      INTEGER,                        -- Peso en libras
    reach_inches    REAL,                           -- Alcance en pulgadas
    stance          VARCHAR(20),                    -- Orthodox, Southpaw, Switch
    wins            INTEGER DEFAULT 0,
    losses          INTEGER DEFAULT 0,
    draws           INTEGER DEFAULT 0,
    no_contests     INTEGER DEFAULT 0,

    -- Career stats (promedios de carrera de UFCStats)
    slpm            REAL,                           -- Sig. Strikes Landed per Minute
    str_acc         REAL,                           -- Striking Accuracy (0-1)
    sapm            REAL,                           -- Sig. Strikes Absorbed per Minute
    str_def         REAL,                           -- Strike Defense (0-1)
    td_avg          REAL,                           -- Takedown Avg per 15 min
    td_acc          REAL,                           -- Takedown Accuracy (0-1)
    td_def          REAL,                           -- Takedown Defense (0-1)
    sub_avg         REAL,                           -- Submission Avg per 15 min

    has_belt        BOOLEAN DEFAULT FALSE,
    profile_url     TEXT,
    source          VARCHAR(50) DEFAULT 'ufcstats',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_fighters_name ON fighters(name);
CREATE INDEX IF NOT EXISTS idx_fighters_weight ON fighters(weight_lbs);
CREATE INDEX IF NOT EXISTS idx_fighters_stance ON fighters(stance);

-- ============================================================
-- 3. EVENTOS
-- ============================================================
CREATE TABLE IF NOT EXISTS events (
    event_id        VARCHAR(50) PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    date            VARCHAR(100),                   -- Texto original de la fecha
    date_parsed     DATE,                           -- Fecha parseada (YYYY-MM-DD)
    location        VARCHAR(255),
    org_id          VARCHAR(50) DEFAULT 'ufc',
    url             TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_events_org FOREIGN KEY (org_id) REFERENCES organizations(org_id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_events_date ON events(date_parsed);
CREATE INDEX IF NOT EXISTS idx_events_org ON events(org_id);
CREATE INDEX IF NOT EXISTS idx_events_name ON events(name);

-- ============================================================
-- 4. PELEAS (FIGHTS)
-- ============================================================
CREATE TABLE IF NOT EXISTS fights (
    fight_id        VARCHAR(50) PRIMARY KEY,
    event_id        VARCHAR(50) NOT NULL,
    fighter_a_id    VARCHAR(50),
    fighter_b_id    VARCHAR(50),
    fighter_a_name  VARCHAR(255) NOT NULL,
    fighter_b_name  VARCHAR(255) NOT NULL,
    winner_id       VARCHAR(50),
    winner_name     VARCHAR(255),
    is_draw         BOOLEAN DEFAULT FALSE,
    is_no_contest   BOOLEAN DEFAULT FALSE,
    method          VARCHAR(100),                   -- KO/TKO, Submission, Decision, etc.
    method_detail   VARCHAR(255),                   -- Detalle específico
    round           INTEGER,
    time            VARCHAR(20),
    time_seconds    INTEGER,
    weight_class    VARCHAR(100),
    fight_url       TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_fights_event FOREIGN KEY (event_id) REFERENCES events(event_id),
    CONSTRAINT fk_fights_fighter_a FOREIGN KEY (fighter_a_id) REFERENCES fighters(fighter_id),
    CONSTRAINT fk_fights_fighter_b FOREIGN KEY (fighter_b_id) REFERENCES fighters(fighter_id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_fights_event ON fights(event_id);
CREATE INDEX IF NOT EXISTS idx_fights_fighter_a ON fights(fighter_a_id);
CREATE INDEX IF NOT EXISTS idx_fights_fighter_b ON fights(fighter_b_id);
CREATE INDEX IF NOT EXISTS idx_fights_winner ON fights(winner_id);
CREATE INDEX IF NOT EXISTS idx_fights_names ON fights(fighter_a_name, fighter_b_name);
CREATE INDEX IF NOT EXISTS idx_fights_weight_class ON fights(weight_class);

-- ============================================================
-- 5. ESTADÍSTICAS POR ROUND (FIGHT_STATS)
-- ============================================================
CREATE TABLE IF NOT EXISTS fight_stats (
    stat_id                 SERIAL PRIMARY KEY,
    fight_id                VARCHAR(50) NOT NULL,
    fighter_id              VARCHAR(50),
    fighter_name            VARCHAR(255) NOT NULL,
    round                   INTEGER NOT NULL,

    -- Totals
    knockdowns              INTEGER,
    sig_strikes_landed      INTEGER,
    sig_strikes_attempted   INTEGER,
    sig_strike_pct          VARCHAR(20),
    total_strikes_landed    INTEGER,
    total_strikes_attempted INTEGER,
    takedowns_landed        INTEGER,
    takedowns_attempted     INTEGER,
    takedown_pct            VARCHAR(20),
    submission_attempts     INTEGER,
    reversals               INTEGER,
    control_time_seconds    INTEGER,

    -- Significant Strikes por zona
    head_landed             INTEGER,
    head_attempted          INTEGER,
    body_landed             INTEGER,
    body_attempted          INTEGER,
    leg_landed              INTEGER,
    leg_attempted           INTEGER,

    -- Significant Strikes por posición
    distance_landed         INTEGER,
    distance_attempted      INTEGER,
    clinch_landed           INTEGER,
    clinch_attempted        INTEGER,
    ground_landed           INTEGER,
    ground_attempted        INTEGER,

    CONSTRAINT fk_fight_stats_fight FOREIGN KEY (fight_id) REFERENCES fights(fight_id),
    CONSTRAINT fk_fight_stats_fighter FOREIGN KEY (fighter_id) REFERENCES fighters(fighter_id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_fight_stats_fight ON fight_stats(fight_id);
CREATE INDEX IF NOT EXISTS idx_fight_stats_fighter ON fight_stats(fighter_id);
CREATE INDEX IF NOT EXISTS idx_fight_stats_fighter_name ON fight_stats(fighter_name);

-- ============================================================
-- 6. CALIDAD DE DATOS (DATA_QUALITY)
-- ============================================================
CREATE TABLE IF NOT EXISTS data_quality (
    fight_id        VARCHAR(50) PRIMARY KEY,
    detail_level    VARCHAR(20) NOT NULL CHECK(detail_level IN ('full', 'basic', 'result_only')),
    has_round_stats BOOLEAN DEFAULT FALSE,
    has_sig_strikes BOOLEAN DEFAULT FALSE,
    source          VARCHAR(50) DEFAULT 'ufcstats',
    notes           TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_data_quality_fight FOREIGN KEY (fight_id) REFERENCES fights(fight_id)
);

-- ============================================================
-- 7. USUARIOS (USERS) - Para autenticación
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50) NOT NULL UNIQUE,
    email           VARCHAR(255) UNIQUE,
    password        VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL DEFAULT 'user',
    verified        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============================================================
-- 8. EVENTOS DE ANALYTICS (ANALYTICS_EVENTS)
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_events (
    id              SERIAL PRIMARY KEY,
    event_type      VARCHAR(50) NOT NULL,
    page            VARCHAR(255),
    detail          TEXT,
    ip              VARCHAR(50),
    user_agent      TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON analytics_events(created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_page ON analytics_events(page);

-- ============================================================
-- 9. LOGS DE ACTUALIZACIÓN (UPDATE_LOGS)
-- ============================================================
CREATE TABLE IF NOT EXISTS update_logs (
    id              SERIAL PRIMARY KEY,
    action          VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'running',
    result          TEXT,
    started_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    finished_at     TIMESTAMP WITH TIME ZONE
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_update_logs_action ON update_logs(action);
CREATE INDEX IF NOT EXISTS idx_update_logs_status ON update_logs(status);
CREATE INDEX IF NOT EXISTS idx_update_logs_started_at ON update_logs(started_at);

-- ============================================================
-- 10. PICKS (VOTACIONES DE USUARIOS)
-- ============================================================
CREATE TABLE IF NOT EXISTS picks (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    event_name      VARCHAR(255) NOT NULL,
    fighter_a       VARCHAR(255) NOT NULL,
    fighter_b       VARCHAR(255) NOT NULL,
    picked_winner   VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_picks_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uniq_picks UNIQUE (user_id, event_name, fighter_a, fighter_b)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_picks_user_id ON picks(user_id);
CREATE INDEX IF NOT EXISTS idx_picks_event_name ON picks(event_name);
CREATE INDEX IF NOT EXISTS idx_picks_fighters ON picks(fighter_a, fighter_b);

-- ============================================================
-- 11. SHERDOG FEATURES (DATOS PRE-UFC)
-- ============================================================
CREATE TABLE IF NOT EXISTS sherdog_features (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(255) NOT NULL UNIQUE,
    pre_ufc_fights      INTEGER,
    pre_ufc_wr          REAL,                 -- Win rate pre-UFC
    pre_ufc_ko_rate     REAL,                 -- KO rate pre-UFC
    pre_ufc_sub_rate    REAL,                 -- Submission rate pre-UFC
    pre_ufc_dec_rate    REAL,                 -- Decision rate pre-UFC
    pre_ufc_finish_rate REAL,                 -- Finish rate pre-UFC
    pre_ufc_ko_loss_rate REAL,                -- KO loss rate pre-UFC
    pre_ufc_sub_loss_rate REAL,               -- Submission loss rate pre-UFC
    pre_ufc_streak      INTEGER,              -- Racha pre-UFC
    total_pro_fights    INTEGER,              -- Total peleas profesionales
    org_level           INTEGER,              -- Nivel de organización
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_sherdog_features_name ON sherdog_features(name);

-- ============================================================
-- VISTAS ÚTILES (OPTIONAL)
-- ============================================================

-- Vista: Estadísticas consolidadas por peleador
CREATE OR REPLACE VIEW fighter_career_summary AS
SELECT
    fs.fighter_name,
    COUNT(DISTINCT fs.fight_id) as total_fights,
    SUM(fs.knockdowns) as total_kd,
    SUM(fs.sig_strikes_landed) as total_sig_landed,
    SUM(fs.sig_strikes_attempted) as total_sig_attempted,
    SUM(fs.takedowns_landed) as total_td_landed,
    SUM(fs.takedowns_attempted) as total_td_attempted,
    SUM(fs.submission_attempts) as total_sub_att,
    SUM(fs.control_time_seconds) as total_ctrl,
    SUM(fs.head_landed) as total_head,
    SUM(fs.body_landed) as total_body,
    SUM(fs.leg_landed) as total_leg,
    SUM(fs.distance_landed) as total_distance,
    SUM(fs.clinch_landed) as total_clinch,
    SUM(fs.ground_landed) as total_ground,
    MAX(fs.round) as max_rounds
FROM fight_stats fs
GROUP BY fs.fighter_name;

-- ============================================================
-- TRIGGERS PARA UPDATED_AT
-- ============================================================

-- Función para actualizar timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para fighters
CREATE TRIGGER update_fighters_updated_at
    BEFORE UPDATE ON fighters
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger para data_quality
CREATE TRIGGER update_data_quality_updated_at
    BEFORE UPDATE ON data_quality
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger para users
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger para sherdog_features
CREATE TRIGGER update_sherdog_features_updated_at
    BEFORE UPDATE ON sherdog_features
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- COMENTARIOS EN TABLAS (DOCUMENTACIÓN)
-- ============================================================

COMMENT ON TABLE organizations IS 'Organizaciones de MMA (UFC, Bellator, etc.)';
COMMENT ON TABLE fighters IS 'Perfiles de luchadores y sus estadísticas de carrera';
COMMENT ON TABLE events IS 'Eventos de peleas (UFC numbered, Fight Night, etc.)';
COMMENT ON TABLE fights IS 'Resultados de peleas individuales dentro de eventos';
COMMENT ON TABLE fight_stats IS 'Estadísticas detalladas por round de cada pelea';
COMMENT ON TABLE data_quality IS 'Metadatos sobre la calidad de datos de cada pelea';
COMMENT ON TABLE users IS 'Usuarios del sistema con autenticación JWT';
COMMENT ON TABLE analytics_events IS 'Eventos de tracking para análisis de uso';
COMMENT ON TABLE update_logs IS 'Logs de ejecución de scripts de scraping';
COMMENT ON TABLE picks IS 'Predicciones/votaciones de usuarios para peleas';
COMMENT ON TABLE sherdog_features IS 'Estadísticas pre-UFC de peleadores (Sherdog)';
