import { useState, useRef, useCallback } from 'react';

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
  // Historical fields (optional)
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

// ─── Logo SVG as data URI ───
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

  // Card dimensions: 1080 wide, height dynamic based on number of fights
  const CARD_W = 1080;
  const HEADER_H = 180;
  const FIGHT_ROW_H = 64;
  const FOOTER_H = 60;
  const PADDING_TOP = 40;
  const PADDING_BOTTOM = 24;
  const GAP = 8;
  const CARD_H = PADDING_TOP + HEADER_H + (fights.length * (FIGHT_ROW_H + GAP)) + FOOTER_H + PADDING_BOTTOM;

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
        width: cardRef.current.offsetWidth,
        height: cardRef.current.offsetHeight,
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

  // ─── The actual card rendered at real pixel size ───
  const EventCard = () => (
    <div style={{
      width: CARD_W,
      height: CARD_H,
      background: `linear-gradient(180deg, ${C.bg} 0%, #08081a 50%, ${C.bg} 100%)`,
      fontFamily: 'Inter, system-ui, sans-serif',
      color: C.text,
      padding: `${PADDING_TOP}px 48px ${PADDING_BOTTOM}px`,
      display: 'flex',
      flexDirection: 'column',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background octagon */}
      <div style={{
        position: 'absolute', top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        opacity: 0.025, pointerEvents: 'none',
      }}>
        <svg width="700" height="700" viewBox="0 0 100 100">
          <polygon points="50,5 93,27.5 93,72.5 50,95 7,72.5 7,27.5" fill="none" stroke="#fff" strokeWidth="1"/>
        </svg>
      </div>

      {/* ── Header ── */}
      <div style={{ marginBottom: 20 }}>
        {/* Top bar: logo + branding */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <img src={LOGO_SVG} alt="" width={36} height={36} />
            <span style={{ fontWeight: 800, fontSize: 20, letterSpacing: '0.5px' }}>
              <span style={{ color: C.red }}>CAGE</span>
              <span style={{ color: C.gold }}>MIND</span>
            </span>
          </div>
          <span style={{ color: C.muted, fontSize: 13 }}>ML Predictions</span>
        </div>

        {/* Divider */}
        <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.border}, transparent)`, marginBottom: 20 }} />

        {/* Event info */}
        <div style={{
          background: `linear-gradient(135deg, ${C.card}cc, ${C.dark}cc)`,
          border: `1px solid ${C.border}`,
          borderRadius: 14,
          padding: '20px 28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div>
            <h2 style={{ color: '#fff', fontSize: 28, fontWeight: 900, margin: 0, lineHeight: 1.2 }}>{eventName}</h2>
            <p style={{ color: C.muted, fontSize: 14, marginTop: 6 }}>
              {eventDate}{location ? ` · ${location}` : ''}
            </p>
          </div>
          <div style={{ textAlign: 'center' }}>
            <span style={{
              color: C.gold, fontSize: 15, fontWeight: 700,
              background: `${C.dark}80`, padding: '8px 16px', borderRadius: 8,
              display: 'inline-block',
            }}>
              {totalFights} peleas · {predictedFights} predicciones
            </span>
          </div>
        </div>
      </div>

      {/* ── Fight Rows ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: GAP, flex: 1 }}>
        {fights.map((fight, idx) => {
          const pred = fight.prediction;
          const probA = pred ? Math.round(pred.prob_a * 100) : null;
          const probB = pred ? Math.round(pred.prob_b * 100) : null;
          const aWins = pred ? pred.prob_a > pred.prob_b : false;

          return (
            <div key={idx} style={{
              height: FIGHT_ROW_H,
              background: `${C.card}99`,
              border: `1px solid ${pred ? C.border : `${C.border}60`}`,
              borderRadius: 10,
              display: 'flex',
              alignItems: 'center',
              padding: '0 24px',
              opacity: pred ? 1 : 0.5,
            }}>
              {/* Status dot */}
              <div style={{
                width: 10, height: 10, borderRadius: '50%',
                background: pred ? C.gold : C.border,
                marginRight: 16, flexShrink: 0,
              }} />

              {/* Fighter A side */}
              <div style={{ flex: 1, textAlign: 'right', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10 }}>
                <span style={{
                  color: pred && aWins ? '#fff' : C.muted,
                  fontSize: 15, fontWeight: pred && aWins ? 700 : 500,
                }}>
                  {fight.fighter_a}
                </span>
                {probA !== null && (
                  <span style={{
                    color: aWins ? C.gold : C.muted,
                    fontSize: 13, fontWeight: 700,
                    minWidth: 38,
                    textAlign: 'right',
                  }}>
                    {probA}%
                  </span>
                )}
              </div>

              {/* VS + Weight class */}
              <div style={{
                width: 120, textAlign: 'center', flexShrink: 0,
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1,
              }}>
                <span style={{ color: C.muted, fontSize: 12, fontWeight: 600 }}>vs</span>
                {fight.weight_class && (
                  <span style={{ color: `${C.muted}80`, fontSize: 10 }}>{fight.weight_class}</span>
                )}
              </div>

              {/* Fighter B side */}
              <div style={{ flex: 1, textAlign: 'left', display: 'flex', alignItems: 'center', gap: 10 }}>
                {probB !== null && (
                  <span style={{
                    color: !aWins ? C.gold : C.muted,
                    fontSize: 13, fontWeight: 700,
                    minWidth: 38,
                  }}>
                    {probB}%
                  </span>
                )}
                <span style={{
                  color: pred && !aWins ? '#fff' : C.muted,
                  fontSize: 15, fontWeight: pred && !aWins ? 700 : 500,
                }}>
                  {fight.fighter_b}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Footer ── */}
      <div style={{ paddingTop: 16, marginTop: 'auto' }}>
        <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.border}, transparent)`, marginBottom: 12 }} />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, opacity: 0.5 }}>
          <img src={LOGO_SVG} alt="" width={14} height={14} />
          <span style={{ color: C.muted, fontSize: 12, letterSpacing: 0.5 }}>
            cagemind.app · ML Predictions
          </span>
        </div>
      </div>
    </div>
  );

  // ─── Scale for preview ───
  const previewScale = Math.min(0.55, 540 / CARD_W);
  const previewW = CARD_W * previewScale;
  const previewH = CARD_H * previewScale;

  return (
    <>
      {/* Trigger Button */}
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

      {/* Modal */}
      {showModal && (
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-auto"
          onClick={(e) => { if (e.target === e.currentTarget) setShowModal(false); }}
        >
          <div className="bg-ufc-gray border border-ufc-border rounded-2xl p-6 w-[600px] max-w-[95vw] max-h-[90vh] overflow-auto animate-fadeIn">
            {/* Modal Header */}
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-bold text-white">Cartelera completa — {eventName}</h3>
              <button
                onClick={() => setShowModal(false)}
                className="p-1.5 rounded-lg hover:bg-ufc-border/50 text-ufc-muted hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Preview */}
            <div className="mb-5 rounded-xl overflow-hidden border border-ufc-border bg-ufc-dark flex justify-center"
              style={{ height: CARD_H * previewScale + 16 }}
            >
              <div style={{
                transform: `scale(${previewScale})`,
                transformOrigin: 'top center',
                width: CARD_W,
                height: CARD_H,
              }}>
                <div ref={cardRef}>
                  <EventCard />
                </div>
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
                  Descargar PNG (1080×{CARD_H} · 2x resolución)
                </span>
              )}
            </button>

            <p className="text-center text-ufc-muted text-xs mt-3">
              Imagen optimizada para compartir en redes sociales
            </p>
          </div>
        </div>
      )}
    </>
  );
}