import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api";
import { Alert, Async, BackLink, ConfirmDialog, Empty, PageHeader, Pagination, StatusBadge, Timeline } from "../../components/ui";
import { useAction, useFetch, usePaged } from "../../hooks";
import { DOC_TYPES, LEVEL_LABEL, MODE_LABEL, TUTOR_STATUSES, fmtDate, fmtDateTime, fmtSize, humanize, money, statusLabel } from "../../labels";
import type { Obj } from "../../types";

// ------------------------------------------------------------------ overview
const TILES: [string, string, string][] = [
  ["pending_tutor_applications", "Pending tutor applications", "/admin/tutors"],
  ["pending_documents", "Documents awaiting review", "/admin/credentials"],
  ["tutors_with_changes_to_review", "Approved tutors with changes to review", "/admin/tutors?changes=1"],
  ["new_requests", "New parent requests", "/admin/requests?status=new"],
  ["unresolved_phone_requests", "Unresolved telephone requests", "/admin/phone"],
  ["new_inquiries", "New parent inquiries", "/admin/inquiries"],
  ["open_jobs", "Open tutoring jobs", "/admin/jobs"],
  ["pending_job_applications", "Pending job applications", "/admin/applications"],
  ["introductions_awaiting_completion", "Introductions awaiting completion", "/admin/introductions"],
  ["approved_tutors", "Approved tutors", "/admin/directory"],
  ["total_tutors", "Registered tutors", "/admin/users?role=tutor"],
  ["total_parents", "Parents", "/admin/users?role=parent"],
];

export function AdminOverview() {
  const f = useFetch<Obj>("/admin/stats/");
  return (
    <>
      <PageHeader title="Overview" subtitle="Live counts from the database." actions={<Link className="btn" to="/admin/phone/new">Record a phone request</Link>} />
      <Async f={f}>
        {(s) => (
          <div className="grid cols-3">
            {TILES.map(([key, label, to]) => (
              <Link key={key} to={to} className="card card-link">
                <div className="stat">{s[key] ?? 0}</div>
                <div className="muted">{label}</div>
              </Link>
            ))}
          </div>
        )}
      </Async>
    </>
  );
}

// ------------------------------------------------------------------ tutor applications / directory
export function AdminTutors({ directory = false }: { directory?: boolean }) {
  const params = new URLSearchParams(window.location.search);
  const [status, setStatus] = useState(directory ? "approved" : params.get("changes") ? "approved" : "under_review");
  const [search, setSearch] = useState("");
  const [changes, setChanges] = useState(Boolean(params.get("changes")));
  const f = usePaged<Obj>("/admin/tutors/", { status, search, has_unreviewed_changes: changes });
  return (
    <>
      <PageHeader title={directory ? "Tutor Directory" : "Tutor Applications"} subtitle={directory ? "All tutors, any status. Only Approved tutors appear publicly." : "Review applications and credentials."} />
      <div className="filters">
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="">All statuses</option>
          {TUTOR_STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
        </select>
        <input className="input" placeholder="Search name, email or phone" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search" />
        <label className="check"><input type="checkbox" checked={changes} onChange={(e) => setChanges(e.target.checked)} /> Changes awaiting review</label>
      </div>
      <Async f={f}>
        {(d) => d.results.length === 0 ? (
          <Empty title="No tutors match">Try a different status or search.</Empty>
        ) : (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Tutor</th><th>Status</th><th>Location</th><th>Docs to review</th><th>Submitted</th><th /></tr></thead>
                <tbody>
                  {d.results.map((t) => (
                    <tr key={t.id}>
                      <td><strong>{t.display_name}</strong><div className="muted small">{t.email}</div></td>
                      <td>
                        <StatusBadge status={t.status} />
                        {t.has_unreviewed_changes && <span className="badge badge-amber" style={{ marginLeft: 4 }}>Changes to review</span>}
                        {!t.account_active && <span className="badge badge-red" style={{ marginLeft: 4 }}>Account inactive</span>}
                      </td>
                      <td>{t.location_name ?? "-"}</td>
                      <td>{t.pending_documents}</td>
                      <td>{fmtDate(t.submitted_at)}</td>
                      <td><Link className="btn btn-outline btn-sm" to={`/admin/tutors/${t.id}`}>Open</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={f.page} count={d.count} onPage={f.setPage} />
          </>
        )}
      </Async>
    </>
  );
}

// ------------------------------------------------------------------ document review actions (shared)
export function DocumentActions({ d, onChanged }: { d: Obj; onChanged: () => void }) {
  const a = useAction();
  const [dlg, setDlg] = useState<"verified" | "rejected" | null>(null);

  const download = () => a.run(() => api.download(`/documents/${d.id}/download/`, d.original_name));
  async function review(note: string) {
    const ok = await a.run(() => api.post(`/admin/documents/${d.id}/review/`, { status: dlg, note }));
    if (ok !== undefined) {
      setDlg(null);
      onChanged();
    }
  }
  return (
    <>
      <div className="row">
        <button className="btn btn-outline btn-sm" onClick={download} disabled={a.busy}>Download</button>
        {d.status !== "verified" && <button className="btn btn-sm" onClick={() => setDlg("verified")}>Verify</button>}
        {d.status !== "rejected" && <button className="btn btn-danger btn-sm" onClick={() => setDlg("rejected")}>Reject</button>}
      </div>
      {a.error && !dlg && <div className="err small">{a.error}</div>}
      <ConfirmDialog
        open={dlg !== null}
        title={dlg === "verified" ? "Mark document as verified?" : "Reject this document?"}
        message={<>
          <p>{d.original_name}</p>
          {dlg === "verified" && <p className="muted small">Verified means you reviewed this document. It does not verify identity or run a background check.</p>}
          {a.error && <Alert kind="error">{a.error}</Alert>}
        </>}
        noteLabel={dlg === "rejected" ? "Reason (shown to the tutor)" : "Note"}
        noteRequired={dlg === "rejected"}
        confirmLabel={dlg === "verified" ? "Mark verified" : "Reject"}
        danger={dlg === "rejected"}
        busy={a.busy}
        onConfirm={review}
        onCancel={() => setDlg(null)}
      />
    </>
  );
}

// ------------------------------------------------------------------ tutor detail + decisions
type Decision = { action: string; label: string; needsNote: boolean; danger?: boolean; text: string };
const DECISIONS: Record<string, Decision> = {
  approve: { action: "approve", label: "Approve", needsNote: false, text: "The profile becomes publicly listed and the tutor can use the job board." },
  "request-info": { action: "request-info", label: "Request more information", needsNote: true, text: "Tell the tutor exactly what is needed." },
  reject: { action: "reject", label: "Reject", needsNote: true, danger: true, text: "The tutor will see your explanation." },
  suspend: { action: "suspend", label: "Suspend", needsNote: true, danger: true, text: "The profile is removed from public search immediately." },
  reinstate: { action: "reinstate", label: "Reinstate", needsNote: false, text: "The profile is listed again." },
};

function decisionsFor(t: Obj): Decision[] {
  switch (t.status) {
    case "under_review": return [DECISIONS.approve, DECISIONS["request-info"], DECISIONS.reject];
    case "info_required": return [DECISIONS.approve, DECISIONS.reject];
    case "approved": return [...(t.has_unreviewed_changes ? [{ ...DECISIONS.approve, label: "Approve changes" }] : []), DECISIONS.suspend];
    case "suspended": return [DECISIONS.reinstate];
    default: return [];
  }
}

export function AdminTutorDetail() {
  const { id } = useParams();
  const f = useFetch<Obj>(`/admin/tutors/${id}/`);
  const a = useAction();
  const [dlg, setDlg] = useState<Decision | null>(null);

  async function decide(note: string) {
    if (!dlg) return;
    const r = await a.run(() => api.post<Obj>(`/admin/tutors/${id}/${dlg.action}/`, { note }));
    if (r) {
      setDlg(null);
      f.reload();
    }
  }
  async function toggleQualification(q: Obj) {
    await a.run(() => api.post(`/admin/qualifications/${q.id}/verify/`, { verified: !q.verified }));
    f.reload();
  }

  return (
    <Async f={f}>
      {(t) => (
        <>
          <BackLink to="/admin/tutors">Tutor applications</BackLink>
          <PageHeader
            title={t.display_name}
            subtitle={<><StatusBadge status={t.status} /> {t.has_unreviewed_changes && <span className="badge badge-amber">Changes awaiting review</span>} {!t.account_active && <span className="badge badge-red">Account inactive</span>}</>}
            actions={decisionsFor(t).map((dc) => (
              <button key={dc.action + dc.label} className={`btn ${dc.danger ? "btn-danger" : ""}`} onClick={() => { a.setError(null); setDlg(dc); }}>{dc.label}</button>
            ))}
          />
          {a.error && !dlg && <Alert kind="error">{a.error}</Alert>}
          {t.status_note && <Alert kind="info"><strong>Last decision note:</strong> {t.status_note}</Alert>}

          <div className="grid cols-2">
            <div className="card">
              <h3>Contact (private)</h3>
              <dl className="kv">
                <dt>Email</dt><dd>{t.email}</dd>
                <dt>Phone</dt><dd>{t.phone || "-"}</dd>
                <dt>Location</dt><dd>{t.location_name ?? "-"}</dd>
                <dt>Submitted</dt><dd>{fmtDateTime(t.submitted_at)}</dd>
                <dt>Last review</dt><dd>{t.reviewed_at ? `${fmtDateTime(t.reviewed_at)} by ${t.reviewed_by_name ?? "-"}` : "-"}</dd>
              </dl>
            </div>
            <div className="card">
              <h3>Teaching</h3>
              <dl className="kv">
                <dt>Subjects</dt><dd>{t.subjects.map((s: Obj) => s.name).join(", ") || "-"}</dd>
                <dt>Grades</dt><dd>{t.grade_levels.map((g: Obj) => g.name).join(", ") || "-"}</dd>
                <dt>Mode</dt><dd>{MODE_LABEL[t.teaching_mode] ?? t.teaching_mode}</dd>
                <dt>Experience</dt><dd>{t.years_experience} years</dd>
                <dt>Rate</dt><dd>{money(t.rate_amount, t.rate_unit) ?? "-"}</dd>
                <dt>Gender</dt><dd>{t.gender ? `${humanize(t.gender)}${t.show_gender ? "" : " (hidden from public)"}` : "Not provided"}</dd>
                <dt>Languages</dt><dd>{(t.languages ?? []).join(", ") || "-"}</dd>
              </dl>
            </div>
          </div>

          <div className="card mt">
            <h3>Biography &amp; methods <span className="muted small">(written by the tutor, not verified)</span></h3>
            <p style={{ whiteSpace: "pre-wrap" }}>{t.bio || "-"}</p>
            {t.teaching_methods && <p style={{ whiteSpace: "pre-wrap" }}>{t.teaching_methods}</p>}
          </div>

          <h2 className="mt-2">Qualifications</h2>
          {t.qualifications.length === 0 ? <p className="muted">None entered.</p> : (
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Qualification</th><th>Institution</th><th>Year</th><th>Verified</th><th /></tr></thead>
              <tbody>
                {t.qualifications.map((q: Obj) => (
                  <tr key={q.id}>
                    <td><strong>{q.title}</strong><div className="muted small">{LEVEL_LABEL[q.level] ?? q.level}{q.field_of_study ? ` · ${q.field_of_study}` : ""}</div></td>
                    <td>{q.institution}</td>
                    <td>{q.year ?? "-"}</td>
                    <td>{q.verified ? <span className="badge badge-green">Verified {fmtDate(q.verified_at)}</span> : <span className="badge badge-gray">Not verified</span>}</td>
                    <td><button className="btn btn-outline btn-sm" onClick={() => toggleQualification(q)} disabled={a.busy}>{q.verified ? "Remove verification" : "Mark verified"}</button></td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}

          <h2 className="mt-2">Credential documents</h2>
          {t.documents.length === 0 ? <p className="muted">No documents uploaded.</p> : (
            <div className="table-wrap"><table className="table">
              <thead><tr><th>File</th><th>Type</th><th>Linked to</th><th>Status</th><th>Uploaded</th><th /></tr></thead>
              <tbody>
                {t.documents.map((d: Obj) => (
                  <tr key={d.id}>
                    <td>{d.original_name}<div className="muted small">{fmtSize(d.size)}</div></td>
                    <td>{DOC_TYPES.find((x) => x.value === d.doc_type)?.label ?? d.doc_type}</td>
                    <td>{d.qualification_title ?? "-"}</td>
                    <td><StatusBadge status={d.status} />{d.reviewer_note && <div className="muted small">{d.reviewer_note}</div>}</td>
                    <td>{fmtDate(d.uploaded_at)}</td>
                    <td><DocumentActions d={d} onChanged={f.reload} /></td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          )}

          <h2 className="mt-2">Decision history</h2>
          <div className="card"><Timeline items={t.history} /></div>

          <ConfirmDialog
            open={dlg !== null}
            title={dlg ? `${dlg.label}: ${t.display_name}` : ""}
            message={<>{dlg && <p>{dlg.text}</p>}{a.error && <Alert kind="error">{a.error}</Alert>}</>}
            noteLabel={dlg?.needsNote ? "Explanation" : "Note"}
            noteRequired={dlg?.needsNote}
            confirmLabel={dlg?.label}
            danger={dlg?.danger}
            busy={a.busy}
            onConfirm={decide}
            onCancel={() => setDlg(null)}
          />
        </>
      )}
    </Async>
  );
}

// ------------------------------------------------------------------ credential verification queue
export function AdminCredentials() {
  const [status, setStatus] = useState("pending");
  const f = usePaged<Obj>("/admin/documents/", { status });
  return (
    <>
      <PageHeader title="Credential Verification" subtitle="Review uploaded documents. Downloads are logged." />
      <div className="filters">
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="">All</option>
          <option value="pending">Pending review</option>
          <option value="verified">Verified</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>
      <Async f={f}>
        {(d) => d.results.length === 0 ? (
          <Empty title="Nothing to review">No documents match this filter.</Empty>
        ) : (
          <>
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Tutor</th><th>File</th><th>Type</th><th>Linked to</th><th>Status</th><th>Uploaded</th><th /></tr></thead>
              <tbody>
                {d.results.map((x) => (
                  <tr key={x.id}>
                    <td><Link to={`/admin/tutors/${x.tutor}`}>{x.tutor_name}</Link></td>
                    <td>{x.original_name}<div className="muted small">{fmtSize(x.size)}</div></td>
                    <td>{DOC_TYPES.find((t) => t.value === x.doc_type)?.label ?? x.doc_type}</td>
                    <td>{x.qualification_title ?? "-"}</td>
                    <td><StatusBadge status={x.status} /></td>
                    <td>{fmtDate(x.uploaded_at)}</td>
                    <td><DocumentActions d={x} onChanged={f.reload} /></td>
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

// ------------------------------------------------------------------ user management (parents & tutors)
export function AdminUsers() {
  const params = new URLSearchParams(window.location.search);
  const [role, setRole] = useState(params.get("role") ?? "parent");
  const [active, setActive] = useState("");
  const [search, setSearch] = useState("");
  const f = usePaged<Obj>("/admin/users/", { role, is_active: active, search });
  const a = useAction();
  const [target, setTarget] = useState<{ user: Obj; activate: boolean } | null>(null);

  async function toggle() {
    if (!target) return;
    const ok = await a.run(() => api.post(`/admin/users/${target.user.id}/${target.activate ? "reactivate" : "suspend"}/`));
    if (ok !== undefined) {
      setTarget(null);
      f.reload();
    }
  }
  return (
    <>
      <PageHeader title="Parent & Tutor Accounts" subtitle="Suspending an account blocks sign-in and removes tutors from public search." />
      <div className="filters">
        <select className="input" value={role} onChange={(e) => setRole(e.target.value)} aria-label="Role">
          <option value="parent">Parents</option>
          <option value="tutor">Tutors</option>
          <option value="admin">Administrators</option>
        </select>
        <select className="input" value={active} onChange={(e) => setActive(e.target.value)} aria-label="Account state">
          <option value="">Active and suspended</option>
          <option value="true">Active</option>
          <option value="false">Suspended</option>
        </select>
        <input className="input" placeholder="Search name, email or phone" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search" />
      </div>
      {a.error && !target && <Alert kind="error">{a.error}</Alert>}
      <Async f={f}>
        {(d) => d.results.length === 0 ? <Empty title="No accounts match" /> : (
          <>
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Joined</th><th>State</th><th /></tr></thead>
              <tbody>
                {d.results.map((u) => (
                  <tr key={u.id}>
                    <td>{u.full_name}</td><td>{u.email}</td><td>{u.phone || "-"}</td><td>{fmtDate(u.created_at)}</td>
                    <td>{u.is_active ? <span className="badge badge-green">Active</span> : <span className="badge badge-red">Suspended</span>}</td>
                    <td>
                      {u.role !== "admin" && (
                        <button className={`btn btn-sm ${u.is_active ? "btn-danger" : "btn-outline"}`} onClick={() => { a.setError(null); setTarget({ user: u, activate: !u.is_active }); }}>
                          {u.is_active ? "Suspend" : "Reactivate"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table></div>
            <Pagination page={f.page} count={d.count} onPage={f.setPage} />
          </>
        )}
      </Async>
      <ConfirmDialog
        open={target !== null}
        title={target?.activate ? "Reactivate this account?" : "Suspend this account?"}
        message={<>{target && <p>{target.user.full_name} ({target.user.email})</p>}{a.error && <Alert kind="error">{a.error}</Alert>}</>}
        confirmLabel={target?.activate ? "Reactivate" : "Suspend"}
        danger={!target?.activate}
        busy={a.busy}
        onConfirm={toggle}
        onCancel={() => setTarget(null)}
      />
    </>
  );
}
