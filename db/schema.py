
import sqlite3
from pathlib import Path
from config.settings import DB_PATH, setup_logging

logger = setup_logging("database")

SCHEMA_SQL = """
-- ============================================================
-- ORGANIZACIONES
-- ============================================================
CREATE TABLE IF NOT EXISTS organizations (
    org_id          TEXT PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    country         TEXT
);

-- Insertar UFC como organización por defecto
INSERT OR IGNORE INTO organizations (org_id, name, country)
VALUES ('ufc', 'UFC', 'USA');

-- ============================================================
-- PELEADORES
-- ============================================================
CREATE TABLE IF NOT EXISTS fighters (
    fighter_id      TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    first_name      TEXT,
    last_name       TEXT,
    nickname        TEXT,
    dob             TEXT,                    -- Fecha de nacimiento (texto: 'Mon DD, YYYY')
    height_inches   REAL,                    -- Altura en pulgadas
    weight_lbs      INTEGER,                 -- Peso en libras
    reach_inches    REAL,                    -- Alcance en pulgadas
    stance          TEXT,                    -- Orthodox, Southpaw, Switch
    wins            INTEGER DEFAULT 0,
    losses          INTEGER DEFAULT 0,
    draws           INTEGER DEFAULT 0,
    no_contests     INTEGER DEFAULT 0,
    
    -- Career stats (promedios de carrera de UFCStats)
    slpm            REAL,                    -- Sig. Strikes Landed per Minute
    str_acc         REAL,                    -- Striking Accuracy (0-1)
    sapm            REAL,                    -- Sig. Strikes Absorbed per Minute
    str_def         REAL,                    -- Strike Defense (0-1)
    td_avg          REAL,                    -- Takedown Avg per 15 min
    td_acc          REAL,                    -- Takedown Accuracy (0-1)
    td_def          REAL,                    -- Takedown Defense (0-1)
    sub_avg         REAL,                    -- Submission Avg per 15 min
    
    has_belt        BOOLEAN DEFAULT 0,
    profile_url     TEXT,
    source          TEXT DEFAULT 'ufcstats',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fighters_name ON fighters(name);
CREATE INDEX IF NOT EXISTS idx_fighters_weight ON fighters(weight_lbs);

-- ============================================================
-- EVENTOS
-- ============================================================
CREATE TABLE IF NOT EXISTS events (
    event_id        TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    date            TEXT,                    -- Texto original de la fecha
    date_parsed     DATE,                    -- Fecha parseada (YYYY-MM-DD)
    location        TEXT,
    org_id          TEXT DEFAULT 'ufc',
    url             TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (org_id) REFERENCES organizations(org_id)
);

CREATE INDEX IF NOT EXISTS idx_events_date ON events(date_parsed);
CREATE INDEX IF NOT EXISTS idx_events_org ON events(org_id);

-- ============================================================
-- PELEAS
-- ============================================================
CREATE TABLE IF NOT EXISTS fights (
    fight_id        TEXT PRIMARY KEY,
    event_id        TEXT NOT NULL,
    fighter_a_id    TEXT,
    fighter_b_id    TEXT,
    fighter_a_name  TEXT NOT NULL,
    fighter_b_name  TEXT NOT NULL,
    winner_id       TEXT,
    winner_name     TEXT,
    is_draw         BOOLEAN DEFAULT 0,
    is_no_contest   BOOLEAN DEFAULT 0,
    method          TEXT,                    -- KO/TKO, Submission, Decision, etc.
    method_detail   TEXT,                    -- Detalle específico
    round           INTEGER,
    time            TEXT,
    time_seconds    INTEGER,
    weight_class    TEXT,
    fight_url       TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(event_id),
    FOREIGN KEY (fighter_a_id) REFERENCES fighters(fighter_id),
    FOREIGN KEY (fighter_b_id) REFERENCES fighters(fighter_id)
);

CREATE INDEX IF NOT EXISTS idx_fights_event ON fights(event_id);
CREATE INDEX IF NOT EXISTS idx_fights_fighter_a ON fights(fighter_a_id);
CREATE INDEX IF NOT EXISTS idx_fights_fighter_b ON fights(fighter_b_id);
CREATE INDEX IF NOT EXISTS idx_fights_winner ON fights(winner_id);

-- ============================================================
-- ESTADÍSTICAS POR ROUND
-- ============================================================
CREATE TABLE IF NOT EXISTS fight_stats (
    stat_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    fight_id                TEXT NOT NULL,
    fighter_id              TEXT,
    fighter_name            TEXT NOT NULL,
    round                   INTEGER NOT NULL,
    
    -- Totals
    knockdowns              INTEGER,
    sig_strikes_landed      INTEGER,
    sig_strikes_attempted   INTEGER,
    sig_strike_pct          TEXT,
    total_strikes_landed    INTEGER,
    total_strikes_attempted INTEGER,
    takedowns_landed        INTEGER,
    takedowns_attempted     INTEGER,
    takedown_pct            TEXT,
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
    
    FOREIGN KEY (fight_id) REFERENCES fights(fight_id),
    FOREIGN KEY (fighter_id) REFERENCES fighters(fighter_id)
);

CREATE INDEX IF NOT EXISTS idx_fight_stats_fight ON fight_stats(fight_id);
CREATE INDEX IF NOT EXISTS idx_fight_stats_fighter ON fight_stats(fighter_id);

-- ============================================================
-- CALIDAD DE DATOS
-- ============================================================
CREATE TABLE IF NOT EXISTS data_quality (
    fight_id        TEXT PRIMARY KEY,
    detail_level    TEXT NOT NULL CHECK(detail_level IN ('full', 'basic', 'result_only')),
    has_round_stats BOOLEAN DEFAULT 0,
    has_sig_strikes BOOLEAN DEFAULT 0,
    source          TEXT DEFAULT 'ufcstats',
    notes           TEXT,
    FOREIGN KEY (fight_id) REFERENCES fights(fight_id)
);
"""


def init_database(db_path: Path = None) -> sqlite3.Connection:
    """Inicializa la base de datos con el esquema completo."""
    db_path = db_path or DB_PATH
    logger.info(f"Inicializando base de datos en: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    
    logger.info("Esquema de base de datos creado exitosamente")
    return conn


def get_connection(db_path: Path = None) -> sqlite3.Connection:
    """Obtiene una conexión a la base de datos."""
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_table_counts(conn: sqlite3.Connection) -> dict:
    """Retorna el conteo de filas de cada tabla."""
    tables = ["organizations", "fighters", "events", "fights", "fight_stats", "data_quality"]
    counts = {}
    for table in tables:
        try:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            counts[table] = 0
    return counts


if __name__ == "__main__":
    conn = init_database()
    counts = get_table_counts(conn)
    print("Tablas creadas:")
    for table, count in counts.items():
        print(f"  {table}: {count} filas")
    conn.close()
