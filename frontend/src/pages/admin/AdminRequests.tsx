import { FormEvent, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { Alert, Async, BackLink, ConfirmDialog, Empty, Field, PageHeader, Pagination, Spinner, StatusBadge, Timeline } from "../../components/ui";
import { numOrNull, useAction, useFetch, useForm, usePaged, useReference } from "../../hooks";
import { MODE_LABEL, REQUEST_STATUSES, fmtDate, fmtDateTime, money, statusLabel } from "../../labels";
import type { Obj } from "../../types";

const CLOSING = ["completed", "closed", "cancelled"];

// ------------------------------------------------------------------ list (all requests, or telephone only)
export function RequestsList({ phoneOnly = false }: { phoneOnly?: boolean }) {
  const [sp] = useSearchParams();
  const [status, setStatus] = useState(sp.get("status") ?? "");
  const [source, setSource] = useState("");
  const [scope, setScope] = useState(phoneOnly ? "open" : "");
  const [search, setSearch] = useState("");
  const f = usePaged<Obj>("/admin/requests/", {
    status,
    source: phoneOnly ? "telephone" : source,
    open: scope === "open" ? true : undefined,
    mine: scope === "mine" ? true : undefined,
    unassigned: scope === "unassigned" ? true : undefined,
    search,
  });
  const newPath = phoneOnly ? "/admin/phone/new" : "/admin/requests/new";
  return (
    <>
      <PageHeader
        title={phoneOnly ? "Phone Inquiries" : "Parent Requests"}
        subtitle={phoneOnly ? "Requests recorded by an administrator after a telephone call. Parents do not need an account." : "Online and manually recorded requests."}
        actions={<Link className="btn" to={newPath}>{phoneOnly ? "Record phone request" : "Record a request"}</Link>}
      />
      <div className="filters">
        <select className="input" value={scope} onChange={(e) => setScope(e.target.value)} aria-label="Scope">
          <option value="">All requests</option>
          <option value="open">Open only</option>
          <option value="mine">Assigned to me</option>
          <option value="unassigned">Unassigned</option>
        </select>
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="">Any status</option>
          <option value="draft">{statusLabel("draft")}</option>
          {REQUEST_STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
        </select>
        {!phoneOnly && (
          <select className="input" value={source} onChange={(e) => setSource(e.target.value)} aria-label="Source">
            <option value="">Any source</option>
            <option value="website">Website</option>
            <option value="telephone">Telephone</option>
            <option value="inquiry">Converted inquiry</option>
            <option value="other">Other</option>
          </select>
        )}
        <input className="input" placeholder="Search name, phone, subject…" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search" />
      </div>
      <Async f={f}>
        {(d) => d.results.length === 0 ? (
          <Empty title="No requests found" action={<Link className="btn" to={newPath}>Record a request</Link>}>Adjust the filters or record a new request.</Empty>
        ) : (
          <>
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Ref</th><th>From</th><th>Need</th><th>Status</th><th>Assigned</th><th>Received</th><th /></tr></thead>
              <tbody>
                {d.results.map((r) => (
                  <tr key={r.id}>
                    <td><strong>{r.reference}</strong><div className="muted small">{r.source_display}</div></td>
                    <td>{r.parent_info?.full_name ?? (r.contact_name || "Unnamed caller")}</td>
                    <td>
                      {[r.grade_level_name, r.subject_name].filter(Boolean).join(" ") || <span className="muted">Incomplete</span>}
                      <div className="muted small">{[r.location_name, MODE_LABEL[r.teaching_mode]].filter(Boolean).join(" · ")}</div>
                    </td>
                    <td><StatusBadge status={r.status} />{r.jobs?.length > 0 && <div className="muted small">{r.jobs.length} job(s), {r.applicant_count} applicant(s)</div>}</td>
                    <td>{r.assigned_to_name ?? <span className="muted">-</span>}</td>
                    <td>{fmtDate(r.created_at)}</td>
                    <td><Link className="btn btn-outline btn-sm" to={`/admin/requests/${r.id}`}>Open</Link></td>
                  </tr>
                ))}
              </tbody>
            </table></div>
            <Pagination page={f.page} count={d.count} onPage={f.setPage} />
          </>
        )}
      </Async>
    </>
  );
}

// ------------------------------------------------------------------ create / edit form
export function RequestForm({ initial, defaultSource = "telephone", onSaved }: { initial?: Obj; defaultSource?: string; onSaved: (r: Obj) => void }) {
  const ref = useReference();
  const a = useAction();
  const edit = Boolean(initial?.id);
  const { values, set, bind } = useForm({
    source: initial?.source ?? defaultSource,
    contact_name: initial?.contact_name ?? "",
    contact_phone: initial?.contact_phone ?? "",
    contact_email: initial?.contact_email ?? "",
    subject: initial?.subject ?? "",
    grade_level: initial?.grade_level ?? "",
    location: initial?.location ?? "",
    teaching_mode: initial?.teaching_mode ?? "",
    preferred_gender: initial?.preferred_gender ?? "",
    preferred_schedule: initial?.preferred_schedule ?? "",
    budget_amount: initial?.budget_amount ?? "",
    additional_requirements: initial?.additional_requirements ?? "",
    internal_notes: initial?.internal_notes ?? "",
    is_draft: false,
  });
  if (!ref) return <Spinner />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const body = {
      ...(edit ? {} : { source: values.source }),
      contact_name: values.contact_name,
      contact_phone: values.contact_phone,
      contact_email: values.contact_email,
      subject: numOrNull(values.subject),
      grade_level: numOrNull(values.grade_level),
      location: numOrNull(values.location),
      teaching_mode: values.teaching_mode,
      preferred_gender: values.preferred_gender,
      preferred_schedule: values.preferred_schedule,
      budget_amount: values.budget_amount === "" ? null : values.budget_amount,
      additional_requirements: values.additional_requirements,
      internal_notes: values.internal_notes,
      ...(edit ? {} : { is_draft: values.is_draft }),
    };
    const r = await a.run(() => (edit ? api.patch<Obj>(`/admin/requests/${initial!.id}/`, body) : api.post<Obj>("/admin/requests/", body)));
    if (r) onSaved(r);
  }
  const hasParent = Boolean(initial?.parent);
  return (
    <form onSubmit={submit} noValidate>
      {a.error && <Alert kind="error">{a.error}</Alert>}
      {!hasParent && (
        <>
          <h3>Caller</h3>
          <p className="muted small">Everything here is optional. Keep it to what you need to follow up.</p>
          <div className="grid cols-3">
            <Field label="Name or reference" error={a.fields.contact_name}><input className="input" {...bind("contact_name")} maxLength={150} /></Field>
            <Field label="Phone" error={a.fields.contact_phone}><input className="input" inputMode="tel" {...bind("contact_phone")} maxLength={30} /></Field>
            <Field label="Email" error={a.fields.contact_email}><input className="input" type="email" {...bind("contact_email")} /></Field>
          </div>
        </>
      )}
      <h3 className="mt">The need</h3>
      <div className="grid cols-3">
        <Field label="Subject" error={a.fields.subject}>
          <select className="input" {...bind("subject")}><option value="">Not known yet</option>{ref.subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
        </Field>
        <Field label="Grade level" error={a.fields.grade_level}>
          <select className="input" {...bind("grade_level")}><option value="">Not known yet</option>{ref.grade_levels.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}</select>
        </Field>
        <Field label="Teaching mode" error={a.fields.teaching_mode}>
          <select className="input" {...bind("teaching_mode")}><option value="">Not known yet</option>{ref.request_modes.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}</select>
        </Field>
        <Field label="General location" error={a.fields.location}>
          <select className="input" {...bind("location")}><option value="">Not known / online</option>{ref.locations.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}</select>
        </Field>
        <Field label="Preferred schedule" error={a.fields.preferred_schedule}><input className="input" {...bind("preferred_schedule")} maxLength={200} placeholder="e.g. 3 evenings a week" /></Field>
        <Field label="Budget (ETB)" error={a.fields.budget_amount}><input className="input" type="number" min="0" step="0.01" {...bind("budget_amount")} /></Field>
        <Field label="Preferred tutor gender" error={a.fields.preferred_gender}>
          <select className="input" {...bind("preferred_gender")}><option value="">No preference</option><option value="male">Male</option><option value="female">Female</option></select>
        </Field>
        {!edit && (
          <Field label="Source">
            <select className="input" {...bind("source")}><option value="telephone">Telephone</option><option value="other">Other (walk-in, email…)</option></select>
          </Field>
        )}
      </div>
      <Field label="Additional requirements" error={a.fields.additional_requirements}><textarea className="input" {...bind("additional_requirements")} maxLength={2000} /></Field>
      <Field label="Internal notes (never shown to parents)" error={a.fields.internal_notes}><textarea className="input" {...bind("internal_notes")} /></Field>
      <div className="form-actions">
        <button className="btn" disabled={a.busy}>{a.busy ? "Saving…" : edit ? "Save changes" : "Save request"}</button>
        {!edit && <label className="check"><input type="checkbox" checked={values.is_draft} onChange={(e) => set("is_draft", e.target.checked)} /> Save as incomplete draft (finish later)</label>}
      </div>
    </form>
  );
}

export function NewRequest({ phone = false }: { phone?: boolean }) {
  const nav = useNavigate();
  return (
    <>
      <BackLink to={phone ? "/admin/phone" : "/admin/requests"}>{phone ? "Phone inquiries" : "Parent requests"}</BackLink>
      <PageHeader title={phone ? "Record a phone request" : "Record a request"} subtitle="The parent does not need an account. You can save an incomplete request and return to it." />
      <div className="card"><RequestForm onSaved={(r) => nav(`/admin/requests/${r.id}`)} /></div>
    </>
  );
}

// ------------------------------------------------------------------ detail
export function RequestDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const f = useFetch<Obj>(`/admin/requests/${id}/`);
  const a = useAction();
  const [status, setStatus] = useState("");
  const [latest, setLatest] = useState("");
  const [outcome, setOutcome] = useState("");
  const [confirm, setConfirm] = useState(false);

  async function applyStatus(note = "") {
    const r = await a.run(() => api.post<Obj>(`/admin/requests/${id}/set-status/`, { status, latest_update: latest || undefined, outcome: outcome || undefined, note }));
    if (r) {
      setConfirm(false);
      setLatest("");
      f.reload();
    }
  }
  function onSubmitStatus(e: FormEvent) {
    e.preventDefault();
    if (!status) return;
    if (CLOSING.includes(status)) {
      a.setError(null);
      setConfirm(true);
    } else applyStatus();
  }
  async function assign(adminId: number | null) {
    await a.run(() => api.post(`/admin/requests/${id}/assign/`, { admin: adminId }));
    f.reload();
  }
  async function createJob() {
    const job = await a.run(() => api.post<Obj>(`/admin/requests/${id}/create-job/`));
    if (job) nav(`/admin/jobs/${job.id}`);
  }

  return (
    <Async f={f}>
      {(r) => (
        <>
          <BackLink to={r.source === "telephone" ? "/admin/phone" : "/admin/requests"}>Requests</BackLink>
          <PageHeader
            title={r.reference}
            subtitle={<><StatusBadge status={r.status} /> <span className="badge badge-gray">{r.source_display}</span> {r.assigned_to_name ? `Assigned to ${r.assigned_to_name}` : "Unassigned"}</>}
            actions={<>
              <Link className="btn" to={`/admin/matching?request=${r.id}`}>Find matching tutors</Link>
              <button className="btn btn-outline" onClick={createJob} disabled={a.busy}>Create job from request</button>
            </>}
          />
          {a.error && !confirm && <Alert kind="error">{a.error}</Alert>}
          {r.status === "draft" && <Alert kind="warning">This request is an incomplete draft. Set the status to <strong>New</strong> or <strong>In review</strong> when ready; parents never see drafts.</Alert>}

          <div className="grid cols-2">
            <div className="card">
              <h3>Contact (private)</h3>
              {r.parent_info ? (
                <dl className="kv"><dt>Parent</dt><dd>{r.parent_info.full_name}</dd><dt>Email</dt><dd>{r.parent_info.email}</dd><dt>Phone</dt><dd>{r.parent_info.phone || "-"}</dd></dl>
              ) : (
                <dl className="kv"><dt>Name</dt><dd>{r.contact_name || "-"}</dd><dt>Phone</dt><dd>{r.contact_phone || "-"}</dd><dt>Email</dt><dd>{r.contact_email || "-"}</dd></dl>
              )}
              <div className="row">
                {r.assigned_to !== user?.id && <button className="btn btn-outline btn-sm" onClick={() => assign(user!.id)} disabled={a.busy}>Assign to me</button>}
                {r.assigned_to && <button className="btn btn-ghost btn-sm" onClick={() => assign(null)} disabled={a.busy}>Unassign</button>}
              </div>
            </div>
            <div className="card">
              <h3>Requirements</h3>
              <dl className="kv">
                <dt>Subject</dt><dd>{r.subject_name ?? "-"}</dd>
                <dt>Grade</dt><dd>{r.grade_level_name ?? "-"}</dd>
                <dt>Mode</dt><dd>{MODE_LABEL[r.teaching_mode] ?? "-"}</dd>
                <dt>Location</dt><dd>{r.location_name ?? "-"}</dd>
                <dt>Schedule</dt><dd>{r.preferred_schedule || "-"}</dd>
                <dt>Budget</dt><dd>{money(r.budget_amount) ?? "-"}</dd>
                <dt>Preferred tutor</dt><dd>{r.preferred_tutor ? <Link to={`/admin/tutors/${r.preferred_tutor}`}>{r.preferred_tutor_name}</Link> : "-"}</dd>
                <dt>Tutor gender</dt><dd>{r.preferred_gender || "No preference"}</dd>
              </dl>
              {r.additional_requirements && <p className="small" style={{ whiteSpace: "pre-wrap" }}>{r.additional_requirements}</p>}
            </div>
          </div>

          <div className="card mt">
            <h3>Update status</h3>
            <p className="muted small">The "message to parent" is shown on their My Requests page. Do not include private details.</p>
            <form onSubmit={onSubmitStatus}>
              <div className="grid cols-3">
                <Field label="New status" required>
                  <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
                    <option value="">Choose…</option>
                    {["new", ...REQUEST_STATUSES.filter((s) => s !== "new")].map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
                  </select>
                </Field>
                <Field label="Message to parent"><input className="input" value={latest} onChange={(e) => setLatest(e.target.value)} maxLength={300} /></Field>
                <Field label="Outcome (internal)" hint="Recommended when closing."><input className="input" value={outcome} onChange={(e) => setOutcome(e.target.value)} /></Field>
              </div>
              <button className="btn" disabled={!status || a.busy}>Update status</button>
            </form>
            {r.outcome && <p className="small"><strong>Recorded outcome:</strong> {r.outcome}</p>}
          </div>

          <div className="grid cols-2 mt">
            <div className="card">
              <h3>Jobs from this request</h3>
              {r.jobs.length === 0 ? <p className="muted small">No public job. This request can be resolved privately.</p> : (
                <ul className="stack">{r.jobs.map((j: Obj) => <li key={j.id}><Link to={`/admin/jobs/${j.id}`}>{j.reference} {j.title}</Link> <StatusBadge status={j.status} /></li>)}</ul>
              )}
            </div>
            <div className="card">
              <h3>Introductions</h3>
              {r.introductions.length === 0 ? <p className="muted small">None yet. Create one from the matching page.</p> : (
                <ul className="stack">{r.introductions.map((i: Obj) => <li key={i.id}><Link to={`/admin/introductions/${i.id}`}>{i.tutor_name}</Link> <StatusBadge status={i.status} /></li>)}</ul>
              )}
            </div>
          </div>

          <details className="card mt">
            <summary><strong>Edit request details</strong></summary>
            <div className="mt"><RequestForm initial={r} onSaved={() => f.reload()} /></div>
          </details>

          <h2 className="mt-2">History</h2>
          <div className="card"><Timeline items={r.history} /><p className="muted small">Received {fmtDateTime(r.created_at)}</p></div>

          <ConfirmDialog
            open={confirm}
            title={`Mark request as ${statusLabel(status)}?`}
            message={<>{status === "cancelled" || status === "closed" ? <p>The parent will see this status. Add a short reason.</p> : <p>The request will be completed.</p>}{a.error && <Alert kind="error">{a.error}</Alert>}</>}
            noteLabel="Reason / note"
            noteRequired={status !== "completed"}
            confirmLabel="Confirm"
            danger={status !== "completed"}
            busy={a.busy}
            onConfirm={applyStatus}
            onCancel={() => setConfirm(false)}
          />
        </>
      )}
    </Async>
  );
}

// ------------------------------------------------------------------ matching
export function Matching() {
  const [sp, setSp] = useSearchParams();
  const requestId = sp.get("request");
  const list = useFetch<{ results: Obj[] }>("/admin/requests/?open=true&page_size=50");
  const req = useFetch<Obj>(requestId ? `/admin/requests/${requestId}/` : null);
  const matches = useFetch<Obj>(requestId ? `/admin/requests/${requestId}/matches/` : null);
  const a = useAction();
  const [done, setDone] = useState<Record<number, number>>({});

  async function introduce(tutorId: number) {
    const intro = await a.run(() => api.post<Obj>("/admin/introductions/", { parent_request: Number(requestId), tutor: tutorId }));
    if (intro) {
      setDone((d) => ({ ...d, [tutorId]: intro.id }));
      req.reload();
    }
  }

  return (
    <>
      <PageHeader title="Tutor Matching" subtitle="Suggestions are based on the request's details. You decide who to contact; nothing is sent to anyone from this page." />
      <div className="filters">
        <select className="input" value={requestId ?? ""} onChange={(e) => setSp(e.target.value ? { request: e.target.value } : {})} aria-label="Choose a request">
          <option value="">Choose a request…</option>
          {(list.data?.results ?? []).map((r) => (
            <option key={r.id} value={r.id}>{r.reference} · {[r.grade_level_name, r.subject_name].filter(Boolean).join(" ") || "incomplete"} · {r.parent_info?.full_name ?? (r.contact_name || "caller")}</option>
          ))}
        </select>
      </div>
      {!requestId && <Empty title="Pick a request to see suggestions">Matching needs at least a subject on the request.</Empty>}
      {requestId && req.data && (
        <div className="card mb">
          <strong>{req.data.reference}</strong> · {[req.data.grade_level_name, req.data.subject_name].filter(Boolean).join(" ") || "Subject not set"} · {req.data.location_name ?? "No location"} · {MODE_LABEL[req.data.teaching_mode] ?? "any mode"}
          {req.data.preferred_gender && <> · prefers {req.data.preferred_gender} tutor</>}{" "}
          <Link to={`/admin/requests/${req.data.id}`}>Open request</Link>
          {!req.data.subject && <Alert kind="warning">Add a subject to the request to get meaningful suggestions.</Alert>}
        </div>
      )}
      {a.error && <Alert kind="error">{a.error}</Alert>}
      {requestId && (
        <Async f={matches}>
          {(m) => m.results.length === 0 ? (
            <Empty title="No approved tutors match" action={requestId ? <Link className="btn" to={`/admin/requests/${requestId}`}>Create a job instead</Link> : undefined}>
              No approved, active tutor teaches this subject with the given preferences. You can publish a job so tutors can express interest.
            </Empty>
          ) : (
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Tutor</th><th>Why suggested</th><th>Concerns</th><th>Profile</th><th /></tr></thead>
              <tbody>
                {m.results.map((t: Obj) => (
                  <tr key={t.id}>
                    <td>
                      <Link to={`/admin/tutors/${t.id}`}><strong>{t.display_name}</strong></Link>
                      {m.preferred_tutor === t.id && <span className="badge badge-blue" style={{ marginLeft: 6 }}>Parent's choice</span>}
                      <div className="muted small">Score {t.score}</div>
                    </td>
                    <td>{t.reasons.map((x: string) => <span key={x} className="chip">{x}</span>)}</td>
                    <td>{t.concerns.length ? t.concerns.map((x: string) => <span key={x} className="badge badge-amber" style={{ margin: 2 }}>{x}</span>) : <span className="muted small">None</span>}</td>
                    <td className="small">
                      {t.location?.label ?? "-"}<br />{MODE_LABEL[t.teaching_mode]} · {t.years_experience} yrs<br />
                      {money(t.rate_amount, t.rate_unit) ?? "No rate"}<br />{t.verified_documents} verified doc(s)
                    </td>
                    <td>
                      {done[t.id] ? <Link className="btn btn-outline btn-sm" to={`/admin/introductions/${done[t.id]}`}>View introduction</Link> : (
                        <button className="btn btn-sm" onClick={() => introduce(t.id)} disabled={a.busy}>Start introduction</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}
        </Async>
      )}
    </>
  );
}
