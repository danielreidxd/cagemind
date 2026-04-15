
from __future__ import annotations

import pickle
import sqlite3
import os

from backend.config import DATABASE_URL, MODELS_PATH

# ============================================================
# CARGA DE MODELOS Y DATOS (al iniciar)
# ============================================================

models_bundle = None
fighter_cache = None
fighter_stats_cache = None




def get_db():
    """Retorna una conexión compatible. Soporta SQLite y PostgreSQL."""
    if DATABASE_URL.startswith("postgresql"):
        import psycopg2
        import psycopg2.extras # Necesario para DictCursor
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        clean_path = DATABASE_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(clean_path)
        conn.row_factory = sqlite3.Row
        return conn


def load_models():
    global models_bundle
    if models_bundle is None:
        with open(MODELS_PATH, "rb") as f:
            models_bundle = pickle.load(f)
    return models_bundle


class AliasDict(dict):
    """Diccionario que resuelve distintos casings y alias comunes (ej: Patricio Pitbull)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aliases = {
            "patricio pitbull": "Patricio Freire",
            "pitbull freire": "Patricio Freire",
            "dricus duplessis": "Dricus Du Plessis",
            "islam makachev": "Islam Makhachev",
            "khabib nurmagomedov": "Khabib Nurmagomedov",
            "khamzat chimaev": "Khamzat Chimaev",
            "magomed ankalaev": "Magomed Ankalaev",
            "zhang weili": "Weili Zhang",
        }
        self.lower_map = {str(k).lower(): k for k in self.keys()}

    def get(self, key, default=None):
        if not isinstance(key, str):
            return super().get(key, default)
        
        # 1. Exact match
        if super().__contains__(key):
            return super().get(key)
            
        key_lower = key.lower().strip()
        
        # 2. Alias match
        if key_lower in self.aliases:
            real_name = self.aliases[key_lower]
            if super().__contains__(real_name):
                return super().get(real_name)
                
        # 3. Case-insensitive match 
        if key_lower in self.lower_map:
            return super().get(self.lower_map[key_lower])
            
        return default

    def __contains__(self, key):
        return self.get(key) is not None

    def __getitem__(self, key):
        res = self.get(key)
        if res is None:
            raise KeyError(key)
        return res

def load_fighter_cache():
    """Carga todos los peleadores en memoria para búsquedas rápidas."""
    global fighter_cache
    if fighter_cache is None:
        conn = get_db()
        
        if DATABASE_URL.startswith("postgresql"):
            import psycopg2.extras
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        else:
            cur = conn.cursor()

        query = """
            SELECT name, height_inches, reach_inches, weight_lbs, stance,
                   wins, losses, draws, dob,
                   slpm, str_acc, sapm, str_def,
                   td_avg, td_acc, td_def, sub_avg
            FROM fighters
            ORDER BY name
        """
        cur.execute(query)
        rows = cur.fetchall()
        
        cur.close()
        conn.close()
        
        fighter_cache = AliasDict({row["name"]: dict(row) for row in rows})
    return fighter_cache


def load_fighter_stats_cache():
    """Carga stats agregadas por peleador."""
    global fighter_stats_cache
    if fighter_stats_cache is None:
        conn = get_db()

        if DATABASE_URL.startswith("postgresql"):
            import psycopg2.extras
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        else:
            cur = conn.cursor()

        query = """
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
            GROUP BY fs.fighter_name
        """
        cur.execute(query)
        stats = cur.fetchall()
        
        cur.close()
        conn.close()
        
        fighter_stats_cache = AliasDict({row["fighter_name"]: dict(row) for row in stats})
    return fighter_stats_cache
