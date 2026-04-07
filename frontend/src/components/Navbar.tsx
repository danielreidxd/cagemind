import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function Navbar() {
  const location = useLocation();
  const isActive = (path: string) => location.pathname === path;
  const [menuOpen, setMenuOpen] = useState(false);
  const { user, isAdmin, logout } = useAuth();

  const navLink = (path: string, label: string, mobile = false) => (
    <Link to={path}
      onClick={() => setMenuOpen(false)}
      className={
        (mobile ? 'block w-full px-4 py-3 text-[13px] ' : 'px-3.5 py-1.5 text-[12px] ') +
        'rounded-md font-medium transition-all duration-150 tracking-wide ' +
        (isActive(path)
          ? 'bg-ufc-red text-white'
          : 'text-ufc-muted hover:text-ufc-text hover:bg-ufc-card')
      }>
      {label}
    </Link>
  );

  return (
    <nav className="bg-ufc-surface border-b border-ufc-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-[52px]">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5" onClick={() => setMenuOpen(false)}>
            <svg width="24" height="24" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
              <polygon points="50,5 93,27.5 93,72.5 50,95 7,72.5 7,27.5" fill="none" stroke="#B91C1C" strokeWidth="4"/>
              <polygon points="50,20 76,35 76,65 50,80 24,65 24,35" fill="none" stroke="#C9A227" strokeWidth="1.5" opacity="0.4"/>
              <circle cx="38" cy="38" r="2.5" fill="#B91C1C"/>
              <circle cx="62" cy="38" r="2.5" fill="#B91C1C"/>
              <circle cx="50" cy="50" r="3" fill="#C9A227"/>
              <circle cx="38" cy="62" r="2.5" fill="#B91C1C"/>
              <circle cx="62" cy="62" r="2.5" fill="#B91C1C"/>
              <line x1="38" y1="38" x2="50" y2="50" stroke="#B91C1C" strokeWidth="0.8" opacity="0.4"/>
              <line x1="62" y1="38" x2="50" y2="50" stroke="#B91C1C" strokeWidth="0.8" opacity="0.4"/>
              <line x1="38" y1="62" x2="50" y2="50" stroke="#B91C1C" strokeWidth="0.8" opacity="0.4"/>
              <line x1="62" y1="62" x2="50" y2="50" stroke="#B91C1C" strokeWidth="0.8" opacity="0.4"/>
            </svg>
            <span className="font-bold text-[15px] tracking-[1.5px]">
              <span className="text-ufc-red-light">CAGE</span><span className="text-ufc-gold">MIND</span>
            </span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-0.5">
            {navLink("/", "Proximamente")}
            {navLink("/historico", "Historico")}
            {navLink("/sandbox", "Sandbox")}
            {navLink("/stats", "Stats")}
            {navLink("/leaderboard", "Ranking")}
            {isAdmin && navLink("/admin", "Admin")}

            {user ? (
              <div className="flex items-center gap-2 ml-3 pl-3 border-l border-ufc-border">
                <span className="text-[11px] text-ufc-muted">{user.username}</span>
                <button onClick={logout} className="text-[11px] text-ufc-muted hover:text-white transition-colors">
                  Salir
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-1 ml-3 pl-3 border-l border-ufc-border">
                <Link to="/login" className="px-3 py-1.5 text-[11px] text-ufc-muted hover:text-white transition-colors">
                  Login
                </Link>
                <Link to="/register" className="px-3 py-1.5 text-[11px] bg-ufc-gold/10 text-ufc-gold rounded-md hover:bg-ufc-gold/20 transition-colors font-medium">
                  Registro
                </Link>
              </div>
            )}
          </div>

          {/* Hamburger */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden p-2 rounded-md text-ufc-muted hover:text-white hover:bg-ufc-card transition-colors"
          >
            {menuOpen ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-ufc-border bg-ufc-surface px-4 py-3 space-y-1">
          {navLink("/", "Proximamente", true)}
          {navLink("/historico", "Historico", true)}
          {navLink("/sandbox", "Sandbox", true)}
          {navLink("/stats", "Stats", true)}
          {navLink("/leaderboard", "Ranking", true)}
          {isAdmin && navLink("/admin", "Admin", true)}
          {user ? (
            <div className="pt-2 mt-2 border-t border-ufc-border flex items-center justify-between px-4">
              <span className="text-[12px] text-ufc-muted">{user.username}</span>
              <button onClick={() => { logout(); setMenuOpen(false); }} className="text-[12px] text-ufc-red-light">Salir</button>
            </div>
          ) : (
            <div className="pt-2 mt-2 border-t border-ufc-border flex gap-2 px-4">
              <Link to="/login" onClick={() => setMenuOpen(false)} className="flex-1 text-center py-2 text-[12px] text-ufc-muted hover:text-white rounded-md hover:bg-ufc-card">Login</Link>
              <Link to="/register" onClick={() => setMenuOpen(false)} className="flex-1 text-center py-2 text-[12px] text-ufc-gold bg-ufc-gold/10 rounded-md font-medium">Registro</Link>
            </div>
          )}
        </div>
      )}
    </nav>
  );
}