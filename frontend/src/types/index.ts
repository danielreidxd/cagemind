export interface Fighter {
  name: string;
  wins: number;
  losses: number;
  draws: number;
  weight_lbs: number | null;
  stance: string | null;
  height_inches: number | null;
  reach_inches: number | null;
}

export interface FighterProfile {
  name: string;
  record: string;
  height: number | null;
  reach: number | null;
  weight: number | null;
  stance: string | null;
  win_probability: number;
}

export interface PredictionResponse {
  fighter_a: string;
  fighter_b: string;
  winner: string;
  winner_probability: number;
  loser_probability: number;
  method_prediction: Record<string, number>;
  goes_to_decision: { finish: number; decision: number };
  round_prediction: Record<string, number>;
  fighter_a_profile: FighterProfile;
  fighter_b_profile: FighterProfile;
}

export interface FighterSearchResult {
  count: number;
  fighters: Fighter[];
}

export interface FighterDetail {
  profile: Record<string, any>;
  career_stats: Record<string, any>;
  recent_fights: {
    opponent: string;
    result: string;
    method: string;
    round: number;
    date: string;
  }[];
}

export interface StatsResponse {
  database: Record<string, number>;
  last_event: { name: string; date_parsed: string } | null;
  top_fighters_by_wins: Fighter[];
  model_info: { features: number; models: string[] };
}
