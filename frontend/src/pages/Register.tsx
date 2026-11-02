import { FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { homeFor, useAuth } from "../auth";
import { Alert, Field } from "../components/ui";
import { useAction, useForm } from "../hooks";

export default function Register({ role }: { role: "parent" | "tutor" }) {
  const { user, register } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const from = (loc.state as { from?: string } | null)?.from;
  const f = useForm({ full_name: "", email: "", phone: "", password: "" });
  const a = useAction();
  const isTutor = role === "tutor";

  if (user) return <Navigate to={homeFor(user.role)} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const data: Record<string, string> = { ...f.values, email: f.values.email.trim() };
    if (!data.phone) delete data.phone;
    const u = await a.run(() => register(role, data));
    if (u) nav(isTutor ? "/tutor/profile" : from ?? "/parent", { replace: true });
  }

  return (
    <div className="container">
      <div className="card auth-card">
        <h1 style={{ fontSize: "1.7rem" }}>{isTutor ? "Apply as a tutor" : "Create a parent account"}</h1>
        <p className="muted small">
          {isTutor
            ? "Create your account first, then complete your profile and upload your qualifications. Your profile is only shown publicly after an administrator approves it."
            : "An account lets you send tutor requests and follow their progress. It takes less than a minute."}
        </p>
        {a.error && <Alert kind="error">{a.error}</Alert>}
        <form onSubmit={submit} noValidate>
          <Field label="Full name" required error={a.fields.full_name}><input className="input" autoComplete="name" required {...f.bind("full_name")} aria-invalid={Boolean(a.fields.full_name)} /></Field>
          <Field label="Email" required error={a.fields.email}><input className="input" type="email" autoComplete="email" required {...f.bind("email")} aria-invalid={Boolean(a.fields.email)} /></Field>
          <Field label="Phone number" required={isTutor} error={a.fields.phone} hint={isTutor ? "Kept private. Used by the administrator only." : "Only if you want us to be able to call you."}>
            <input className="input" type="tel" autoComplete="tel" required={isTutor} {...f.bind("phone")} aria-invalid={Boolean(a.fields.phone)} />
          </Field>
          <Field label="Password" required error={a.fields.password} hint="At least 8 characters; avoid common or all-numeric passwords.">
            <input className="input" type="password" autoComplete="new-password" required {...f.bind("password")} aria-invalid={Boolean(a.fields.password)} />
          </Field>
          <button className="btn" style={{ width: "100%" }} disabled={a.busy}>{a.busy ? "Creating account…" : "Create account"}</button>
        </form>
        <p className="mt small">Already registered? <Link to="/login" state={{ from }}>Log in</Link>.</p>
      </div>
    </div>
  );
}
