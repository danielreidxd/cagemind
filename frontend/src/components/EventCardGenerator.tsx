import { useState, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';

interface FightPrediction {
  predicted_winner: string;
  prob_a: number;
  prob_b: number;
  confidence: number;
  method_prediction: Record<string, number>;
}

interface EventFight {
  fighter_a: string;
  fighter_b: string;
  weight_class: string | null;
  prediction: FightPrediction | null;
  winner?: string | null;
  method?: string | null;
  round?: number | null;
}

interface Props {
  eventName: string;
  eventDate: string;
  location?: string | null;
  fights: EventFight[];
  totalFights: number;
  predictedFights: number;
}

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

const C = {
  bg: '#0D0D0D',
  card: '#1C1C3A',
  border: '#2A2A4A',
  red: '#C8102E',
  gold: '#D4AF37',
  blue: '#378ADD',
  text: '#E0E0E0',
  muted: '#8888AA',
  dark: '#111118',
};

export default function EventCardGenerator({ eventName, eventDate, location, fights, totalFights, predictedFights }: Props) {
  const [generating, setGenerating] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  const CARD_W = 1080;
  const ROW_H = 56;
  const ROW_GAP = 6;
  const CARD_H = 48 + 140 + (fights.length * (ROW_H + ROW_GAP)) + 60 + 32;

  const handleGenerate = useCallback(async () => {
    if (!cardRef.current) return;
    setGenerating(true);
    try {
      const html2canvas = (await import('html2canvas')).default;
      const canvas = await html2canvas(cardRef.current, {
        backgroundColor: C.bg,
        scale: 2,
        useCORS: true,
        logging: false,
      });
      const link = document.createElement('a');
      const safeName = eventName.replace(/[^a-zA-Z0-9]/g, '_');
      link.download = `CageMind_${safeName}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (err) {
      console.error('Error generating event card:', err);
    } finally {
      setGenerating(false);
    }
  }, [eventName]);

  const previewScale = Math.min(1, 840 / CARD_W);

  // ─── The card rendered at 1080px real size ───
  const EventCard = () => (
    <div
      style={{
        width: CARD_W,
        minHeight: CARD_H,
        backgroundColor: C.bg,
        fontFamily: 'Inter, system-ui, sans-serif',
        color: C.text,
        padding: '48px 56px 32px',
        boxSizing: 'border-box' as const,
      }}
    >
      {/* ── Logo bar ── */}
      <table style={{ width: '100%', borderCollapse: 'collapse' as const, marginBottom: 16 }}>
        <tbody>
          <tr>
            <td style={{ verticalAlign: 'middle' }}>
              <img src={LOGO_SVG} alt="" width={36} height={36} style={{ verticalAlign: 'middle', marginRight: 10 }} />
              <span style={{ fontWeight: 800, fontSize: 20, letterSpacing: 0.5, verticalAlign: 'middle' }}>
                <span style={{ color: C.red }}>CAGE</span>
                <span style={{ color: C.gold }}>MIND</span>
              </span>
            </td>
            <td style={{ verticalAlign: 'middle', textAlign: 'right' as const }}>
              <span style={{ color: C.muted, fontSize: 13 }}>ML Predictions</span>
            </td>
          </tr>
        </tbody>
      </table>

      {/* Divider */}
      <div style={{ height: 1, backgroundColor: C.border, marginBottom: 20 }} />

      {/* ── Event info box ── */}
      <table style={{
        width: '100%', borderCollapse: 'collapse' as const,
        backgroundColor: C.card, borderRadius: 14,
        marginBottom: 20, border: `1px solid ${C.border}`,
      }}>
        <tbody>
          <tr>
            <td style={{ padding: '20px 28px', verticalAlign: 'middle' }}>
              <div style={{ color: '#fff', fontSize: 26, fontWeight: 900, lineHeight: 1.2, marginBottom: 6, whiteSpace: 'normal' as const, wordSpacing: '4px' }}>
                {eventName}
              </div>
              <div style={{ color: C.muted, fontSize: 14 }}>
                {eventDate}{location ? ` \u00B7 ${location}` : ''}
              </div>
            </td>
            <td style={{ padding: '20px 28px', verticalAlign: 'middle', textAlign: 'right' as const, whiteSpace: 'nowrap' as const }}>
              <span style={{
                color: C.gold, fontSize: 13, fontWeight: 700,
                backgroundColor: C.dark, padding: '8px 16px', borderRadius: 8,
              }}>
                {totalFights} peleas &middot; {predictedFights} predicciones
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      {/* ── Fight rows ── */}
      {fights.map((fight, idx) => {
        const pred = fight.prediction;
        const probA = pred ? Math.round(pred.prob_a * 100) : null;
        const probB = pred ? Math.round(pred.prob_b * 100) : null;
        const aWins = pred ? pred.prob_a > pred.prob_b : false;

        return (
          <table
            key={idx}
            style={{
              width: '100%',
              borderCollapse: 'collapse' as const,
              backgroundColor: C.card,
              border: `1px solid ${pred ? C.border : `${C.border}60`}`,
              borderRadius: 10,
              marginBottom: ROW_GAP,
              opacity: pred ? 1 : 0.5,
              height: ROW_H,
              tableLayout: 'fixed' as const,
            }}
          >
            <tbody>
              <tr>
                {/* Dot */}
                <td style={{ width: 50, textAlign: 'center' as const, verticalAlign: 'middle' }}>
                  <div style={{
                    width: 10, height: 10, borderRadius: '50%',
                    backgroundColor: pred ? C.gold : C.border,
                    display: 'inline-block',
                  }} />
                </td>

                {/* Fighter A name */}
                <td style={{
                  width: '32%', textAlign: 'right' as const, verticalAlign: 'middle',
                  padding: '0 6px',
                  color: pred && aWins ? '#fff' : C.muted,
                  fontSize: 15, fontWeight: pred && aWins ? 700 : 500,
                  whiteSpace: 'nowrap' as const, overflow: 'hidden' as const,
                  textOverflow: 'ellipsis' as const,
                  wordSpacing: '3px',
                }}>
                  {fight.fighter_a}
                </td>

                {/* Prob A */}
                <td style={{
                  width: 50, textAlign: 'right' as const, verticalAlign: 'middle',
                  color: aWins ? C.gold : C.muted,
                  fontSize: 13, fontWeight: 700,
                  padding: '0 4px',
                }}>
                  {probA !== null ? `${probA}%` : ''}
                </td>

                {/* VS + weight class */}
                <td style={{
                  width: 110, textAlign: 'center' as const, verticalAlign: 'middle',
                  padding: '0 4px',
                }}>
                  <div style={{ color: C.muted, fontSize: 12, fontWeight: 600, lineHeight: 1.2 }}>vs</div>
                  {fight.weight_class && (
                    <div style={{ color: `${C.muted}80`, fontSize: 9, lineHeight: 1.2 }}>{fight.weight_class}</div>
                  )}
                </td>

                {/* Prob B */}
                <td style={{
                  width: 50, textAlign: 'left' as const, verticalAlign: 'middle',
                  color: !aWins ? C.gold : C.muted,
                  fontSize: 13, fontWeight: 700,
                  padding: '0 4px',
                }}>
                  {probB !== null ? `${probB}%` : ''}
                </td>

                {/* Fighter B name */}
                <td style={{
                  width: '32%', textAlign: 'left' as const, verticalAlign: 'middle',
                  padding: '0 6px',
                  color: pred && !aWins ? '#fff' : C.muted,
                  fontSize: 15, fontWeight: pred && !aWins ? 700 : 500,
                  whiteSpace: 'nowrap' as const, overflow: 'hidden' as const,
                  textOverflow: 'ellipsis' as const,
                  wordSpacing: '3px',
                }}>
                  {fight.fighter_b}
                </td>
              </tr>
            </tbody>
          </table>
        );
      })}

      {/* ── Footer ── */}
      <div style={{ height: 1, backgroundColor: C.border, marginTop: 16, marginBottom: 12 }} />
      <table style={{ width: '100%', borderCollapse: 'collapse' as const }}>
        <tbody>
          <tr>
            <td style={{ textAlign: 'center' as const, opacity: 0.5, verticalAlign: 'middle' }}>
              <img src={LOGO_SVG} alt="" width={14} height={14} style={{ verticalAlign: 'middle', marginRight: 6 }} />
              <span style={{ color: C.muted, fontSize: 12, letterSpacing: 0.5, verticalAlign: 'middle' }}>
                cagemind.app &middot; ML Predictions
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );

  // ─── Modal rendered via portal to document.body ───
  const modal = showModal ? createPortal(
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 999999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(0,0,0,0.88)',
        backdropFilter: 'blur(4px)',
        padding: 24,
      }}
      onClick={(e) => { if (e.target === e.currentTarget) setShowModal(false); }}
    >
      <div
        style={{
          backgroundColor: '#1A1A2E',
          border: '1px solid #2A2A4A',
          borderRadius: 16,
          padding: 24,
          width: '80vw',
          maxWidth: 920,
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column' as const,
        }}
        className="animate-fadeIn"
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexShrink: 0 }}>
          <h3 style={{ color: '#fff', fontSize: 18, fontWeight: 700, margin: 0 }}>{eventName}</h3>
          <button
            onClick={() => setShowModal(false)}
            style={{
              background: 'none', border: 'none', color: C.muted, cursor: 'pointer',
              padding: 6, borderRadius: 8, fontSize: 20, lineHeight: 1,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#fff')}
            onMouseLeave={(e) => (e.currentTarget.style.color = C.muted)}
          >
            ✕
          </button>
        </div>

        {/* Preview — scrollable */}
        <div style={{
          flex: 1, minHeight: 0, overflow: 'auto',
          borderRadius: 12, border: `1px solid ${C.border}`,
          backgroundColor: C.bg, marginBottom: 16,
        }}>
          <div style={{
            transform: `scale(${previewScale})`,
            transformOrigin: 'top left',
            width: CARD_W,
            height: CARD_H,
          }}>
            <div ref={cardRef}>
              <EventCard />
            </div>
          </div>
        </div>

        {/* Download */}
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="btn-primary"
          style={{ width: '100%', padding: '14px 0', fontSize: 15, flexShrink: 0 }}
        >
          {generating ? 'Generando imagen...' : `Descargar PNG (1080×${CARD_H} · 2x)`}
        </button>
      </div>
    </div>,
    document.body,
  ) : null;

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className="flex items-center gap-2 px-4 py-2 bg-ufc-border hover:bg-ufc-muted/30 text-ufc-text text-sm font-medium rounded-lg transition-all duration-200 hover:scale-105 active:scale-95"
        title="Descargar imagen de la cartelera completa"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        Descargar cartelera
      </button>
      {modal}
    </>
  );
}