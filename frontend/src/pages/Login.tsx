import { FormEvent, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { errMsg } from "../api";
import { homeFor, useAuth } from "../auth";
import { Alert, Field } from "../components/ui";
import { useAction } from "../hooks";

export default function Login() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const from = (loc.state as { from?: string } | null)?.from;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const a = useAction();

  if (user) return <Navigate to={from ?? homeFor(user.role)} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const u = await a.run(() => login(email.trim(), password));
    if (u) nav(from ?? homeFor(u.role), { replace: true });
  }

  return (
    <div className="container">
      <div className="card auth-card">
        <h1 style={{ fontSize: "1.7rem" }}>Log in</h1>
        {from && <Alert>Please log in to continue.</Alert>}
        {a.error && <Alert kind="error">{a.error.includes("No active account") ? "Incorrect email or password." : a.error}</Alert>}
        <form onSubmit={submit}>
          <Field label="Email" required><input className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
          <Field label="Password" required><input className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
          <button className="btn" style={{ width: "100%" }} disabled={a.busy}>{a.busy ? "Logging in…" : "Log in"}</button>
        </form>
        <p className="mt small">New here? <Link to="/register">Create a parent account</Link> or <Link to="/register/tutor">apply as a tutor</Link>.</p>
      </div>
    </div>
  );
}

export { errMsg };
