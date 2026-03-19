import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function Navbar() {
  const location = useLocation();
  const isActive = (path: string) => location.pathname === path;
  const [menuOpen, setMenuOpen] = useState(false);
  const { isAdmin } = useAuth();

  const navLink = (path: string, label: string, mobile = false) => (
    <Link to={path}
      onClick={() => setMenuOpen(false)}
      className={
        (mobile ? 'block w-full px-4 py-3 text-base ' : 'px-4 py-2 text-sm ') +
        'rounded-lg font-medium transition-all ' +
        (isActive(path) ? 'bg-ufc-red text-white' : 'text-ufc-muted hover:text-white hover:bg-ufc-border/50')
      }>
      {label}
    </Link>
  );

  return (
    <nav className="bg-ufc-gray/90 backdrop-blur-md border-b border-ufc-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3" onClick={() => setMenuOpen(false)}>
            <svg width="32" height="32" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
              <polygon points="50,5 93,27.5 93,72.5 50,95 7,72.5 7,27.5" fill="none" stroke="#C8102E" strokeWidth="4"/>
              <polygon points="50,20 76,35 76,65 50,80 24,65 24,35" fill="none" stroke="#D4AF37" strokeWidth="2" opacity="0.5"/>
              <circle cx="38" cy="38" r="3" fill="#C8102E"/>
              <circle cx="62" cy="38" r="3" fill="#C8102E"/>
              <circle cx="50" cy="50" r="4" fill="#D4AF37"/>
              <circle cx="38" cy="62" r="3" fill="#C8102E"/>
              <circle cx="62" cy="62" r="3" fill="#C8102E"/>
              <line x1="38" y1="38" x2="50" y2="50" stroke="#C8102E" strokeWidth="1" opacity="0.5"/>
              <line x1="62" y1="38" x2="50" y2="50" stroke="#C8102E" strokeWidth="1" opacity="0.5"/>
              <line x1="38" y1="62" x2="50" y2="50" stroke="#C8102E" strokeWidth="1" opacity="0.5"/>
              <line x1="62" y1="62" x2="50" y2="50" stroke="#C8102E" strokeWidth="1" opacity="0.5"/>
            </svg>
            <span className="font-extrabold text-lg tracking-wide">
              <span className="text-ufc-red">CAGE</span><span className="gold-gradient">MIND</span>
            </span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {navLink("/", "Proximamente")}
            {navLink("/historico", "Historico")}
            {navLink("/sandbox", "Sandbox")}
            {navLink("/stats", "Stats")}
            {isAdmin && navLink("/admin", "Admin")}
          </div>

          {/* Hamburger button */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden p-2 rounded-lg text-ufc-muted hover:text-white hover:bg-ufc-border/50 transition-colors"
          >
            {menuOpen ? (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-ufc-border/50 bg-ufc-gray/95 backdrop-blur-md px-4 py-3 space-y-1">
          {navLink("/", "Proximamente", true)}
          {navLink("/historico", "Historico", true)}
          {navLink("/sandbox", "Sandbox", true)}
          {navLink("/stats", "Stats", true)}
          {isAdmin && navLink("/admin", "Admin", true)}
        </div>
      )}
    </nav>
  );
}
