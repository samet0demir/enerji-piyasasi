import { Link, useLocation } from 'react-router-dom';
import './Navigation.css';

export function Navigation() {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="navigation">
      <div className="nav-brand">
        <h1>EPIAS Analiz</h1>
      </div>
      <div className="nav-links">
        <Link
          to="/"
          className={`nav-link ${isActive('/') ? 'active' : ''}`}
        >
          Genel Bakis
        </Link>
        <Link
          to="/production"
          className={`nav-link ${isActive('/production') ? 'active' : ''}`}
        >
          Uretim Analizi
        </Link>
        <Link
          to="/consumption"
          className={`nav-link ${isActive('/consumption') ? 'active' : ''}`}
        >
          Tuketim Analizi
        </Link>
      </div>
    </nav>
  );
}
