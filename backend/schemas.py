"""
Schemas Pydantic para la API.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


# ============================================================
# PREDICCIONES
# ============================================================

class PredictionRequest(BaseModel):
    fighter_a: str
    fighter_b: str


class FighterProfile(BaseModel):
    name: str
    height_inches: Optional[float] = None
    reach_inches: Optional[float] = None
    weight_lbs: Optional[int] = None
    stance: Optional[str] = None
    wins: int = 0
    losses: int = 0
    draws: int = 0
    dob: Optional[str] = None
    slpm: Optional[float] = None
    str_acc: Optional[float] = None
    sapm: Optional[float] = None
    str_def: Optional[float] = None
    td_avg: Optional[float] = None
    td_acc: Optional[float] = None
    td_def: Optional[float] = None
    sub_avg: Optional[float] = None


class PredictionResponse(BaseModel):
    fighter_a: str
    fighter_b: str
    winner: str
    winner_probability: float
    loser_probability: float
    method_prediction: dict
    goes_to_decision: dict
    round_prediction: dict
    fighter_a_profile: dict
    fighter_b_profile: dict
    confidence: str = "HIGH"
    confidence_score: float = 1.0
    confidence_reason: str = ""
    explanations: list = []


# ============================================================
# AUTENTICACIÓN
# ============================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


# ============================================================
# ANALYTICS
# ============================================================

class TrackEvent(BaseModel):
    event_type: str       # page_view, prediction, search
    page: Optional[str] = None
    detail: Optional[str] = None


# ============================================================
# PICKS
# ============================================================

class PickRequest(BaseModel):
    event_name: str
    fighter_a: str
    fighter_b: str
    picked_winner: str
