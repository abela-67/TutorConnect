import { FormEvent, useState } from "react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { Alert, Field, PageHeader } from "../../components/ui";
import { idOrNull, useAction, useForm, useReference } from "../../hooks";
import type { User } from "../../types";

export default function Account() {
  const { user, refresh } = useAuth();
  const ref = useReference();
  const isParent = user?.role === "parent";
  const f = useForm({
    full_name: user?.full_name ?? "",
    phone: user?.phone ?? "",
    preferred_contact: user?.preferred_contact ?? "email",
    default_location: user?.default_location ? String(user.default_location) : "",
  });
  const p = useForm({ old_password: "", new_password: "" });
  const a = useAction();
  const b = useAction();
  const [saved, setSaved] = useState("");

  async function save(e: FormEvent) {
    e.preventDefault();
    setSaved("");
    const body: Record<string, unknown> = { full_name: f.values.full_name, phone: f.values.phone };
    if (isParent) {
      body.preferred_contact = f.values.preferred_contact;
      body.default_location = idOrNull(f.values.default_location);
    }
    const r = await a.run(() => api.patch<User>("/auth/me/", body));
    if (r) {
      await refresh();
      setSaved("Your details were updated.");
    }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    setSaved("");
    const r = await b.run(() => api.post("/auth/change-password/", p.values));
    if (r) {
      p.setValues({ old_password: "", new_password: "" });
      setSaved("Your password was changed.");
    }
  }

  return (
    <>
      <PageHeader title="Account settings" />
      {saved && <Alert kind="success">{saved}</Alert>}
      <div className="grid cols-2">
        <form className="card" onSubmit={save}>
          <h3>Your details</h3>
          {a.error && <Alert kind="error">{a.error}</Alert>}
          <Field label="Email" required hint="Your email is your login and cannot be changed here."><input className="input" value={user?.email ?? ""} disabled /></Field>
          <Field label="Full name" required error={a.fields.full_name}><input className="input" required {...f.bind("full_name")} /></Field>
          <Field label="Phone" required={user?.role === "tutor"} error={a.fields.phone}><input className="input" type="tel" {...f.bind("phone")} /></Field>
          {isParent && (
            <>
              <Field label="Preferred way to be contacted">
                <select className="input" {...f.bind("preferred_contact")}>
                  <option value="email">Email</option>
                  <option value="phone">Phone call</option>
                </select>
              </Field>
              <Field label="Usual lesson location" hint="Pre-fills your requests.">
                <select className="input" {...f.bind("default_location")}>
                  <option value="">Not set</option>
                  {ref?.locations.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
                </select>
              </Field>
            </>
          )}
          <button className="btn" disabled={a.busy}>{a.busy ? "Saving…" : "Save changes"}</button>
        </form>

        <form className="card" onSubmit={changePassword}>
          <h3>Change password</h3>
          {b.error && <Alert kind="error">{b.error}</Alert>}
          <Field label="Current password" required error={b.fields.old_password}><input className="input" type="password" autoComplete="current-password" required {...p.bind("old_password")} /></Field>
          <Field label="New password" required error={b.fields.new_password}><input className="input" type="password" autoComplete="new-password" required {...p.bind("new_password")} /></Field>
          <button className="btn" disabled={b.busy}>Change password</button>
        </form>
      </div>
    </>
  );
}
