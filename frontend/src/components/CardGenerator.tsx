import { useState, useRef, useCallback } from 'react';
import type { PredictionResponse } from '../types';
import { formatHeight, formatProbability } from '../utils/api';
import { useAuth } from '../contexts/AuthContext';

type CardFormat = 'vertical' | 'horizontal';

interface Props {
  prediction: PredictionResponse;
  eventName?: string;
}

// ─── Inline CageMind logo as data URI (avoids cross-origin issues with html2canvas) ───
const LOGO_SVG = `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<polygon points="50,8 89,29 89,71 50,92 11,71 11,29" fill="none" stroke="#C8102E" stroke-width="4"/>
<polygon points="50,22 74,36 74,64 50,78 26,64 26,36" fill="none" stroke="#D4AF37" stroke-width="2" opacity="0.5"/>
<circle cx="38" cy="38" r="4" fill="#C8102E"/><circle cx="62" cy="38" r="4" fill="#C8102E"/>
<circle cx="50" cy="50" r="5" fill="#D4AF37"/>
<circle cx="38" cy="62" r="4" fill="#C8102E"/><circle cx="62" cy="62" r="4" fill="#C8102E"/>
<line x1="38" y1="38" x2="50" y2="50" stroke="#C8102E" stroke-width="1.5" opacity="0.6"/>
<line x1="62" y1="38" x2="50" y2="50" stroke="#C8102E" stroke-width="1.5" opacity="0.6"/>
<line x1="38" y1="62" x2="50" y2="50" stroke="#C8102E" stroke-width="1.5" opacity="0.6"/>
<line x1="62" y1="62" x2="50" y2="50" stroke="#C8102E" stroke-width="1.5" opacity="0.6"/>
</svg>`)}`;

// ─── Color constants ───
const COLORS = {
  bg: '#0D0D0D',
  card: '#1C1C3A',
  border: '#2A2A4A',
  red: '#C8102E',
  gold: '#D4AF37',
  blue: '#378ADD',
  purple: '#7F77DD',
  text: '#E0E0E0',
  muted: '#8888AA',
  dark: '#0D0D0D',
};

// ─── Method colors ───
const METHOD_COLORS: Record<string, string> = {
  'KO/TKO': COLORS.red,
  'Submission': COLORS.purple,
  'Decision': COLORS.blue,
};

export default function CardGenerator({ prediction, eventName }: Props) {
  const { isAdmin } = useAuth();
  const [format, setFormat] = useState<CardFormat>('vertical');
  const [generating, setGenerating] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  const { fighter_a_profile: a, fighter_b_profile: b, winner } = prediction;
  const aIsWinner = winner === prediction.fighter_a;
  let probA = Math.round(a.win_probability * 100);
  let probB = 100 - probA;

  if (probA === 50 && probB === 50) {
    if (a.win_probability > b.win_probability) {
      probA = 51; probB = 49;
    } else {
      probA = 49; probB = 51;
    }
  }

  const winnerProb = aIsWinner ? probA : probB;

  const methodEntries = Object.entries(prediction.method_prediction).map(
    ([name, value]) => ({ name, pct: Math.round(value * 100) })
  );
  const finishPct = Math.round(prediction.goes_to_decision.finish * 100);
  const decisionPct = Math.round(prediction.goes_to_decision.decision * 100);

  const roundEntries = Object.entries(prediction.round_prediction).map(
    ([name, value]) => ({ name: name.replace('Round ', 'R'), pct: Math.round(value * 100) })
  );

  const handleGenerate = useCallback(async () => {
    if (!cardRef.current) return;
    setGenerating(true);

    try {
      // Dynamically import html2canvas to keep bundle lean
      const html2canvas = (await import('html2canvas')).default;

      const canvas = await html2canvas(cardRef.current, {
        backgroundColor: COLORS.bg,
        scale: 2, // 2x for retina quality
        useCORS: true,
        logging: false,
        width: cardRef.current.offsetWidth,
        height: cardRef.current.offsetHeight,
      });

      const link = document.createElement('a');
      const safeName = `${prediction.fighter_a.replace(/\s/g, '_')}_vs_${prediction.fighter_b.replace(/\s/g, '_')}`;
      link.download = `CageMind_${safeName}_${format}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (err) {
      console.error('Error generating card:', err);
    } finally {
      setGenerating(false);
    }
  }, [format, prediction]);

  // ─── Shared sub-components ───
  const LogoHeader = ({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) => {
    const logoSizes = { sm: 24, md: 32, lg: 44 };
    const textSizes = { sm: '14px', md: '18px', lg: '24px' };
    const s = logoSizes[size];
    const t = textSizes[size];
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: size === 'lg' ? 12 : 8 }}>
        <img src={LOGO_SVG} alt="" width={s} height={s} />
        <span style={{ fontWeight: 800, fontSize: t, letterSpacing: '0.5px' }}>
          <span style={{ color: COLORS.red }}>CAGE</span>
          <span style={{ color: COLORS.gold }}>MIND</span>
        </span>
      </div>
    );
  };

  const ProbBar = ({ pctA, pctB, height = 12 }: { pctA: number; pctB: number; height?: number }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ color: COLORS.red, fontWeight: 700, fontSize: height > 10 ? 14 : 11, minWidth: 42, textAlign: 'right' as const }}>{pctA}%</span>
      <div style={{ flex: 1, height, background: COLORS.dark, borderRadius: height / 2, overflow: 'hidden', display: 'flex' }}>
        <div style={{ width: `${pctA}%`, height: '100%', background: COLORS.red, borderRadius: `${height / 2}px 0 0 ${height / 2}px` }} />
        <div style={{ width: `${pctB}%`, height: '100%', background: COLORS.blue, borderRadius: `0 ${height / 2}px ${height / 2}px 0` }} />
      </div>
      <span style={{ color: COLORS.blue, fontWeight: 700, fontSize: height > 10 ? 14 : 11, minWidth: 42 }}>{pctB}%</span>
    </div>
  );

  const MethodBars = ({ fontSize = 13, barHeight = 16 }: { fontSize?: number; barHeight?: number }) => (
    <div style={{ display: 'flex', flexDirection: 'column' as const, gap: 6 }}>
      {methodEntries.map((m) => (
        <div key={m.name} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: COLORS.text, fontSize, minWidth: 78 }}>{m.name}</span>
          <div style={{ flex: 1, height: barHeight, background: COLORS.dark, borderRadius: 4, overflow: 'hidden' }}>
            <div style={{ width: `${m.pct}%`, height: '100%', background: METHOD_COLORS[m.name] || '#888', borderRadius: 4 }} />
          </div>
          <span style={{ color: COLORS.muted, fontSize: fontSize - 1, minWidth: 32, textAlign: 'right' as const }}>{m.pct}%</span>
        </div>
      ))}
    </div>
  );

  const FinishDonut = ({ size = 80 }: { size?: number }) => {
    const r = size * 0.35;
    const strokeW = size * 0.12;
    const c = 2 * Math.PI * r;
    const finishLen = (finishPct / 100) * c;
    const decLen = (decisionPct / 100) * c;
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Decision arc */}
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={COLORS.blue} strokeWidth={strokeW}
            strokeDasharray={`${decLen} ${c}`}
            strokeDashoffset={0}
            transform={`rotate(-90 ${size / 2} ${size / 2})`} />
          {/* Finish arc on top */}
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={COLORS.red} strokeWidth={strokeW}
            strokeDasharray={`${finishLen} ${c}`}
            strokeDashoffset={-decLen}
            transform={`rotate(-90 ${size / 2} ${size / 2})`} />
        </svg>
        <div style={{ display: 'flex', flexDirection: 'column' as const, gap: 4 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS.red }} />
            <span style={{ color: COLORS.muted, fontSize: 12 }}>Finish <strong style={{ color: COLORS.text }}>{finishPct}%</strong></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS.blue }} />
            <span style={{ color: COLORS.muted, fontSize: 12 }}>Decision <strong style={{ color: COLORS.text }}>{decisionPct}%</strong></span>
          </div>
        </div>
      </div>
    );
  };

  const RoundBars = ({ barHeight = 80, fontSize = 11 }: { barHeight?: number; fontSize?: number }) => {
    const maxPct = Math.max(...roundEntries.map((r) => r.pct), 1);
    return (
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: barHeight + 20 }}>
        {roundEntries.map((r) => (
          <div key={r.name} style={{ flex: 1, display: 'flex', flexDirection: 'column' as const, alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
            <span style={{ color: COLORS.muted, fontSize: fontSize - 1, marginBottom: 2 }}>{r.pct}%</span>
            <div style={{
              width: '100%', maxWidth: 36,
              height: `${(r.pct / maxPct) * barHeight}px`,
              background: COLORS.gold, borderRadius: '4px 4px 0 0',
              minHeight: 4,
            }} />
            <span style={{ color: COLORS.text, fontSize, marginTop: 4 }}>{r.name}</span>
          </div>
        ))}
      </div>
    );
  };

  const Watermark = ({ fontSize = 11 }: { fontSize?: number }) => (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, opacity: 0.5 }}>
      <img src={LOGO_SVG} alt="" width={14} height={14} />
      <span style={{ color: COLORS.muted, fontSize, letterSpacing: 0.5 }}>
        cagemind.app · ML Predictions
      </span>
    </div>
  );

  const FighterCard = ({ name, record, height, reach, weight, stance, prob, isWinner, color, label }:
    { name: string; record: string; height: number | null; reach: number | null; weight: number | null; stance: string | null; prob: number; isWinner: boolean; color: string; label: string }) => (
    <div style={{
      background: isWinner ? `${color}15` : `${COLORS.dark}90`,
      border: isWinner ? `2px solid ${color}60` : `1px solid ${COLORS.border}`,
      borderRadius: 12, padding: 16, textAlign: 'center' as const, flex: 1,
    }}>
      <p style={{ color, fontSize: 10, fontWeight: 700, textTransform: 'uppercase' as const, letterSpacing: 1.5 }}>{label}</p>
      <p style={{ color: isWinner ? '#fff' : COLORS.muted, fontSize: 18, fontWeight: 800, marginTop: 6 }}>{name}</p>
      <p style={{ color: COLORS.muted, fontSize: 12, marginTop: 2 }}>{record}</p>
      <p style={{ color: isWinner ? color : COLORS.muted, fontSize: 24, fontWeight: 800, marginTop: 8 }}>{prob}%</p>
      <div style={{ marginTop: 10, fontSize: 11, color: COLORS.muted, lineHeight: 1.8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Altura</span><span style={{ color: COLORS.text }}>{formatHeight(height)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Reach</span><span style={{ color: COLORS.text }}>{reach ? `${reach}"` : '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Peso</span><span style={{ color: COLORS.text }}>{weight ? `${weight} lbs` : '--'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Stance</span><span style={{ color: COLORS.text }}>{stance || '--'}</span>
        </div>
      </div>
    </div>
  );

  // ─── VERTICAL CARD (1080×1920 IG Story) ───
  const VerticalCard = () => (
    <div style={{
      width: 1080, height: 1920,
      background: COLORS.bg,
      fontFamily: 'Inter, system-ui, sans-serif',
      color: COLORS.text,
      padding: '48px 48px 36px',
      display: 'flex', flexDirection: 'column' as const,
      position: 'relative' as const,
      overflow: 'hidden',
    }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <LogoHeader size="lg" />
        {eventName && (
          <span style={{ color: COLORS.muted, fontSize: 16 }}>{eventName}</span>
        )}
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: COLORS.border, marginBottom: 32 }} />

      {/* Winner Banner */}
      <div style={{
        textAlign: 'center', padding: '28px 0', marginBottom: 28,
        background: `${COLORS.card}`,
        borderRadius: 16, border: `1px solid ${COLORS.border}`,
      }}>
        <p style={{ color: COLORS.muted, fontSize: 14, textTransform: 'uppercase', letterSpacing: 2, marginBottom: 6 }}>
          Prediccion del modelo
        </p>
        <p style={{ color: '#fff', fontSize: 40, fontWeight: 900 }}>{winner}</p>
        <p style={{ color: COLORS.gold, fontSize: 36, fontWeight: 800, marginTop: 4 }}>{winnerProb}%</p>
      </div>

      {/* Fighter Cards */}
      <div style={{ display: 'flex', gap: 20, marginBottom: 28 }}>
        <FighterCard
          name={a.name} record={a.record} height={a.height} reach={a.reach}
          weight={a.weight} stance={a.stance} prob={probA} isWinner={aIsWinner}
          color={COLORS.red} label="Peleador A"
        />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{
            width: 56, height: 56, borderRadius: '50%', background: COLORS.border,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <span style={{ color: COLORS.muted, fontWeight: 700, fontSize: 16 }}>VS</span>
          </div>
        </div>
        <FighterCard
          name={b.name} record={b.record} height={b.height} reach={b.reach}
          weight={b.weight} stance={b.stance} prob={probB} isWinner={!aIsWinner}
          color={COLORS.blue} label="Peleador B"
        />
      </div>

      {/* Probability Bar */}
      <div style={{
        background: `${COLORS.card}cc`, border: `1px solid ${COLORS.border}`,
        borderRadius: 12, padding: '16px 20px', marginBottom: 20,
      }}>
        <p style={{ color: COLORS.muted, fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 10 }}>
          Probabilidad de victoria
        </p>
        <ProbBar pctA={probA} pctB={probB} height={14} />
      </div>

      {/* Method + Finish */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20, flex: 1 }}>
        {/* Method */}
        <div style={{
          flex: 1, background: `${COLORS.card}cc`, border: `1px solid ${COLORS.border}`,
          borderRadius: 12, padding: '16px 20px',
        }}>
          <p style={{ color: COLORS.muted, fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 14 }}>
            Metodo de victoria
          </p>
          <MethodBars fontSize={14} barHeight={18} />
        </div>

        {/* Finish vs Decision */}
        <div style={{
          flex: 1, background: `${COLORS.card}cc`, border: `1px solid ${COLORS.border}`,
          borderRadius: 12, padding: '16px 20px',
        }}>
          <p style={{ color: COLORS.muted, fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 14 }}>
            Finish vs Decision
          </p>
          <FinishDonut size={90} />
        </div>
      </div>

      {/* Round prediction */}
      {prediction.goes_to_decision.finish > 0.35 && (
        <div style={{
          background: `${COLORS.card}cc`, border: `1px solid ${COLORS.border}`,
          borderRadius: 12, padding: '16px 20px', marginBottom: 20,
        }}>
          <p style={{ color: COLORS.muted, fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 10 }}>
            Round de finalizacion
          </p>
          <RoundBars barHeight={70} fontSize={12} />
        </div>
      )}

      {/* Footer */}
      <div style={{ marginTop: 'auto', paddingTop: 16 }}>
        <div style={{ height: 1, background: COLORS.border, marginBottom: 16 }} />
        <Watermark fontSize={13} />
      </div>
    </div>
  );

  // ─── HORIZONTAL CARD (1200×675 Twitter) ───
  const HorizontalCard = () => (
    <div style={{
      width: 1200, height: 675,
      background: COLORS.bg,
      fontFamily: 'Inter, system-ui, sans-serif',
      color: COLORS.text,
      padding: '28px 36px 20px',
      display: 'flex', flexDirection: 'column' as const,
      position: 'relative' as const,
      overflow: 'hidden',
    }}>

      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <LogoHeader size="md" />
        <div style={{ textAlign: 'right' }}>
          {eventName && <span style={{ color: COLORS.muted, fontSize: 13 }}>{eventName} · </span>}
          <span style={{ color: COLORS.muted, fontSize: 13 }}>ML Prediction</span>
        </div>
      </div>

      <div style={{ height: 1, background: COLORS.border, marginBottom: 16 }} />

      {/* Main content: 3 columns */}
      <div style={{ display: 'flex', gap: 20, flex: 1 }}>
        {/* LEFT: Winner + Fighters + Prob Bar */}
        <div style={{ flex: 1.1, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Winner */}
          <div style={{
            textAlign: 'center', padding: '14px 0',
            background: `${COLORS.card}`,
            borderRadius: 10, border: `1px solid ${COLORS.border}`,
          }}>
            <p style={{ color: COLORS.muted, fontSize: 10, textTransform: 'uppercase', letterSpacing: 2, marginBottom: 2 }}>
              Ganador predicho
            </p>
            <p style={{ color: '#fff', fontSize: 22, fontWeight: 900 }}>{winner}</p>
            <p style={{ color: COLORS.gold, fontSize: 20, fontWeight: 800 }}>{winnerProb}%</p>
          </div>

          {/* Fighters side by side compact */}
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{
              flex: 1, background: aIsWinner ? `${COLORS.red}15` : `${COLORS.dark}90`,
              border: aIsWinner ? `2px solid ${COLORS.red}60` : `1px solid ${COLORS.border}`,
              borderRadius: 8, padding: 10, textAlign: 'center',
            }}>
              <p style={{ color: COLORS.red, fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1 }}>Peleador A</p>
              <p style={{ color: aIsWinner ? '#fff' : COLORS.muted, fontSize: 13, fontWeight: 800, marginTop: 2 }}>{a.name}</p>
              <p style={{ color: COLORS.muted, fontSize: 10 }}>{a.record}</p>
              <p style={{ color: aIsWinner ? COLORS.red : COLORS.muted, fontSize: 18, fontWeight: 800, marginTop: 4 }}>{probA}%</p>
              <div style={{ fontSize: 9, color: COLORS.muted, marginTop: 4, lineHeight: 1.6 }}>
                <span>{formatHeight(a.height)} · {a.reach ? a.reach + '"' : '--'} · {a.weight ? a.weight + 'lb' : '--'}</span>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{
                width: 28, height: 28, borderRadius: '50%', background: COLORS.border,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <span style={{ color: COLORS.muted, fontWeight: 700, fontSize: 9 }}>VS</span>
              </div>
            </div>
            <div style={{
              flex: 1, background: !aIsWinner ? `${COLORS.blue}15` : `${COLORS.dark}90`,
              border: !aIsWinner ? `2px solid ${COLORS.blue}60` : `1px solid ${COLORS.border}`,
              borderRadius: 8, padding: 10, textAlign: 'center',
            }}>
              <p style={{ color: COLORS.blue, fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1 }}>Peleador B</p>
              <p style={{ color: !aIsWinner ? '#fff' : COLORS.muted, fontSize: 13, fontWeight: 800, marginTop: 2 }}>{b.name}</p>
              <p style={{ color: COLORS.muted, fontSize: 10 }}>{b.record}</p>
              <p style={{ color: !aIsWinner ? COLORS.blue : COLORS.muted, fontSize: 18, fontWeight: 800, marginTop: 4 }}>{probB}%</p>
              <div style={{ fontSize: 9, color: COLORS.muted, marginTop: 4, lineHeight: 1.6 }}>
                <span>{formatHeight(b.height)} · {b.reach ? b.reach + '"' : '--'} · {b.weight ? b.weight + 'lb' : '--'}</span>
              </div>
            </div>
          </div>

          {/* Prob bar */}
          <ProbBar pctA={probA} pctB={probB} height={10} />
        </div>

        {/* Vertical divider */}
        <div style={{ width: 1, background: COLORS.border }} />

        {/* RIGHT: Method + Finish + Round */}
        <div style={{ flex: 0.9, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Method */}
          <div style={{ background: `${COLORS.card}cc`, border: `1px solid ${COLORS.border}`, borderRadius: 10, padding: '12px 14px' }}>
            <p style={{ color: COLORS.muted, fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 8 }}>
              Metodo de victoria
            </p>
            <MethodBars fontSize={12} barHeight={12} />
          </div>

          {/* Finish + Round side by side */}
          <div style={{ display: 'flex', gap: 10, flex: 1 }}>
            <div style={{
              flex: 1, background: `${COLORS.card}cc`, border: `1px solid ${COLORS.border}`,
              borderRadius: 10, padding: '12px 14px',
            }}>
              <p style={{ color: COLORS.muted, fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 8 }}>
                Finish vs Dec
              </p>
              <FinishDonut size={70} />
            </div>

            {prediction.goes_to_decision.finish > 0.35 && (
              <div style={{
                flex: 1, background: `${COLORS.card}cc`, border: `1px solid ${COLORS.border}`,
                borderRadius: 10, padding: '12px 14px',
              }}>
                <p style={{ color: COLORS.muted, fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 8 }}>
                  Round
                </p>
                <RoundBars barHeight={50} fontSize={10} />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{ marginTop: 'auto', paddingTop: 8 }}>
        <div style={{ height: 1, background: COLORS.border, marginBottom: 8 }} />
        <Watermark fontSize={11} />
      </div>
    </div>
  );

  // ─── UI: Modal with preview + download ───
  if (!isAdmin) return null;

  return (
    <>
      {/* Trigger Button */}
      <button
        onClick={() => setShowModal(true)}
        className="flex items-center gap-2 px-4 py-2 bg-ufc-border hover:bg-ufc-muted/30 text-ufc-text text-sm font-medium rounded-lg transition-all duration-200 hover:scale-105 active:scale-95"
        title="Generar imagen para redes sociales"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        Compartir
      </button>

      {/* Offscreen full-size card for html2canvas capture (no transform, no scale) */}
      {showModal && (
        <div
          ref={cardRef}
          style={{
            position: 'fixed',
            left: '-9999px',
            top: 0,
            zIndex: -1,
            pointerEvents: 'none',
          }}
        >
          {format === 'vertical' ? <VerticalCard /> : <HorizontalCard />}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-auto"
          onClick={(e) => { if (e.target === e.currentTarget) setShowModal(false); }}
        >
          <div className="bg-ufc-gray border border-ufc-border rounded-2xl p-6 max-w-[95vw] max-h-[95vh] overflow-auto animate-fadeIn">
            {/* Modal Header */}
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-bold text-white">Generar imagen para redes</h3>
              <button
                onClick={() => setShowModal(false)}
                className="p-1.5 rounded-lg hover:bg-ufc-border/50 text-ufc-muted hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Format Toggle */}
            <div className="flex gap-2 mb-5">
              <button
                onClick={() => setFormat('vertical')}
                className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${format === 'vertical'
                    ? 'bg-ufc-red text-white'
                    : 'bg-ufc-border/50 text-ufc-muted hover:text-white'
                  }`}
              >
                📱 Vertical (IG Story)
              </button>
              <button
                onClick={() => setFormat('horizontal')}
                className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${format === 'horizontal'
                    ? 'bg-ufc-red text-white'
                    : 'bg-ufc-border/50 text-ufc-muted hover:text-white'
                  }`}
              >
                🖥️ Horizontal (Twitter)
              </button>
            </div>

            {/* Visible preview (CSS-only scale, no ref) */}
            <div className="mb-5 rounded-xl overflow-hidden border border-ufc-border bg-ufc-dark flex justify-center">
              <div style={{
                transform: format === 'vertical' ? 'scale(0.22)' : 'scale(0.45)',
                transformOrigin: 'top center',
                height: format === 'vertical' ? 1920 * 0.22 : 675 * 0.45,
                width: format === 'vertical' ? 1080 * 0.22 : 1200 * 0.45,
              }}>
                {format === 'vertical' ? <VerticalCard /> : <HorizontalCard />}
              </div>
            </div>

            {/* Download Button */}
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="w-full btn-primary text-base py-3"
            >
              {generating ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Generando imagen...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Descargar PNG ({format === 'vertical' ? '1080×1920' : '1200×675'})
                </span>
              )}
            </button>

            <p className="text-center text-ufc-muted text-xs mt-3">
              La imagen se genera a 2x resolución para máxima calidad
            </p>
          </div>
        </div>
      )}
    </>
  );
}
