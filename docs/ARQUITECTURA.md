# 🏗️ Arquitectura del Sistema - CageMind

Diagrama completo de la arquitectura del sistema UFC Fight Predictor.

---

## 📊 Diagrama de Arquitectura General

```mermaid
flowchart TB
    subgraph Fuentes["📥 Fuentes de Datos"]
        U1[UFCStats.com]
        S1[Sherdog.com]
        U2[UFC.com]
    end

    subgraph Scraping["🕷️ Scraping Pipeline"]
        direction TB
        SP1[scrape_fighters.py]
        SP2[scrape_events.py]
        SP3[scrape_fights.py]
        SP4[scrape_fight_stats.py]
        SP5[scrape_sherdog.py]
        CP{Checkpoint System}
        RL[Rate Limiter]
        LOG[Logging System]
    end

    subgraph Procesamiento["⚙️ Procesamiento de Datos"]
        direction TB
        CLEAN[Data Cleaning]
        VAL[Validation]
        NORM[Normalization]
        TRANS[Transformation]
        FEAT[Feature Engineering]
    end

    subgraph Almacenamiento["💾 Almacenamiento"]
        direction TB
        PG[("🗄️ PostgreSQL (Supabase)")]
        subgraph Tablas["Tablas (11)"]
            T1[organizations]
            T2[fighters]
            T3[events]
            T4[fights]
            T5[fight_stats]
            T6[data_quality]
            T7[users]
            T8[analytics_events]
            T9[update_logs]
            T10[picks]
            T11[sherdog_features]
        end
    end

    subgraph ML["🤖 Machine Learning"]
        direction TB
        FE[Feature Extraction]
        TRAIN[Model Training]
        CAL[Calibration]
        subgraph Modelos["Modelos Entrenados"]
            M1[Winner Model<br/>XGBoost]
            M2[Method Model<br/>Logistic Regression]
            M3[Distance Model<br/>Random Forest]
            M4[Round Model<br/>XGBoost]
        end
        subgraph Resultados["Resultados"]
            MR1[Model Metrics]
            MR2[Feature Importance]
            MR3[Confusion Matrix]
        end
    end

    subgraph Backend["🔙 Backend API"]
        direction TB
        FASTAPI[FastAPI Server]
        subgraph Routers["Routers (9)"]
            R1[fighters]
            R2[events]
            R3[fights]
            R4[predictions]
            R5[stats]
            R6[auth]
            R7[admin]
            R8[analytics]
            R9[odds]
        end
        subgraph Servicios["Services"]
            S1[predictions.py]
            S2[fighters.py]
            S3[odds.py]
            S4[explainability.py]
        end
        AUTH[JWT Authentication]
        CORS[CORS Middleware]
    end

    subgraph Frontend["🎨 Frontend"]
        direction TB
        REACT[React 18 + TypeScript]
        VITE[Vite Build Tool]
        subgraph Componentes["Componentes"]
            C1[Fighter Cards]
            C2[Event Cards]
            C3[Prediction Sandbox]
            C4[Leaderboard]
            C5[Auth Forms]
        end
        subgraph Contextos["Context API"]
            CT1[AuthContext]
            CT2[ThemeContext]
        end
        TAIL[Tailwind CSS]
    end

    subgraph Deploy["🚀 Deploy & Hosting"]
        direction TB
        VERCEL[Vercel<br/>Frontend]
        RAIL[Railway<br/>Backend API]
        SUPABASE[Supabase<br/>PostgreSQL]
    end

    subgraph Usuarios["👥 Usuarios"]
        direction TB
        USER1[Usuarios Públicos]
        USER2[Administradores]
        USER3[Sistema ML]
    end

    %% Flujo de Datos
    U1 -->|HTTP Requests| SP1
    U1 -->|HTTP Requests| SP2
    U1 -->|HTTP Requests| SP3
    U1 -->|HTTP Requests| SP4
    S1 -->|HTTP Requests| SP5
    
    SP1 --> CP
    SP2 --> CP
    SP3 --> CP
    SP4 --> CP
    SP5 --> CP
    
    CP -->|Datos Crudos| CLEAN
    RL -.-> SP1
    RL -.-> SP2
    RL -.-> SP3
    RL -.-> SP4
    RL -.-> SP5
    
    CLEAN --> VAL
    VAL --> NORM
    NORM --> TRANS
    TRANS --> FEAT
    
    FEAT -->|Bulk Insert| PG
    PG --> T1
    PG --> T2
    PG --> T3
    PG --> T4
    PG --> T5
    PG --> T6
    PG --> T7
    PG --> T8
    PG --> T9
    PG --> T10
    PG --> T11
    
    T2 -->|Fighter Data| FE
    T4 -->|Fight History| FE
    T5 -->|Stats Agregadas| FE
    T11 -->|Pre-UFC Data| FE
    
    FE --> TRAIN
    TRAIN --> M1
    TRAIN --> M2
    TRAIN --> M3
    TRAIN --> M4
    TRAIN --> MR1
    TRAIN --> MR2
    TRAIN --> MR3
    
    M1 --> CAL
    M2 --> CAL
    M3 --> CAL
    M4 --> CAL
    
    CAL -->|Modelos .pkl| FASTAPI
    
    USER1 -->|HTTP/HTTPS| VERCEL
    USER2 -->|HTTP/HTTPS| VERCEL
    
    VERCEL -->|API Calls| RAIL
    RAIL --> FASTAPI
    
    FASTAPI --> R1
    FASTAPI --> R2
    FASTAPI --> R3
    FASTAPI --> R4
    FASTAPI --> R5
    FASTAPI --> R6
    FASTAPI --> R7
    FASTAPI --> R8
    FASTAPI --> R9
    
    R1 --> S2
    R4 --> S1
    R9 --> S3
    R4 --> S4
    
    FASTAPI --> AUTH
    FASTAPI --> CORS
    
    R1 -->|Read| T2
    R2 -->|Read| T3
    R3 -->|Read| T4
    R4 -->|Read/Write| T2
    R4 -->|Read| M1
    R5 -->|Read| T1
    R5 -->|Read| T2
    R5 -->|Read| T3
    R5 -->|Read| T4
    R6 -->|Write| T7
    R7 -->|Read| T1
    R7 -->|Read| T2
    R7 -->|Read| T3
    R7 -->|Read| T4
    R8 -->|Write| T8
    R9 -->|External| ODDS_API
    
    RAIL -->|Read/Write| PG
    VERCEL -->|API REST| RAIL
    
    FASTAPI --> C1
    FASTAPI --> C2
    FASTAPI --> C3
    FASTAPI --> C4
    FASTAPI --> C5
    
    REACT --> VITE
    VITE --> VERCEL
    
    C1 --> TAIL
    C2 --> TAIL
    C3 --> TAIL
    C4 --> TAIL
    C5 --> TAIL
    
    CT1 --> AUTH
    CT2 --> TAIL
    
    USER3 -->|Entrenamiento| TRAIN
    
    ODDS_API[["📊 Odds API<br/>(the-odds-api.com)"]] -.-> R9
    
    %% Estilos
    classDef fuentes fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef scraping fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef procesamiento fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef almacenamiento fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef ml fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef backend fill:#fff8e1,stroke:#f57f17,stroke-width:2px
    classDef frontend fill:#e3f2fd,stroke:#0d47a1,stroke-width:2px
    classDef deploy fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    classDef usuarios fill:#ffebee,stroke:#b71c1c,stroke-width:2px
    
    class U1,S1,U2 fuentes
    class SP1,SP2,SP3,SP4,SP5,CP,RL,LOG scraping
    class CLEAN,VAL,NORM,TRANS,FEAT procesamiento
    class PG,T1,T2,T3,T4,T5,T6,T7,T8,T9,T10,T11 almacenamiento
    class FE,TRAIN,CAL,M1,M2,M3,M4,MR1,MR2,MR3 ml
    class FASTAPI,R1,R2,R3,R4,R5,R6,R7,R8,R9,S1,S2,S3,S4,AUTH,CORS backend
    class REACT,VITE,C1,C2,C3,C4,C5,CT1,CT2,TAIL frontend
    class VERCEL,RAIL,SUPABASE deploy
    class USER1,USER2,USER3 usuarios
```

---

## 🔄 Flujo de Datos Detallado

```mermaid
sequenceDiagram
    participant U as Usuario
    participant V as Vercel (Frontend)
    participant R as Railway (Backend)
    participant S as Supabase (PostgreSQL)
    participant M as ML Models
    participant API as Odds API
    participant SCR as Scrapers

    %% Inicio de sesión
    U->>V: Login (username/password)
    V->>R: POST /auth/login
    R->>S: SELECT user WHERE username=?
    S-->>R: User data
    R->>R: Verify password (bcrypt)
    R->>R: Generate JWT token
    R-->>V: JWT token
    V-->>U: Dashboard

    %% Búsqueda de peleador
    U->>V: Search fighter
    V->>R: GET /fighters?search=name
    R->>S: SELECT FROM fighters WHERE name LIKE ?
    S-->>R: Fighters list
    R-->>V: JSON response
    V-->>U: Fighter cards

    %% Predicción
    U->>V: Select fighters A vs B
    V->>R: POST /predict {fighter_a, fighter_b}
    R->>S: SELECT fighter stats
    S-->>R: Fighter A & B data
    R->>M: Load models (.pkl)
    M-->>R: Loaded models
    R->>R: Compute features
    R->>M: Predict winner (XGBoost)
    M-->>R: Win probability
    R->>M: Predict method (LogReg)
    M-->>R: Method probabilities
    R->>M: Predict round (XGBoost)
    M-->>R: Round probabilities
    R->>R: Apply calibration
    R->>R: Generate explanations
    R-->>V: Prediction JSON
    V-->>U: Prediction UI

    %% Value bets
    R->>API: GET odds
    API-->>R: American odds
    R->>R: Calculate implied prob
    R->>R: Compare with ML prob
    R->>R: Identify value bets
    R-->>V: Value bets list
    V-->>U: Betting recommendations

    %% Admin - Trigger scraping
    U->>V: Admin panel
    V->>R: POST /admin/update
    R->>S: INSERT update_logs (running)
    S-->>R: Log ID
    R->>SCR: Execute scraper
    SCR->>SCR: Scrape UFCStats
    SCR->>SCR: Process data
    SCR->>S: Bulk insert fighters
    SCR->>S: Bulk insert events
    SCR->>S: Bulk insert fights
    SCR->>S: Bulk insert fight_stats
    S-->>SCR: Success
    SCR-->>R: Complete
    R->>S: UPDATE update_logs (success)
    S-->>R: Updated
    R-->>V: Update complete
    V-->>U: Results

    %% Analytics tracking
    V->>R: POST /analytics/track
    R->>S: INSERT analytics_events
    S-->>R: OK
    R-->>V: Tracked
```

---

## 🗂️ Estructura de la Base de Datos

```mermaid
erDiagram
    organizations ||--o{ events : "hosts"
    events ||--o{ fights : "contains"
    fighters ||--o{ fights : "participates in"
    fights ||--o{ fight_stats : "has"
    fights ||--o{ data_quality : "tracked by"
    users ||--o{ picks : "makes"
    users ||--o{ analytics_events : "generates"
    users ||--o{ update_logs : "triggers"

    organizations {
        text org_id PK
        text name UK
        text country
    }

    fighters {
        text fighter_id PK
        text name
        real height_inches
        real reach_inches
        integer weight_lbs
        text stance
        integer wins
        integer losses
        real slpm
        real str_acc
        real td_avg
    }

    events {
        text event_id PK
        text name
        date date_parsed
        text location
    }

    fights {
        text fight_id PK
        text event_id FK
        text fighter_a_name
        text fighter_b_name
        text winner_name
        text method
        integer round
    }

    fight_stats {
        integer stat_id PK
        text fight_id FK
        text fighter_id FK
        integer round
        integer sig_strikes_landed
        integer takedowns_landed
        integer control_time_seconds
    }

    users {
        integer id PK
        text username UK
        text email UK
        text password
        text role
    }

    picks {
        integer id PK
        integer user_id FK
        text event_name
        text picked_winner
    }
```

---

## 🌐 Infraestructura de Deploy

```mermaid
flowchart TB
    subgraph CDN["🌍 CDN"]
        VercelEdge[Vercel Edge Network]
    end

    subgraph Frontend["🎨 Frontend"]
        Vercel[Vercel<br/>React SPA]
    end

    subgraph Backend["🔙 Backend"]
        Railway[Railway<br/>FastAPI<br/>Python 3.10+]
    end

    subgraph Database["💾 Database"]
        Supabase[Supabase<br/>PostgreSQL 15<br/>AWS us-west-2]
    end

    subgraph External["🌐 External"]
        OddsAPI[Odds API]
        UFCStats[UFCStats.com]
        Sherdog[Sherdog.com]
    end

    Browser[👤 Usuario] --> VercelEdge
    VercelEdge --> Vercel
    Vercel -->|API REST| Railway
    Railway -->|psycopg2 SSL| Supabase
    Railway -->|HTTP| UFCStats
    Railway -->|HTTP| Sherdog
    Railway -->|API| OddsAPI
```

---

## 📈 Flujo de Predicción

```mermaid
flowchart LR
    U[Usuario] --> REQ[POST /predict]
    REQ --> DB[(PostgreSQL)]
    DB --> F1[Get Fighter A]
    DB --> F2[Get Fighter B]
    F1 --> FE[Feature Vector<br/>47 features]
    F2 --> FE
    FE --> M1[XGBoost<br/>Winner]
    FE --> M2[LogReg<br/>Method]
    FE --> M3[RF<br/>Distance]
    FE --> M4[XGBoost<br/>Round]
    M1 --> CAL[Calibration]
    M2 --> CAL
    M3 --> CAL
    M4 --> CAL
    CAL --> RESP[JSON Response]
    RESP --> U
```


