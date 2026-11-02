import { FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../api";
import { Alert, Async, BackLink, ConfirmDialog, Empty, Field, PageHeader, Pagination, Spinner, StatusBadge, Timeline } from "../../components/ui";
import { numOrNull, useAction, useFetch, useForm, usePaged, useReference } from "../../hooks";
import { APPLICATION_STATUSES, JOB_STATUSES, MODE_LABEL, fmtDate, money, statusLabel } from "../../labels";
import type { Obj } from "../../types";

// ------------------------------------------------------------------ list
export function JobsList() {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const f = usePaged<Obj>("/admin/jobs/", { status, search });
  return (
    <>
      <PageHeader title="Tutoring Jobs" subtitle="Only administrators can create and publish jobs." actions={<Link className="btn" to="/admin/jobs/new">New job</Link>} />
      <div className="filters">
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="">Any status</option>
          {JOB_STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
        </select>
        <input className="input" placeholder="Search title or subject" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search" />
      </div>
      <Async f={f}>
        {(d) => d.results.length === 0 ? (
          <Empty title="No jobs yet" action={<Link className="btn" to="/admin/jobs/new">Create a job</Link>}>Create a job from a parent request, or start a blank one.</Empty>
        ) : (
          <>
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Job</th><th>Status</th><th>Where / how</th><th>Applicants</th><th>Deadline</th><th>Source</th><th /></tr></thead>
              <tbody>
                {d.results.map((j) => (
                  <tr key={j.id}>
                    <td><strong>{j.reference}</strong><div>{j.title}</div></td>
                    <td><StatusBadge status={j.status} /></td>
                    <td>{[j.location_name, MODE_LABEL[j.teaching_mode]].filter(Boolean).join(" · ") || "-"}</td>
                    <td>{j.application_count}</td>
                    <td>{j.application_deadline ? fmtDate(j.application_deadline) : "-"}</td>
                    <td>{j.source_request ? <Link to={`/admin/requests/${j.source_request}`}>{j.source_request_reference}</Link> : <span className="muted">Direct</span>}</td>
                    <td><Link className="btn btn-outline btn-sm" to={`/admin/jobs/${j.id}`}>Open</Link></td>
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

// ------------------------------------------------------------------ form (create + edit)
function JobForm({ initial, onSaved }: { initial?: Obj; onSaved: (j: Obj) => void }) {
  const ref = useReference();
  const a = useAction();
  const edit = Boolean(initial?.id);
  const { values, bind } = useForm({
    title: initial?.title ?? "",
    subject: initial?.subject ?? "",
    grade_level: initial?.grade_level ?? "",
    location: initial?.location ?? "",
    teaching_mode: initial?.teaching_mode ?? "in_person",
    preferred_schedule: initial?.preferred_schedule ?? "",
    frequency: initial?.frequency ?? "",
    duration: initial?.duration ?? "",
    payment_amount: initial?.payment_amount ?? "",
    payment_note: initial?.payment_note ?? "",
    required_qualifications: initial?.required_qualifications ?? "",
    additional_requirements: initial?.additional_requirements ?? "",
    application_deadline: initial?.application_deadline ?? "",
    internal_notes: initial?.internal_notes ?? "",
  });
  if (!ref) return <Spinner />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const body = {
      ...values,
      subject: numOrNull(values.subject),
      grade_level: numOrNull(values.grade_level),
      location: numOrNull(values.location),
      payment_amount: values.payment_amount === "" ? null : values.payment_amount,
      application_deadline: values.application_deadline || null,
    };
    const j = await a.run(() => (edit ? api.patch<Obj>(`/admin/jobs/${initial!.id}/`, body) : api.post<Obj>("/admin/jobs/", body)));
    if (j) onSaved(j);
  }
  return (
    <form onSubmit={submit} noValidate>
      {a.error && <Alert kind="error">{a.error}</Alert>}
      <Alert kind="warning">Everything except <strong>internal notes</strong> is visible to every approved tutor. Never include the parent's name, phone, email, address or the child's details. Phone numbers and emails are rejected automatically.</Alert>
      <div className="grid cols-2">
        <Field label="Job title" required error={a.fields.title}><input className="input" {...bind("title")} maxLength={150} placeholder="Grade 10 Mathematics Tutor" /></Field>
        <Field label="Teaching mode" required error={a.fields.teaching_mode}>
          <select className="input" {...bind("teaching_mode")}>{ref.request_modes.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}</select>
        </Field>
        <Field label="Subject" required hint="Required to publish." error={a.fields.subject}>
          <select className="input" {...bind("subject")}><option value="">Choose…</option>{ref.subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
        </Field>
        <Field label="Grade level" required hint="Required to publish." error={a.fields.grade_level}>
          <select className="input" {...bind("grade_level")}><option value="">Choose…</option>{ref.grade_levels.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}</select>
        </Field>
        <Field label="General location" hint="Area only, never an address. Required unless online." error={a.fields.location}>
          <select className="input" {...bind("location")}><option value="">None / online</option>{ref.locations.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}</select>
        </Field>
        <Field label="Application deadline" error={a.fields.application_deadline}><input className="input" type="date" {...bind("application_deadline")} /></Field>
        <Field label="Preferred schedule" error={a.fields.preferred_schedule}><input className="input" {...bind("preferred_schedule")} maxLength={200} placeholder="Weekday evenings" /></Field>
        <Field label="Lesson frequency" error={a.fields.frequency}><input className="input" {...bind("frequency")} maxLength={100} placeholder="3 days per week" /></Field>
        <Field label="Expected duration" error={a.fields.duration}><input className="input" {...bind("duration")} maxLength={100} placeholder="One school term" /></Field>
        <Field label="Payment amount (ETB)" error={a.fields.payment_amount}><input className="input" type="number" min="0" step="0.01" {...bind("payment_amount")} /></Field>
        <Field label="Payment note" error={a.fields.payment_note}><input className="input" {...bind("payment_note")} maxLength={150} placeholder="Negotiable" /></Field>
      </div>
      <Field label="Required qualifications or experience" error={a.fields.required_qualifications}><textarea className="input" {...bind("required_qualifications")} maxLength={1000} /></Field>
      <Field label="Additional requirements" error={a.fields.additional_requirements}><textarea className="input" {...bind("additional_requirements")} maxLength={1500} /></Field>
      <Field label="Internal notes (administrators only)" error={a.fields.internal_notes}><textarea className="input" {...bind("internal_notes")} /></Field>
      <div className="form-actions"><button className="btn" disabled={a.busy}>{a.busy ? "Saving…" : edit ? "Save changes" : "Save as draft"}</button></div>
    </form>
  );
}

export function NewJob() {
  const nav = useNavigate();
  return (
    <>
      <BackLink to="/admin/jobs">Jobs</BackLink>
      <PageHeader title="New tutoring job" subtitle="Saved as a draft. Nothing is visible to tutors until you publish." />
      <div className="card"><JobForm onSaved={(j) => nav(`/admin/jobs/${j.id}`)} /></div>
    </>
  );
}

// ------------------------------------------------------------------ application actions (shared with the all-applications page)
export function ApplicationActions({ app, onChanged }: { app: Obj; onChanged: () => void }) {
  const a = useAction();
  const [dlg, setDlg] = useState<"selected" | "not_selected" | null>(null);

  async function setStatus(status: string, note = "") {
    const r = await a.run(() => api.post(`/admin/applications/${app.id}/set-status/`, { status, note }));
    if (r !== undefined) {
      setDlg(null);
      onChanged();
    }
  }
  if (app.status === "withdrawn") return <span className="muted small">Withdrawn by tutor</span>;
  return (
    <>
      <div className="row">
        {app.status !== "under_review" && app.status !== "selected" && <button className="btn btn-outline btn-sm" disabled={a.busy} onClick={() => setStatus("under_review")}>Review</button>}
        {app.status !== "shortlisted" && app.status !== "selected" && <button className="btn btn-outline btn-sm" disabled={a.busy} onClick={() => setStatus("shortlisted")}>Shortlist</button>}
        {app.status !== "selected" && <button className="btn btn-sm" disabled={a.busy} onClick={() => { a.setError(null); setDlg("selected"); }}>Select</button>}
        {app.status !== "not_selected" && <button className="btn btn-danger btn-sm" disabled={a.busy} onClick={() => { a.setError(null); setDlg("not_selected"); }}>Not selected</button>}
      </div>
      {a.error && !dlg && <div className="err small">{a.error}</div>}
      <ConfirmDialog
        open={dlg !== null}
        title={dlg === "selected" ? `Select ${app.tutor_profile.display_name}?` : `Mark ${app.tutor_profile.display_name} as not selected?`}
        message={<>
          {dlg === "selected" ? <p>The tutor is notified and the job moves to <strong>Tutor Selected</strong>. Selecting does not share anyone's contact details; arrange the introduction separately.</p> : <p>The tutor is notified.</p>}
          {a.error && <Alert kind="error">{a.error}</Alert>}
        </>}
        noteLabel="Note (internal)"
        confirmLabel={dlg === "selected" ? "Select tutor" : "Mark not selected"}
        danger={dlg === "not_selected"}
        busy={a.busy}
        onConfirm={(note) => setStatus(dlg!, note)}
        onCancel={() => setDlg(null)}
      />
    </>
  );
}

const FIT_LABELS: [string, string][] = [["subject", "Subject"], ["grade_level", "Grade"], ["teaching_mode", "Mode"], ["same_location", "Same area"]];

function FitChips({ fit }: { fit: Obj }) {
  return <>{FIT_LABELS.map(([k, l]) => <span key={k} className={`badge ${fit[k] ? "badge-green" : "badge-gray"}`} style={{ margin: 2 }}>{fit[k] ? "✓" : "✗"} {l}</span>)}</>;
}

function ApplicantTable({ apps, onChanged }: { apps: Obj[]; onChanged: () => void }) {
  return (
    <div className="table-wrap"><table className="table">
      <thead><tr><th>Tutor</th><th>Fit with job</th><th>Credentials</th><th>Message</th><th>Status</th><th>Decision</th></tr></thead>
      <tbody>
        {apps.map((a) => (
          <tr key={a.id}>
            <td>
              <Link to={`/admin/tutors/${a.tutor}`}><strong>{a.tutor_profile.display_name}</strong></Link>
              <div className="muted small">{a.tutor_profile.location?.label ?? "-"} · {a.tutor_profile.years_experience} yrs · {money(a.tutor_profile.rate_amount, a.tutor_profile.rate_unit) ?? "no rate"}</div>
              {a.job_title && <div className="small"><Link to={`/admin/jobs/${a.job}`}>{a.job_reference} {a.job_title}</Link></div>}
            </td>
            <td><FitChips fit={a.fit} /></td>
            <td className="small">
              {a.tutor_profile.verified_documents} verified doc(s)<br />{a.tutor_profile.verified_qualifications} verified qualification(s)
              {a.tutor_profile.has_unreviewed_changes && <div><span className="badge badge-amber">Changes awaiting review</span></div>}
            </td>
            <td className="small" style={{ maxWidth: 220 }}>{a.message || <span className="muted">-</span>}</td>
            <td><StatusBadge status={a.status} /><div className="muted small">{fmtDate(a.created_at)}</div></td>
            <td><ApplicationActions app={a} onChanged={onChanged} /></td>
          </tr>
        ))}
      </tbody>
    </table></div>
  );
}

export function ApplicationsList() {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const f = usePaged<Obj>("/admin/applications/", { status, search });
  return (
    <>
      <PageHeader title="Job Applications" subtitle="Applications are private to administrators and the applying tutor." />
      <div className="filters">
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="">Any status</option>
          {APPLICATION_STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
        </select>
        <input className="input" placeholder="Search tutor or job" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search" />
      </div>
      <Async f={f}>
        {(d) => d.results.length === 0 ? <Empty title="No applications" /> : (
          <>
            <ApplicantTable apps={d.results} onChanged={f.reload} />
            <Pagination page={f.page} count={d.count} onPage={f.setPage} />
          </>
        )}
      </Async>
    </>
  );
}

// ------------------------------------------------------------------ detail
export function JobDetail() {
  const { id } = useParams();
  const f = useFetch<Obj>(`/admin/jobs/${id}/`);
  const apps = useFetch<Obj[]>(`/admin/jobs/${id}/applications/`);
  const a = useAction();
  const [target, setTarget] = useState("");
  const [dlg, setDlg] = useState<null | "status" | "finalize">(null);
  const [outcome, setOutcome] = useState("");

  const reloadAll = () => {
    f.reload();
    apps.reload();
  };
  async function publish() {
    const j = await a.run(() => api.post<Obj>(`/admin/jobs/${id}/publish/`));
    if (j) reloadAll();
  }
  async function changeStatus(note: string) {
    const j = await a.run(() => api.post<Obj>(`/admin/jobs/${id}/set-status/`, { status: target, note }));
    if (j) {
      setDlg(null);
      setTarget("");
      reloadAll();
    }
  }
  async function finalize() {
    const j = await a.run(() => api.post<Obj>(`/admin/jobs/${id}/finalize/`, { outcome }));
    if (j) {
      setDlg(null);
      reloadAll();
    }
  }
  const needsNote = target === "closed" || target === "cancelled";

  return (
    <Async f={f}>
      {(j) => (
        <>
          <BackLink to="/admin/jobs">Jobs</BackLink>
          <PageHeader
            title={`${j.reference} · ${j.title}`}
            subtitle={<><StatusBadge status={j.status} /> {j.source_request ? <>From <Link to={`/admin/requests/${j.source_request}`}>{j.source_request_reference}</Link></> : "Created directly"}</>}
            actions={j.status === "draft" ? <button className="btn" onClick={publish} disabled={a.busy}>Publish job</button> : undefined}
          />
          {a.error && !dlg && <Alert kind="error">{a.error}</Alert>}
          {j.status === "draft" && <Alert kind="info">This job is a draft and is not visible to tutors. Review the text for private details, then publish.</Alert>}

          <div className="grid cols-2">
            <div className="card">
              <h3>What tutors see</h3>
              <dl className="kv">
                <dt>Subject</dt><dd>{j.subject_name ?? "-"}</dd>
                <dt>Grade</dt><dd>{j.grade_level_name ?? "-"}</dd>
                <dt>Location</dt><dd>{j.location_name ?? "-"}</dd>
                <dt>Mode</dt><dd>{MODE_LABEL[j.teaching_mode] ?? "-"}</dd>
                <dt>Schedule</dt><dd>{j.preferred_schedule || "-"}</dd>
                <dt>Frequency</dt><dd>{j.frequency || "-"}</dd>
                <dt>Duration</dt><dd>{j.duration || "-"}</dd>
                <dt>Payment</dt><dd>{[money(j.payment_amount), j.payment_note].filter(Boolean).join(" · ") || "-"}</dd>
                <dt>Deadline</dt><dd>{j.application_deadline ? fmtDate(j.application_deadline) : "-"}</dd>
              </dl>
              {j.required_qualifications && <p className="small">{j.required_qualifications}</p>}
              {j.additional_requirements && <p className="small">{j.additional_requirements}</p>}
            </div>
            {j.status !== "draft" && (
              <div className="card">
                <h3>Manage status</h3>
                <p className="muted small">Only <strong>Open</strong> jobs accept new applications. Selecting a tutor moves the job to Tutor Selected automatically.</p>
                <Field label="Change status to">
                  <select className="input" value={target} onChange={(e) => setTarget(e.target.value)}>
                    <option value="">Choose…</option>
                    {JOB_STATUSES.filter((s) => s !== "draft" && s !== j.status).map((s) => <option key={s} value={s}>{s === "open" && ["closed"].includes(j.status) ? "Open (reopen)" : statusLabel(s)}</option>)}
                  </select>
                </Field>
                <div className="row">
                  <button className="btn" disabled={!target || a.busy} onClick={() => { a.setError(null); setDlg("status"); }}>Update status</button>
                  {["tutor_selected", "shortlisting", "applications_under_review", "open"].includes(j.status) && (
                    <button className="btn btn-outline" onClick={() => { a.setError(null); setDlg("finalize"); }}>Finalize (mark filled)</button>
                  )}
                </div>
                {j.outcome && <p className="small"><strong>Outcome:</strong> {j.outcome}</p>}
              </div>
            )}
          </div>

          <h2 className="mt-2">Applications ({apps.data?.length ?? 0})</h2>
          <Async f={apps}>
            {(list) => list.length === 0 ? <Empty title="No applications yet">{j.status === "draft" ? "Publish the job to let tutors apply." : "Approved tutors who express interest will appear here."}</Empty> : <ApplicantTable apps={list} onChanged={reloadAll} />}
          </Async>

          <details className="card mt-2">
            <summary><strong>Edit job details</strong></summary>
            <div className="mt"><JobForm initial={j} onSaved={() => f.reload()} /></div>
          </details>

          <h2 className="mt-2">History</h2>
          <div className="card"><Timeline items={j.history} /></div>

          <ConfirmDialog
            open={dlg === "status"}
            title={`Change status to ${statusLabel(target)}?`}
            message={<>{needsNote && <p>Tutors with active applications will be notified. Explain why.</p>}{a.error && <Alert kind="error">{a.error}</Alert>}</>}
            noteLabel={needsNote ? "Reason" : "Note"}
            noteRequired={needsNote}
            confirmLabel="Update status"
            danger={needsNote}
            busy={a.busy}
            onConfirm={changeStatus}
            onCancel={() => setDlg(null)}
          />
          <ConfirmDialog
            open={dlg === "finalize"}
            title="Finalize this job?"
            message={<>
              <p>Requires a selected tutor. The job becomes <strong>Filled</strong> and all other active applicants are marked Not Selected and notified.</p>
              <Field label="Outcome notes"><textarea className="input" value={outcome} onChange={(e) => setOutcome(e.target.value)} /></Field>
              {a.error && <Alert kind="error">{a.error}</Alert>}
            </>}
            confirmLabel="Finalize job"
            busy={a.busy}
            onConfirm={finalize}
            onCancel={() => setDlg(null)}
          />
        </>
      )}
    </Async>
  );
}
