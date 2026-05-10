import { NavLink } from 'react-router-dom';
import './Navbar.css';

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="nav-brand">
        <div className="nav-logo"><span>AI</span></div>
        <div className="nav-title">
          <span className="brand-name">AI Codelens</span>
          <span className="brand-sub">Intelligent Software Testing System</span>
        </div>
      </div>
      <div className="nav-links">
        <NavLink to="/" end className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>Dashboard</NavLink>
        <NavLink to="/predict" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>New Prediction</NavLink>
        <NavLink to="/results" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>Recent Results</NavLink>
        <NavLink to="/model" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>Model</NavLink>
      </div>
    </nav>
  );
}
