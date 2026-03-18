import { useState, useEffect } from 'react';

interface Props {
  onFinish: () => void;
  duration?: number;
}

export default function LoadingScreen({ onFinish, duration = 5000 }: Props) {
  const [fadeOut, setFadeOut] = useState(false);

  useEffect(() => {
    const fadeTimer = setTimeout(() => setFadeOut(true), duration - 600);
    const endTimer = setTimeout(() => onFinish(), duration);
    return () => { clearTimeout(fadeTimer); clearTimeout(endTimer); };
  }, [onFinish, duration]);

  return (
    <div
      className={`fixed inset-0 z-[100] bg-[#0D0D0D] flex items-center justify-center transition-opacity duration-500 ${fadeOut ? 'opacity-0' : 'opacity-100'}`}
    >
      <svg width="748" height="924" viewBox="0 0 680 420" xmlns="http://www.w3.org/2000/svg">
        <style>{`
          @keyframes drawCage { from { stroke-dashoffset: 600; } to { stroke-dashoffset: 0; } }
          @keyframes drawCage2 { from { stroke-dashoffset: 500; } to { stroke-dashoffset: 0; } }
          @keyframes drawCage3 { from { stroke-dashoffset: 400; } to { stroke-dashoffset: 0; } }
          @keyframes drawBrain { from { stroke-dashoffset: 400; } to { stroke-dashoffset: 0; } }
          @keyframes nodeIn { 0% { r: 0; opacity: 0; } 60% { r: 4.5; opacity: 1; } 100% { r: 3; opacity: 0.9; } }
          @keyframes nodeCenter { 0% { r: 0; opacity: 0; } 50% { r: 6; opacity: 1; } 100% { r: 3.5; opacity: 1; } }
          @keyframes lineIn { from { opacity: 0; } to { opacity: 0.35; } }
          @keyframes textSlide { from { opacity: 0; letter-spacing: 20px; } to { opacity: 1; letter-spacing: 12px; } }
          @keyframes subIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
          @keyframes pulseNode { 0%,100% { opacity: 0.7; } 50% { opacity: 1; } }
          @keyframes pulseGlow { 0%,100% { opacity: 0.05; } 50% { opacity: 0.15; } }
          @keyframes connPulse { 0% { stroke-dashoffset: 20; } 100% { stroke-dashoffset: 0; } }
          .cage1 { stroke-dasharray: 600; stroke-dashoffset: 600; animation: drawCage 1.2s ease-out 0s forwards; }
          .cage2 { stroke-dasharray: 500; stroke-dashoffset: 500; animation: drawCage2 1s ease-out 0.3s forwards; opacity: 0.4; }
          .cage3 { stroke-dasharray: 400; stroke-dashoffset: 400; animation: drawCage3 0.8s ease-out 0.6s forwards; opacity: 0.3; }
          .cstrut { opacity: 0; animation: lineIn 0.3s ease-out 1s forwards; }
          .brain { stroke-dasharray: 400; stroke-dashoffset: 400; animation: drawBrain 1.5s ease-in-out 1.2s forwards; }
          .bfold { stroke-dasharray: 100; stroke-dashoffset: 100; animation: drawBrain 0.8s ease-in-out 1.8s forwards; opacity: 0.6; }
          .n1 { animation: nodeIn 0.4s ease-out 2.0s forwards; r: 0; opacity: 0; }
          .n2 { animation: nodeIn 0.4s ease-out 2.1s forwards; r: 0; opacity: 0; }
          .n3 { animation: nodeIn 0.4s ease-out 2.2s forwards; r: 0; opacity: 0; }
          .n4 { animation: nodeIn 0.4s ease-out 2.3s forwards; r: 0; opacity: 0; }
          .n5 { animation: nodeIn 0.4s ease-out 2.4s forwards; r: 0; opacity: 0; }
          .n6 { animation: nodeIn 0.4s ease-out 2.5s forwards; r: 0; opacity: 0; }
          .n7 { animation: nodeIn 0.4s ease-out 2.6s forwards; r: 0; opacity: 0; }
          .n8 { animation: nodeIn 0.4s ease-out 2.7s forwards; r: 0; opacity: 0; }
          .nc { animation: nodeCenter 0.6s ease-out 2.8s forwards; r: 0; opacity: 0; }
          .n10 { animation: nodeIn 0.4s ease-out 2.9s forwards; r: 0; opacity: 0; }
          .conn { opacity: 0; animation: lineIn 0.3s ease-out 3.0s forwards; }
          .connG { opacity: 0; animation: lineIn 0.5s ease-out 3.1s forwards; }
          .txt { opacity: 0; animation: textSlide 0.8s ease-out 3.2s forwards; }
          .sub1 { opacity: 0; animation: subIn 0.6s ease-out 3.6s forwards; }
          .sub2 { opacity: 0; animation: subIn 0.6s ease-out 3.9s forwards; }
          .ln { opacity: 0; animation: lineIn 0.4s ease-out 3.8s forwards; }
          .pulse-n { animation: pulseNode 2s ease-in-out 4.2s infinite; }
          .pulse-g { animation: pulseGlow 3s ease-in-out 4.2s infinite; }
          .conn-p { stroke-dasharray: 5 5; animation: connPulse 1.5s linear 4.2s infinite; }
        `}</style>

        <g transform="translate(340, 155)">
          <polygon points="0,-90 78,-45 78,45 0,90 -78,45 -78,-45" fill="none" stroke="#C8102E" strokeWidth="3" className="cage1"/>
          <polygon points="0,-70 60.6,-35 60.6,35 0,70 -60.6,35 -60.6,-35" fill="none" stroke="#C8102E" strokeWidth="1.5" className="cage2"/>
          <polygon points="0,-50 43.3,-25 43.3,25 0,50 -43.3,25 -43.3,-25" fill="none" stroke="#D4AF37" strokeWidth="1" className="cage3"/>

          <line x1="0" y1="-90" x2="0" y2="-70" stroke="#C8102E" strokeWidth="0.8" className="cstrut"/>
          <line x1="78" y1="-45" x2="60.6" y2="-35" stroke="#C8102E" strokeWidth="0.8" className="cstrut"/>
          <line x1="78" y1="45" x2="60.6" y2="35" stroke="#C8102E" strokeWidth="0.8" className="cstrut"/>
          <line x1="0" y1="90" x2="0" y2="70" stroke="#C8102E" strokeWidth="0.8" className="cstrut"/>
          <line x1="-78" y1="45" x2="-60.6" y2="35" stroke="#C8102E" strokeWidth="0.8" className="cstrut"/>
          <line x1="-78" y1="-45" x2="-60.6" y2="-35" stroke="#C8102E" strokeWidth="0.8" className="cstrut"/>

          <path d="M-28,-20 Q-30,-35 -18,-38 Q-5,-42 5,-35 Q15,-28 22,-32 Q32,-36 35,-25 Q38,-14 30,-8 Q22,-2 28,8 Q34,18 25,25 Q16,32 5,28 Q-5,24 -15,30 Q-25,36 -30,25 Q-35,14 -28,5 Q-21,-4 -28,-20 Z" fill="none" stroke="#D4AF37" strokeWidth="2" className="brain"/>
          <path d="M-15,-25 Q-8,-30 0,-22" fill="none" stroke="#D4AF37" strokeWidth="1.2" className="bfold"/>
          <path d="M10,-28 Q18,-20 12,-12" fill="none" stroke="#D4AF37" strokeWidth="1.2" className="bfold"/>
          <path d="M22,-5 Q28,5 20,12" fill="none" stroke="#D4AF37" strokeWidth="1.2" className="bfold"/>
          <path d="M-22,0 Q-28,10 -20,18" fill="none" stroke="#D4AF37" strokeWidth="1.2" className="bfold"/>
          <path d="M-5,5 Q5,0 8,10 Q11,20 0,18" fill="none" stroke="#D4AF37" strokeWidth="1" className="bfold"/>

          <circle cx="-18" cy="-30" fill="#C8102E" className="n1 pulse-n"/>
          <circle cx="8" cy="-32" fill="#C8102E" className="n2 pulse-n"/>
          <circle cx="28" cy="-18" fill="#C8102E" className="n3 pulse-n"/>
          <circle cx="30" cy="8" fill="#C8102E" className="n4 pulse-n"/>
          <circle cx="15" cy="28" fill="#C8102E" className="n5 pulse-n"/>
          <circle cx="-10" cy="26" fill="#C8102E" className="n6 pulse-n"/>
          <circle cx="-28" cy="10" fill="#C8102E" className="n7 pulse-n"/>
          <circle cx="-25" cy="-15" fill="#C8102E" className="n8 pulse-n"/>
          <circle cx="0" cy="-10" fill="#C8102E" className="nc pulse-n"/>
          <circle cx="5" cy="12" fill="#C8102E" className="n10 pulse-n"/>

          <line x1="-18" y1="-30" x2="0" y2="-10" stroke="#C8102E" strokeWidth="0.6" className="conn conn-p"/>
          <line x1="8" y1="-32" x2="0" y2="-10" stroke="#C8102E" strokeWidth="0.6" className="conn conn-p"/>
          <line x1="28" y1="-18" x2="0" y2="-10" stroke="#C8102E" strokeWidth="0.6" className="conn conn-p"/>
          <line x1="30" y1="8" x2="5" y2="12" stroke="#C8102E" strokeWidth="0.6" className="conn conn-p"/>
          <line x1="15" y1="28" x2="5" y2="12" stroke="#C8102E" strokeWidth="0.6" className="conn conn-p"/>
          <line x1="-10" y1="26" x2="5" y2="12" stroke="#C8102E" strokeWidth="0.6" className="conn conn-p"/>
          <line x1="-28" y1="10" x2="0" y2="-10" stroke="#C8102E" strokeWidth="0.6" className="conn conn-p"/>
          <line x1="-25" y1="-15" x2="0" y2="-10" stroke="#C8102E" strokeWidth="0.6" className="conn conn-p"/>
          <line x1="0" y1="-10" x2="5" y2="12" stroke="#D4AF37" strokeWidth="0.8" className="connG conn-p"/>

          <circle cx="0" cy="-10" r="18" fill="#D4AF37" opacity="0" className="pulse-g"/>
        </g>

        <text x="340" y="295" textAnchor="middle" fontFamily="Inter, Helvetica Neue, sans-serif" fontSize="44" fontWeight="800" className="txt">
          <tspan fill="#C8102E">CAGE</tspan><tspan fill="#D4AF37" dx="6">MIND</tspan>
        </text>
        <text x="340" y="325" textAnchor="middle" fontFamily="Inter, Helvetica Neue, sans-serif" fontSize="13" fontWeight="400" letterSpacing="8" fill="#8888AA" className="sub1">MMA FIGHT INTELLIGENCE</text>
        <line x1="240" y1="345" x2="440" y2="345" stroke="#C8102E" strokeWidth="0.5" className="ln"/>
        <text x="340" y="368" textAnchor="middle" fontFamily="Inter, Helvetica Neue, sans-serif" fontSize="11" fontWeight="400" letterSpacing="4" fill="#666677" className="sub2">MACHINE LEARNING PREDICTIONS</text>
      </svg>
    </div>
  );
}
