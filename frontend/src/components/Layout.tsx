import { ReactNode, useEffect, useState } from "react";
import { Link, NavLink, Navigate, Outlet, useLocation } from "react-router-dom";
import { api } from "../api";
import { homeFor, useAuth } from "../auth";
import type { Role } from "../types";
import { Spinner } from "./ui";

const Logo = () => (
  <Link to="/" className="brand" aria-label="TutorConnect home">
    <span className="brand-mark" aria-hidden="true">
      <svg width="20" height="20" viewBox="0 0 32 32"><path d="M4 12l12-6 12 6-12 6z M9 16v6c0 2 3.1 4 7 4s7-2 7-4v-6l-7 3.5z" fill="#fff" /></svg>
    </span>
    TutorConnect
  </Link>
);

export function PublicLayout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  useEffect(() => setOpen(false), [loc.pathname]);
  return (
    <>
      <a href="#main" className="sr-only">Skip to content</a>
      <header className="site-header">
        <div className="container nav">
          <Logo />
          <button className="btn btn-outline btn-sm nav-toggle" aria-expanded={open} aria-label="Toggle menu" onClick={() => setOpen(!open)}>
            Menu
          </button>
          <nav className={`nav-links ${open ? "open" : ""}`} aria-label="Main">
            <NavLink to="/tutors">Find Tutors</NavLink>
            <NavLink to="/register/tutor">Become a Tutor</NavLink>
            {user ? (
              <>
                <NavLink to={homeFor(user.role)}>My Dashboard</NavLink>
                <button className="linklike" onClick={logout}>Log out</button>
              </>
            ) : (
              <>
                <NavLink to="/login">Log in</NavLink>
                <Link className="btn btn-sm" to="/register">Sign up as a parent</Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main id="main"><Outlet /></main>
      <footer className="site-footer">
        <div className="container grid cols-3">
          <div>
            <h4>TutorConnect</h4>
            <p className="small">Qualified tutors, introduced by people who check their credentials. We never share contact details without everyone's agreement.</p>
          </div>
          <div>
            <h4>Parents</h4>
            <ul className="footer-links small">
              <li><Link to="/tutors">Find a tutor</Link></li>
              <li><Link to="/register">Create a parent account</Link></li>
              <li><Link to="/parent/contact">Contact the administrator</Link></li>
            </ul>
          </div>
          <div>
            <h4>Tutors &amp; policies</h4>
            <ul className="footer-links small">
              <li><Link to="/register/tutor">Apply as a tutor</Link></li>
              <li><Link to="/policies#privacy">Privacy</Link></li>
              <li><Link to="/policies#terms">Terms of use</Link></li>
              <li><Link to="/policies#safety">Safety &amp; verification</Link></li>
            </ul>
          </div>
        </div>
        <div className="container small" style={{ marginTop: "1.5rem", opacity: 0.8 }}>© {new Date().getFullYear()} TutorConnect</div>
      </footer>
    </>
  );
}

export interface NavItem { to: string; label: string; end?: boolean; badge?: boolean }

export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <div className="container"><Spinner /></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname + loc.search }} />;
  if (user.role !== role) {
    return (
      <div className="container section">
        <div className="card form-narrow">
          <h2>This page is not available to your account</h2>
          <p className="muted">You are signed in as a {user.role}. This area is for {role === "admin" ? "administrators" : `${role}s`}.</p>
          <Link className="btn" to={homeFor(user.role)}>Go to my dashboard</Link>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}

export function DashboardLayout({ title, nav }: { title: string; nav: NavItem[] }) {
  const { user, logout, refresh } = useAuth();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const loc = useLocation();

  useEffect(() => setOpen(false), [loc.pathname]);
  useEffect(() => {
    refresh();
  }, [refresh]);
  useEffect(() => {
    let alive = true;
    const load = () => api.get<{ count: number }>("/notifications/unread-count/").then((r) => alive && setUnread(r.count)).catch(() => undefined);
    load();
    const t = setInterval(load, 60000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [loc.pathname]);

  return (
    <>
      <header className="site-header">
        <div className="container nav">
          <Logo />
          <div className="row">
            <span className="muted small" style={{ display: "none" }}>{user?.full_name}</span>
            <Link to="/tutors" className="btn btn-ghost btn-sm">Public site</Link>
            <button className="btn btn-outline btn-sm" onClick={logout}>Log out</button>
          </div>
        </div>
      </header>
      <button className="btn btn-outline btn-sm dash-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? "Close menu" : `${title} menu`}
      </button>
      <div className="dash">
        <aside className={`dash-side ${open ? "open" : ""}`} aria-label={`${title} navigation`}>
          <h4>{title}</h4>
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}>
              {n.label}
              {n.badge && unread > 0 && <span className="count-pill" aria-label={`${unread} unread`}>{unread}</span>}
            </NavLink>
          ))}
        </aside>
        <main className="dash-main" id="main"><Outlet /></main>
      </div>
    </>
  );
}
