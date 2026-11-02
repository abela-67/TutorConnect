import { FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { Alert, Async, BackLink, BarList, ConfirmDialog, Empty, Field, PageHeader, Pagination, StatusBadge, Timeline } from "../../components/ui";
import { invalidateReference, useAction, useFetch, usePaged } from "../../hooks";
import { INQUIRY_CATEGORIES, INQUIRY_STATUSES, INTRO_STATUSES, fmtDate, fmtDateTime, statusLabel } from "../../labels";
import type { Obj } from "../../types";

// ------------------------------------------------------------------ introductions
export function IntroductionsList() {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const f = usePaged<Obj>("/admin/introductions/", { status, search });
  return (
    <>
      <PageHeader title="Introductions" subtitle="Parent–tutor introductions arranged by administrators. Start one from the Matching page." actions={<Link className="btn" to="/admin/matching">Open matching</Link>} />
      <div className="filters">
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="">Any status</option>
          {INTRO_STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
        </select>
        <input className="input" placeholder="Search tutor or parent" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search" />
      </div>
      <Async f={f}>
        {(d) => d.results.length === 0 ? <Empty title="No introductions yet">Use Tutor Matching to start one for a request.</Empty> : (
          <>
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Request</th><th>Parent</th><th>Tutor</th><th>Status</th><th>Agreed</th><th>Created</th><th /></tr></thead>
              <tbody>
                {d.results.map((i) => (
                  <tr key={i.id}>
                    <td><Link to={`/admin/requests/${i.parent_request}`}>{i.request_reference}</Link></td>
                    <td>{i.parent_name}</td>
                    <td>{i.tutor_name}</td>
                    <td><StatusBadge status={i.status} /></td>
                    <td className="small">Parent {i.parent_agreed ? "✓" : "–"} · Tutor {i.tutor_agreed ? "✓" : "–"}</td>
                    <td>{fmtDate(i.created_at)}</td>
                    <td><Link className="btn btn-outline btn-sm" to={`/admin/introductions/${i.id}`}>Open</Link></td>
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

export function IntroductionDetail() {
  const { id } = useParams();
  const f = useFetch<Obj>(`/admin/introductions/${id}/`);
  const a = useAction();
  const [status, setStatus] = useState("");
  const [outcome, setOutcome] = useState<string | null>(null);
  const [date, setDate] = useState("");
  const [shareDlg, setShareDlg] = useState(false);
  const [confirm, setConfirm] = useState(false);

  async function consent(party: "parent" | "tutor", agreed: boolean) {
    await a.run(() => api.post(`/admin/introductions/${id}/consent/`, { party, agreed }));
    f.reload();
  }
  async function submitStatus(note = "") {
    const body: Obj = { status, note };
    if (outcome !== null) body.outcome_notes = outcome;
    if (date) body.introduced_on = date;
    const r = await a.run(() => api.post(`/admin/introductions/${id}/set-status/`, body));
    if (r) {
      setConfirm(false);
      setStatus("");
      f.reload();
    }
  }
  async function share() {
    const r = await a.run(() => api.post(`/admin/introductions/${id}/share-contact/`));
    if (r) {
      setShareDlg(false);
      f.reload();
    }
  }
  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!status) return;
    if (status === "cancelled" || status === "closed") {
      a.setError(null);
      setConfirm(true);
    } else submitStatus();
  }

  return (
    <Async f={f}>
      {(i) => {
        const both = i.parent_agreed && i.tutor_agreed;
        const finished = i.status === "cancelled" || i.status === "closed";
        return (
          <>
            <BackLink to="/admin/introductions">Introductions</BackLink>
            <PageHeader title={`${i.tutor_name} ↔ ${i.parent_name}`} subtitle={<><StatusBadge status={i.status} /> <Link to={`/admin/requests/${i.parent_request}`}>{i.request_reference}</Link>{i.job && <> · <Link to={`/admin/jobs/${i.job}`}>{i.job_title}</Link></>}</>} />
            {a.error && !shareDlg && !confirm && <Alert kind="error">{a.error}</Alert>}

            <div className="grid cols-2">
              <div className="card">
                <h3>Consent</h3>
                <p className="muted small">Record agreement only after the person has told you directly. Contact details are shared only when both have agreed.</p>
                {(["parent", "tutor"] as const).map((p) => (
                  <div key={p} className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
                    <span><strong>{p === "parent" ? "Parent" : "Tutor"}</strong>: {i[`${p}_agreed`] ? <span className="badge badge-green">Agreed {fmtDate(i[`${p}_agreed_at`])}</span> : <span className="badge badge-gray">Not yet</span>}</span>
                    <button className="btn btn-outline btn-sm" disabled={a.busy || finished} onClick={() => consent(p, !i[`${p}_agreed`])}>{i[`${p}_agreed`] ? "Withdraw" : "Record agreement"}</button>
                  </div>
                ))}
                <hr />
                <p>
                  <strong>Contact details shared with parent:</strong> {i.contact_shared ? <span className="badge badge-green">Yes, {fmtDate(i.contact_shared_at)}</span> : <span className="badge badge-gray">No</span>}
                </p>
                {!i.contact_shared && <button className="btn" disabled={!both || finished || a.busy} onClick={() => { a.setError(null); setShareDlg(true); }}>Share tutor contact with parent</button>}
                {!both && <p className="muted small">Available after both parties agree.</p>}
              </div>

              <div className="card">
                <h3>Update progress</h3>
                <form onSubmit={onSubmit}>
                  <Field label="Status" required>
                    <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
                      <option value="">Choose…</option>
                      {INTRO_STATUSES.filter((s) => s !== i.status).map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
                    </select>
                  </Field>
                  <Field label="Date introduced"><input className="input" type="date" value={date} onChange={(e) => setDate(e.target.value)} /></Field>
                  <Field label="Outcome notes"><textarea className="input" value={outcome ?? i.outcome_notes ?? ""} onChange={(e) => setOutcome(e.target.value)} /></Field>
                  <button className="btn" disabled={!status || a.busy || finished}>Update</button>
                  {finished && <span className="muted small"> This introduction is finished.</span>}
                </form>
                <p className="muted small">Confirming the match or completing the introduction updates the parent's request and notifies both people.</p>
              </div>
            </div>

            <h2 className="mt-2">History</h2>
            <div className="card"><Timeline items={i.history} /></div>

            <ConfirmDialog open={shareDlg} title="Share contact details?" message={<><p>The parent will see the tutor's name, phone and email on their Introductions page. Both parties have agreed.</p>{a.error && <Alert kind="error">{a.error}</Alert>}</>} confirmLabel="Share" busy={a.busy} onConfirm={share} onCancel={() => setShareDlg(false)} />
            <ConfirmDialog open={confirm} title={`Mark introduction as ${statusLabel(status)}?`} message={<>{a.error && <Alert kind="error">{a.error}</Alert>}</>} noteLabel="Reason" confirmLabel="Confirm" danger busy={a.busy} onConfirm={submitStatus} onCancel={() => setConfirm(false)} />
          </>
        );
      }}
    </Async>
  );
}

// ------------------------------------------------------------------ inquiries
export function InquiriesList() {
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const f = usePaged<Obj>("/admin/inquiries/", { status, category, search });
  return (
    <>
      <PageHeader title="Personal Inquiries" subtitle="Private messages from parents. Never shown publicly." />
      <div className="filters">
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="">Any status</option>
          {INQUIRY_STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
        </select>
        <select className="input" value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category">
          <option value="">Any category</option>
          {INQUIRY_CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        <input className="input" placeholder="Search" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search" />
      </div>
      <Async f={f}>
        {(d) => d.results.length === 0 ? <Empty title="No inquiries" /> : (
          <>
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Ref</th><th>From</th><th>Category</th><th>Status</th><th>Assigned</th><th>Received</th><th /></tr></thead>
              <tbody>
                {d.results.map((q) => (
                  <tr key={q.id}>
                    <td><strong>{q.reference}</strong></td>
                    <td>{q.parent_info?.full_name}</td>
                    <td>{q.category_display}</td>
                    <td><StatusBadge status={q.status} /></td>
                    <td>{q.assigned_to_name ?? "-"}</td>
                    <td>{fmtDate(q.created_at)}</td>
                    <td><Link className="btn btn-outline btn-sm" to={`/admin/inquiries/${q.id}`}>Open</Link></td>
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

export function InquiryDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const f = useFetch<Obj>(`/admin/inquiries/${id}/`);
  const a = useAction();
  const [reply, setReply] = useState("");
  const [replyStatus, setReplyStatus] = useState("awaiting_parent");
  const [notes, setNotes] = useState<string | null>(null);
  const [status, setStatus] = useState("");

  async function respond(e: FormEvent) {
    e.preventDefault();
    const r = await a.run(() => api.post(`/admin/inquiries/${id}/respond/`, { response: reply, status: replyStatus }));
    if (r) {
      setReply("");
      f.reload();
    }
  }
  async function saveNotes() {
    await a.run(() => api.patch(`/admin/inquiries/${id}/`, { internal_notes: notes }));
    setNotes(null);
    f.reload();
  }
  async function assign(adminId: number | null) {
    await a.run(() => api.patch(`/admin/inquiries/${id}/`, { assigned_to: adminId }));
    f.reload();
  }
  async function changeStatus() {
    await a.run(() => api.post(`/admin/inquiries/${id}/set-status/`, { status }));
    setStatus("");
    f.reload();
  }
  async function convert() {
    const r = await a.run(() => api.post<Obj>(`/admin/inquiries/${id}/convert-to-request/`));
    if (r) nav(`/admin/requests/${r.request}`);
  }

  return (
    <Async f={f}>
      {(q) => (
        <>
          <BackLink to="/admin/inquiries">Inquiries</BackLink>
          <PageHeader title={`${q.reference} · ${q.category_display}`} subtitle={<><StatusBadge status={q.status} /> {q.assigned_to_name ? `Assigned to ${q.assigned_to_name}` : "Unassigned"}</>}
            actions={q.converted_request ? <Link className="btn btn-outline" to={`/admin/requests/${q.converted_request}`}>Request {q.converted_request_reference}</Link> : <button className="btn btn-outline" onClick={convert} disabled={a.busy}>Convert to request</button>} />
          {a.error && <Alert kind="error">{a.error}</Alert>}
          <div className="grid cols-2">
            <div className="card">
              <h3>From</h3>
              <dl className="kv"><dt>Parent</dt><dd>{q.parent_info.full_name}</dd><dt>Email</dt><dd>{q.parent_info.email}</dd><dt>Phone</dt><dd>{q.parent_info.phone || "-"}</dd><dt>Prefers</dt><dd>{q.preferred_response}</dd>{q.about_tutor && <><dt>About tutor</dt><dd><Link to={`/admin/tutors/${q.about_tutor}`}>{q.about_tutor_name}</Link></dd></>}</dl>
              <p style={{ whiteSpace: "pre-wrap" }}>{q.message}</p>
              <p className="muted small">Received {fmtDateTime(q.created_at)}</p>
              <div className="row">
                {q.assigned_to !== user?.id && <button className="btn btn-outline btn-sm" onClick={() => assign(user!.id)} disabled={a.busy}>Assign to me</button>}
                {q.assigned_to && <button className="btn btn-ghost btn-sm" onClick={() => assign(null)} disabled={a.busy}>Unassign</button>}
              </div>
            </div>
            <div className="card">
              <h3>Reply to parent</h3>
              {q.admin_response && <Alert kind="info"><strong>Current reply:</strong> <span style={{ whiteSpace: "pre-wrap" }}>{q.admin_response}</span></Alert>}
              <form onSubmit={respond}>
                <Field label="Message" required><textarea className="input" value={reply} onChange={(e) => setReply(e.target.value)} maxLength={3000} /></Field>
                <Field label="Set status to">
                  <select className="input" value={replyStatus} onChange={(e) => setReplyStatus(e.target.value)}>
                    {INQUIRY_STATUSES.filter((s) => s !== "new").map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
                  </select>
                </Field>
                <button className="btn" disabled={!reply.trim() || a.busy}>Send reply</button>
              </form>
            </div>
          </div>

          <div className="grid cols-2 mt">
            <div className="card">
              <h3>Internal notes</h3>
              <p className="muted small">Visible to administrators only.</p>
              <textarea className="input" value={notes ?? q.internal_notes ?? ""} onChange={(e) => setNotes(e.target.value)} />
              <button className="btn btn-outline btn-sm mt" onClick={saveNotes} disabled={notes === null || a.busy}>Save notes</button>
            </div>
            <div className="card">
              <h3>Status</h3>
              <Field label="Change status to">
                <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
                  <option value="">Choose…</option>
                  {INQUIRY_STATUSES.filter((s) => s !== q.status).map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
                </select>
              </Field>
              <button className="btn btn-outline" onClick={changeStatus} disabled={!status || a.busy}>Update</button>
            </div>
          </div>
          <h2 className="mt-2">History</h2>
          <div className="card"><Timeline items={q.history} /></div>
        </>
      )}
    </Async>
  );
}

// ------------------------------------------------------------------ reports
function isoDaysAgo(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

export function Reports() {
  const [start, setStart] = useState(isoDaysAgo(30));
  const [end, setEnd] = useState(isoDaysAgo(0));
  const f = useFetch<Obj>(`/admin/reports/?start=${start}&end=${end}`);
  const list = (rows: Obj[] | undefined, key: string) => (rows ?? []).map((r) => ({ label: String(r[key]), value: r.count as number }));
  return (
    <>
      <PageHeader title="Reports" subtitle="Operational summary for a date range. Figures come directly from the database." />
      <div className="filters">
        <Field label="From" required><input className="input" type="date" value={start} max={end} onChange={(e) => setStart(e.target.value)} /></Field>
        <Field label="To" required><input className="input" type="date" value={end} min={start} onChange={(e) => setEnd(e.target.value)} /></Field>
      </div>
      <Async f={f}>
        {(r) => (
          <div className="grid cols-2">
            <div className="card"><h3>Requests by status</h3><BarList data={r.requests_by_status} /></div>
            <div className="card"><h3>Requests by source</h3><BarList data={r.requests_by_source} /></div>
            <div className="card"><h3>Most requested subjects</h3><BarList data={list(r.top_requested_subjects, "subject")} /></div>
            <div className="card"><h3>Requests per day</h3><BarList data={(r.requests_per_day ?? []).map((x: Obj) => ({ label: x.date, value: x.count }))} /></div>
            <div className="card"><h3>Jobs created, by status</h3><BarList data={r.jobs_by_status} /></div>
            <div className="card"><h3>Job applications by status</h3><BarList data={r.applications_by_status} /></div>
            <div className="card"><h3>Introductions by status</h3><BarList data={r.introductions_by_status} /></div>
            <div className="card"><h3>Tutors by status (all time)</h3><BarList data={r.tutors_by_status} /></div>
            <div className="card"><h3>Approved tutors per subject</h3><BarList data={list(r.approved_tutors_per_subject, "subject")} /></div>
          </div>
        )}
      </Async>
    </>
  );
}

// ------------------------------------------------------------------ audit logs
export function AuditLogs() {
  const [search, setSearch] = useState("");
  const [entity, setEntity] = useState("");
  const f = usePaged<Obj>("/admin/audit-logs/", { search, entity_type: entity }, );
  return (
    <>
      <PageHeader title="Audit Logs" subtitle="Important administrative actions. Entries contain no passwords or tokens." />
      <div className="filters">
        <input className="input" placeholder="Search action, detail or person" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search" />
        <input className="input" placeholder="Entity type (e.g. tutorprofile)" value={entity} onChange={(e) => setEntity(e.target.value)} aria-label="Entity type" />
      </div>
      <Async f={f}>
        {(d) => d.results.length === 0 ? <Empty title="No log entries" /> : (
          <>
            <div className="table-wrap"><table className="table">
              <thead><tr><th>When</th><th>Who</th><th>Action</th><th>Entity</th><th>Detail</th></tr></thead>
              <tbody>
                {d.results.map((l) => (
                  <tr key={l.id}>
                    <td className="small" style={{ whiteSpace: "nowrap" }}>{fmtDateTime(l.created_at)}</td>
                    <td>{l.actor_name}</td>
                    <td><code>{l.action}</code></td>
                    <td className="small">{l.entity_type} #{l.entity_id}</td>
                    <td className="small">{l.detail}</td>
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

// ------------------------------------------------------------------ settings: subjects, grade levels, locations
function CatalogEditor({ title, endpoint, fields, itemLabel }: {
  title: string;
  endpoint: string;
  fields: { key: string; label: string; type?: string; required?: boolean; placeholder?: string }[];
  itemLabel: (o: Obj) => string;
}) {
  const f = useFetch<Obj[]>(`/admin/${endpoint}/`);
  const a = useAction();
  const [form, setForm] = useState<Obj>({});

  async function add(e: FormEvent) {
    e.preventDefault();
    const body: Obj = {};
    for (const fl of fields) if (form[fl.key] !== undefined && form[fl.key] !== "") body[fl.key] = fl.type === "number" ? Number(form[fl.key]) : form[fl.key];
    const r = await a.run(() => api.post(`/admin/${endpoint}/`, body));
    if (r) {
      setForm({});
      invalidateReference();
      f.reload();
    }
  }
  async function toggle(o: Obj) {
    await a.run(() => api.patch(`/admin/${endpoint}/${o.id}/`, { is_active: !o.is_active }));
    invalidateReference();
    f.reload();
  }
  return (
    <div className="card">
      <h3>{title}</h3>
      {a.error && <Alert kind="error">{a.error}</Alert>}
      <form onSubmit={add} className="row" style={{ alignItems: "flex-end" }}>
        {fields.map((fl) => (
          <Field key={fl.key} label={fl.label} required={fl.required} error={a.fields[fl.key]}>
            <input className="input" type={fl.type ?? "text"} placeholder={fl.placeholder} value={form[fl.key] ?? ""} onChange={(e) => setForm({ ...form, [fl.key]: e.target.value })} />
          </Field>
        ))}
        <button className="btn btn-sm" disabled={a.busy}>Add</button>
      </form>
      <Async f={f}>
        {(items) => (
          <ul className="stack mt">
            {items.map((o) => (
              <li key={o.id} className="row" style={{ justifyContent: "space-between" }}>
                <span className={o.is_active ? "" : "muted"}>{itemLabel(o)} {!o.is_active && <span className="badge badge-gray">Inactive</span>}</span>
                <button className="btn btn-outline btn-sm" onClick={() => toggle(o)} disabled={a.busy}>{o.is_active ? "Deactivate" : "Activate"}</button>
              </li>
            ))}
          </ul>
        )}
      </Async>
    </div>
  );
}

export function Settings() {
  return (
    <>
      <PageHeader title="Settings" subtitle="Subjects, grade levels and locations are database records. Deactivate an item to hide it from new forms without losing history." />
      <div className="grid cols-3">
        <CatalogEditor title="Subjects" endpoint="subjects" fields={[{ key: "name", label: "Name", required: true }]} itemLabel={(o) => o.name} />
        <CatalogEditor title="Grade levels" endpoint="grade-levels" fields={[{ key: "name", label: "Name", required: true }, { key: "order", label: "Order", type: "number" }]} itemLabel={(o) => o.name} />
        <CatalogEditor title="Locations" endpoint="locations" fields={[{ key: "country", label: "Country", required: true, placeholder: "Ethiopia" }, { key: "city", label: "City", required: true, placeholder: "Addis Ababa" }, { key: "area", label: "Area", placeholder: "Bole" }]} itemLabel={(o) => o.label} />
      </div>
    </>
  );
}
