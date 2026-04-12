import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_BASE } from '../config';

export default function RegisterPage() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password || !confirm) return;

    if (password !== confirm) {
      setError('Las contraseñas no coinciden');
      return;
    }
    if (password.length < 6) {
      setError('La contraseña debe tener al menos 6 caracteres');
      return;
    }
    if (username.trim().length < 3) {
      setError('El usuario debe tener al menos 3 caracteres');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), email: email.trim(), password }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Error de conexión' }));
        throw new Error(err.detail || 'Error al registrar');
      }

      // Auto-login after register
      await login(username.trim(), password);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Error al registrar');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <svg width="40" height="40" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
              <polygon points="50,5 93,27.5 93,72.5 50,95 7,72.5 7,27.5" fill="none" stroke="#C8102E" strokeWidth="4" />
              <polygon points="50,20 76,35 76,65 50,80 24,65 24,35" fill="none" stroke="#D4AF37" strokeWidth="2" opacity="0.5" />
              <circle cx="50" cy="50" r="4" fill="#D4AF37" />
            </svg>
            <span className="font-extrabold text-2xl tracking-wide">
              <span className="text-ufc-red">CAGE</span><span className="gold-gradient">MIND</span>
            </span>
          </div>
          <p className="text-ufc-muted text-sm">Crea tu cuenta y haz tus picks</p>
        </div>

        {/* Register form */}
        <div className="glass-card p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-ufc-muted font-bold uppercase tracking-wider mb-2">
                Usuario
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input-search"
                placeholder="tu_nombre"
                autoFocus
                autoComplete="username"
                maxLength={20}
              />
            </div>

            <div>
              <label className="block text-xs text-ufc-muted font-bold uppercase tracking-wider mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-search"
                placeholder="tu@email.com"
                autoComplete="email"
              />
            </div>

            <div>
              <label className="block text-xs text-ufc-muted font-bold uppercase tracking-wider mb-2">
                Contraseña
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-search"
                placeholder="mínimo 6 caracteres"
                autoComplete="new-password"
              />
            </div>

            <div>
              <label className="block text-xs text-ufc-muted font-bold uppercase tracking-wider mb-2">
                Confirmar contraseña
              </label>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                className="input-search"
                placeholder="repite tu contraseña"
                autoComplete="new-password"
              />
            </div>

            {error && (
              <div className="text-ufc-red text-sm text-center py-2 bg-ufc-red/10 rounded-lg border border-ufc-red/20">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !username.trim() || !email.trim() || !password || !confirm}
              className="btn-primary w-full text-base py-3"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Creando cuenta...
                </span>
              ) : (
                'Crear cuenta'
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-ufc-muted text-sm mt-6">
          ¿Ya tienes cuenta?{' '}
          <Link to="/login" className="text-ufc-gold hover:underline">Inicia sesión</Link>
        </p>
      </div>
    </div>
  );
}
