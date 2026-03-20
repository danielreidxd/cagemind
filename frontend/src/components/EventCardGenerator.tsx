import { useState, useRef, useCallback, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useAuth } from '../contexts/AuthContext';

interface FightPrediction {
  predicted_winner: string;
  prob_a: number;
  prob_b: number;
  confidence: string | number;
  confidence_score?: number;
  method_prediction: Record<string, number>;
}

interface EventFight {
  fighter_a: string;
  fighter_b: string;
  weight_class: string | null;
  prediction: FightPrediction | null;
}

interface Props {
  eventName: string;
  eventDate: string;
  location?: string | null;
  fights: EventFight[];
  totalFights: number;
  predictedFights: number;
}

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
  white: '#FFFFFF',
};

// ─── Draw the entire card onto a canvas ───
function drawCard(
  canvas: HTMLCanvasElement,
  eventName: string,
  eventDate: string,
  location: string | null | undefined,
  fights: EventFight[],
  totalFights: number,
  predictedFights: number,
) {
  const SCALE = 2; // 2x for retina
  const W = 1080;
  const PAD_X = 56;
  const ROW_H = 58;
  const ROW_GAP = 6;
  const HEADER_BLOCK = 190;
  const FOOTER_BLOCK = 70;
  const TOP_BAR = 80;
  const H = TOP_BAR + HEADER_BLOCK + fights.length * (ROW_H + ROW_GAP) + FOOTER_BLOCK;

  canvas.width = W * SCALE;
  canvas.height = H * SCALE;
  canvas.style.width = W + 'px';
  canvas.style.height = H + 'px';

  const ctx = canvas.getContext('2d')!;
  ctx.scale(SCALE, SCALE);

  // ── Helpers ──
  const roundRect = (x: number, y: number, w: number, h: number, r: number) => {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  };

  const fillRoundRect = (x: number, y: number, w: number, h: number, r: number, color: string) => {
    ctx.fillStyle = color;
    roundRect(x, y, w, h, r);
    ctx.fill();
  };

  const strokeRoundRect = (x: number, y: number, w: number, h: number, r: number, color: string, lineW = 1) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = lineW;
    roundRect(x, y, w, h, r);
    ctx.stroke();
  };

  const drawCircle = (cx: number, cy: number, r: number, color: string) => {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fill();
  };

  const truncText = (text: string, maxW: number): string => {
    if (ctx.measureText(text).width <= maxW) return text;
    let t = text;
    while (t.length > 0 && ctx.measureText(t + '…').width > maxW) {
      t = t.slice(0, -1);
    }
    return t + '…';
  };

  // ── Background ──
  ctx.fillStyle = C.bg;
  ctx.fillRect(0, 0, W, H);

  // ── Logo bar ──
  let y = 40;

  // Draw octagon logo (simplified)
  const logoX = PAD_X;
  const logoY = y - 12;
  const logoS = 32;
  ctx.strokeStyle = C.red;
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 2;
    const px = logoX + logoS / 2 + (logoS / 2) * Math.cos(angle);
    const py = logoY + logoS / 2 + (logoS / 2) * Math.sin(angle);
    if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
  }
  ctx.closePath();
  ctx.stroke();

  // Inner hexagon
  ctx.strokeStyle = C.gold;
  ctx.lineWidth = 1;
  ctx.globalAlpha = 0.5;
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 2;
    const px = logoX + logoS / 2 + (logoS / 3) * Math.cos(angle);
    const py = logoY + logoS / 2 + (logoS / 3) * Math.sin(angle);
    if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
  }
  ctx.closePath();
  ctx.stroke();
  ctx.globalAlpha = 1;

  // Center dot
  drawCircle(logoX + logoS / 2, logoY + logoS / 2, 3, C.gold);

  // CAGEMIND text
  ctx.font = '800 20px Inter, system-ui, sans-serif';
  ctx.fillStyle = C.red;
  ctx.textAlign = 'left';
  ctx.fillText('CAGE', logoX + logoS + 10, y + 2);
  const cageW = ctx.measureText('CAGE').width;
  ctx.fillStyle = C.gold;
  ctx.fillText('MIND', logoX + logoS + 10 + cageW, y + 2);

  // "ML Predictions" right side
  ctx.font = '400 13px Inter, system-ui, sans-serif';
  ctx.fillStyle = C.muted;
  ctx.textAlign = 'right';
  ctx.fillText('ML Predictions', W - PAD_X, y + 2);

  // Divider
  y += 24;
  ctx.fillStyle = C.border;
  ctx.fillRect(PAD_X, y, W - PAD_X * 2, 1);
  y += 20;

  // ── Event info box ──
  const boxH = 90;
  fillRoundRect(PAD_X, y, W - PAD_X * 2, boxH, 14, C.card);
  strokeRoundRect(PAD_X, y, W - PAD_X * 2, boxH, 14, C.border);

  // Event name
  ctx.font = '900 26px Inter, system-ui, sans-serif';
  ctx.fillStyle = C.white;
  ctx.textAlign = 'left';
  ctx.fillText(eventName, PAD_X + 28, y + 38);

  // Event date + location
  ctx.font = '400 14px Inter, system-ui, sans-serif';
  ctx.fillStyle = C.muted;
  const dateStr = eventDate + (location ? ` · ${location}` : '');
  ctx.fillText(dateStr, PAD_X + 28, y + 62);

  // Fights count badge
  const badgeText = `${totalFights} peleas · ${predictedFights} predicciones`;
  ctx.font = '700 13px Inter, system-ui, sans-serif';
  const badgeW = ctx.measureText(badgeText).width + 32;
  const badgeX = W - PAD_X - 28 - badgeW;
  const badgeY = y + (boxH - 34) / 2;
  fillRoundRect(badgeX, badgeY, badgeW, 34, 8, C.dark);
  ctx.fillStyle = C.gold;
  ctx.textAlign = 'center';
  ctx.fillText(badgeText, badgeX + badgeW / 2, badgeY + 22);

  y += boxH + 16;

  // ── Fight rows ──
  const contentW = W - PAD_X * 2;
  const dotCol = 40;
  const probCol = 54;
  const vsCol = 100;
  const nameCol = (contentW - dotCol - probCol * 2 - vsCol) / 2;

  fights.forEach((fight) => {
    const pred = fight.prediction;
    const probA = pred ? Math.round(pred.prob_a * 100) : null;
    const probB = pred ? Math.round(pred.prob_b * 100) : null;
    const aWins = pred ? pred.prob_a > pred.prob_b : false;
    const rowAlpha = pred ? 1 : 0.45;

    ctx.globalAlpha = rowAlpha;

    // Row background
    fillRoundRect(PAD_X, y, contentW, ROW_H, 10, C.card);
    strokeRoundRect(PAD_X, y, contentW, ROW_H, 10, C.border);

    const cy = y + ROW_H / 2;

    // Status dot
    drawCircle(PAD_X + dotCol / 2 + 8, cy, 5, pred ? C.gold : C.border);

    // Fighter A name (right aligned)
    const nameAx = PAD_X + dotCol + nameCol;
    ctx.font = pred && aWins ? '700 15px Inter, system-ui, sans-serif' : '500 15px Inter, system-ui, sans-serif';
    ctx.fillStyle = pred && aWins ? C.white : C.muted;
    ctx.textAlign = 'right';
    const nameA = truncText(fight.fighter_a, nameCol - 12);
    ctx.fillText(nameA, nameAx - 6, cy + 5);

    // Prob A
    if (probA !== null) {
      ctx.font = '700 13px Inter, system-ui, sans-serif';
      ctx.fillStyle = aWins ? C.gold : C.muted;
      ctx.textAlign = 'right';
      ctx.fillText(`${probA}%`, nameAx + probCol - 4, cy + 5);
    }

    // VS + weight class
    const vsCenterX = nameAx + probCol + vsCol / 2;
    ctx.font = '600 12px Inter, system-ui, sans-serif';
    ctx.fillStyle = C.muted;
    ctx.textAlign = 'center';
    ctx.fillText('vs', vsCenterX, cy + (fight.weight_class ? -1 : 4));
    if (fight.weight_class) {
      ctx.font = '400 9px Inter, system-ui, sans-serif';
      ctx.globalAlpha = rowAlpha * 0.6;
      ctx.fillText(fight.weight_class, vsCenterX, cy + 12);
      ctx.globalAlpha = rowAlpha;
    }

    // Prob B
    const probBx = nameAx + probCol + vsCol;
    if (probB !== null) {
      ctx.font = '700 13px Inter, system-ui, sans-serif';
      ctx.fillStyle = !aWins ? C.gold : C.muted;
      ctx.textAlign = 'left';
      ctx.fillText(`${probB}%`, probBx + 4, cy + 5);
    }

    // Fighter B name (left aligned)
    const nameBx = probBx + probCol;
    ctx.font = pred && !aWins ? '700 15px Inter, system-ui, sans-serif' : '500 15px Inter, system-ui, sans-serif';
    ctx.fillStyle = pred && !aWins ? C.white : C.muted;
    ctx.textAlign = 'left';
    const nameB = truncText(fight.fighter_b, nameCol - 12);
    ctx.fillText(nameB, nameBx + 6, cy + 5);

    ctx.globalAlpha = 1;
    y += ROW_H + ROW_GAP;
  });

  // ── Footer ──
  y += 8;
  ctx.fillStyle = C.border;
  ctx.fillRect(PAD_X, y, contentW, 1);
  y += 16;

  // Watermark
  ctx.globalAlpha = 0.5;
  ctx.font = '400 12px Inter, system-ui, sans-serif';
  ctx.fillStyle = C.muted;
  ctx.textAlign = 'center';
  ctx.fillText('cagemind.app · ML Predictions', W / 2, y + 4);

  // Small logo dot
  drawCircle(W / 2 - ctx.measureText('cagemind.app · ML Predictions').width / 2 - 14, y, 3, C.gold);
  ctx.globalAlpha = 1;

  return { width: W, height: H };
}

export default function EventCardGenerator({ eventName, eventDate, location, fights, totalFights, predictedFights }: Props) {
  const { isAdmin } = useAuth();
  const [generating, setGenerating] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const previewCanvasRef = useRef<HTMLCanvasElement>(null);
  const [cardDims, setCardDims] = useState({ width: 1080, height: 800 });

  // Draw preview when modal opens
  useEffect(() => {
    if (showModal && previewCanvasRef.current) {
      const dims = drawCard(previewCanvasRef.current, eventName, eventDate, location, fights, totalFights, predictedFights);
      setCardDims(dims);
    }
  }, [showModal, eventName, eventDate, location, fights, totalFights, predictedFights]);

  const handleGenerate = useCallback(() => {
    setGenerating(true);
    try {
      // Create a fresh offscreen canvas for download
      const offscreen = document.createElement('canvas');
      drawCard(offscreen, eventName, eventDate, location, fights, totalFights, predictedFights);

      const link = document.createElement('a');
      const safeName = eventName.replace(/[^a-zA-Z0-9]/g, '_');
      link.download = `CageMind_${safeName}.png`;
      link.href = offscreen.toDataURL('image/png');
      link.click();
    } catch (err) {
      console.error('Error generating event card:', err);
    } finally {
      setGenerating(false);
    }
  }, [eventName, eventDate, location, fights, totalFights, predictedFights]);

  const previewScale = Math.min(1, 840 / cardDims.width);

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

        {/* Canvas preview */}
        <div style={{
          flex: 1, minHeight: 0, overflow: 'auto',
          borderRadius: 12, border: `1px solid ${C.border}`,
          backgroundColor: C.bg, marginBottom: 16,
          display: 'flex', justifyContent: 'center',
        }}>
          <canvas
            ref={previewCanvasRef}
            style={{
              width: cardDims.width * previewScale,
              height: cardDims.height * previewScale,
              display: 'block',
            }}
          />
        </div>

        {/* Download */}
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="btn-primary"
          style={{ width: '100%', padding: '14px 0', fontSize: 15, flexShrink: 0 }}
        >
          {generating ? 'Generando imagen...' : `Descargar PNG (${cardDims.width}×${cardDims.height} · 2x)`}
        </button>
      </div>
    </div>,
    document.body,
  ) : null;

  if (!isAdmin) return null;

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