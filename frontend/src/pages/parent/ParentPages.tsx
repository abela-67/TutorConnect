import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { Avatar } from "../../components/TutorCard";
import TutorCard from "../../components/TutorCard";
import { Alert, Async, ConfirmDialog, Empty, Field, PageHeader, Pagination, StatusBadge } from "../../components/ui";
import { idOrNull, numOrNull, useAction, useFetch, useForm, usePaged, useReference } from "../../hooks";
import { INQUIRY_CATEGORIES, MODE_LABEL, fmtDate, money } from "../../labels";
import type { Inquiry, Page, ParentIntro, ParentRequest, TutorDetail } from "../../types";

// ------------------------------------------------------------------ overview
export function ParentOverview() {
  const { user } = useAuth();
  const reqs = useFetch<Page<ParentRequest>>("/parent/requests/?page_size=5");
  const intros = useFetch<Page<ParentIntro>>("/parent/introductions/?page_size=1");
  const open = reqs.data?.results.filter((r) => r.is_open) ?? [];
  return (
    <>
      <PageHeader title={`Welcome, ${user?.full_name.split(" ")[0] ?? ""}`} subtitle="Here is what is happening with your tutor requests." actions={<Link className="btn" to="/request-tutor">New tutor request</Link>} />
      <div className="grid cols-3">
        <Link className="card card-link" to="/parent/requests"><div className="stat">{reqs.data?.count ?? "–"}</div><div className="muted">Requests submitted</div></Link>
        <Link className="card card-link" to="/parent/introductions"><div className="stat">{intros.data?.count ?? "–"}</div><div className="muted">Introductions</div></Link>
        <Link className="card card-link" to="/tutors"><div className="stat">→</div><div className="muted">Browse tutors</div></Link>
      </div>
      <h2 className="mt-2">Recent requests</h2>
      <Async f={reqs}>
        {(d) => d.results.length === 0 ? (
          <Empty title="No requests yet" action={<Link className="btn" to="/request-tutor">Request a tutor</Link>}>
            Tell us the subject and grade, and we will help find the right tutor.
          </Empty>
        ) : (
          <div className="stack">
            {d.results.slice(0, 3).map((r) => <RequestCard key={r.id} r={r} />)}
            {open.length === 0 && <p className="muted small">You have no open requests.</p>}
          </div>
        )}
      </Async>
    </>
  );
}

function RequestCard({ r, onCancel }: { r: ParentRequest; onCancel?: () => void }) {
  return (
    <article className="card">
      <div className="row between">
        <div>
          <strong>{r.subject_name} · {r.grade_level_name}</strong>
          <div className="muted small">{r.reference} · submitted {fmtDate(r.created_at)}</div>
        </div>
        <StatusBadge status={r.status} label={r.status_display} />
      </div>
      <dl className="kv mt">
        <dt>Lessons</dt><dd>{MODE_LABEL[r.teaching_mode] ?? r.teaching_mode}{r.location_name && ` · ${r.location_name}`}</dd>
        <dt>Preferred tutor</dt><dd>{r.preferred_tutor_name ?? "Let the administrator suggest"}</dd>
        {r.budget_amount && <><dt>Budget</dt><dd>{money(r.budget_amount)}</dd></>}
        <dt>Latest update</dt><dd>{r.latest_update || "We have received your request."}</dd>
        {r.introductions > 0 && <><dt>Introductions</dt><dd><Link to="/parent/introductions">{r.introductions} arranged</Link></dd></>}
      </dl>
      {onCancel && r.is_open && <div className="form-actions"><button className="btn btn-outline btn-sm" onClick={onCancel}>Cancel request</button></div>}
    </article>
  );
}

// ------------------------------------------------------------------ requests
export function MyRequests() {
  const f = usePaged<ParentRequest>("/parent/requests/");
  const [cancel, setCancel] = useState<ParentRequest | null>(null);
  const a = useAction();
  async function doCancel() {
    if (!cancel) return;
    await a.run(() => api.post(`/parent/requests/${cancel.id}/cancel/`));
    setCancel(null);
    f.reload();
  }
  return (
    <>
      <PageHeader title="My requests" actions={<Link className="btn" to="/request-tutor">New request</Link>} />
      {a.error && <Alert kind="error">{a.error}</Alert>}
      <Async f={f}>
        {(d) => d.results.length === 0 ? (
          <Empty title="No requests yet" action={<Link className="btn" to="/request-tutor">Request a tutor</Link>}>Your requests and their progress will be listed here.</Empty>
        ) : (
          <>
            <div className="stack">{d.results.map((r) => <RequestCard key={r.id} r={r} onCancel={() => setCancel(r)} />)}</div>
            <Pagination page={f.page} count={d.count} onPage={f.setPage} />
          </>
        )}
      </Async>
      <ConfirmDialog open={!!cancel} title="Cancel this request?" message="The administrator will be told. You can always submit a new request later." confirmLabel="Cancel request" danger busy={a.busy} onConfirm={doCancel} onCancel={() => setCancel(null)} />
    </>
  );
}

// ------------------------------------------------------------------ new request (minimal form)
export function RequestTutor() {
  const [sp] = useSearchParams();
  const tutorId = sp.get("tutor");
  const ref = useReference();
  const { user } = useAuth();
  const nav = useNavigate();
  const tutor = useFetch<TutorDetail>(tutorId ? `/tutors/${tutorId}/` : null);
  const f = useForm({
    subject: "", grade_level: "", teaching_mode: "in_person",
    location: user?.default_location ? String(user.default_location) : "",
    preferred_gender: "", preferred_schedule: "", budget_amount: "", additional_requirements: "",
  });
  const a = useAction();
  const online = f.values.teaching_mode === "online";

  async function submit(e: FormEvent) {
    e.preventDefault();
    const body: Record<string, unknown> = {
      subject: idOrNull(f.values.subject), grade_level: idOrNull(f.values.grade_level), teaching_mode: f.values.teaching_mode,
      location: online ? null : idOrNull(f.values.location), preferred_gender: f.values.preferred_gender,
      preferred_schedule: f.values.preferred_schedule, budget_amount: numOrNull(f.values.budget_amount),
      additional_requirements: f.values.additional_requirements,
    };
    if (tutorId) body.preferred_tutor = Number(tutorId);
    const r = await a.run(() => api.post("/parent/requests/", body));
    if (r) nav("/parent/requests", { replace: true });
  }

  const subjects = tutor.data ? ref?.subjects.filter((s) => tutor.data!.subjects.some((x) => x.id === s.id)) : ref?.subjects;

  return (
    <div className="container section">
      <div className="form-narrow" style={{ margin: "0 auto" }}>
        <h1>{tutor.data ? `Request ${tutor.data.display_name}` : "Tell us what you need"}</h1>
        <p className="muted">
          {tutor.data
            ? "We will check the tutor's availability and coordinate an introduction. You do not message the tutor directly."
            : "Answer three quick questions and we will suggest suitable tutors. Everything else is optional."}
        </p>
        {tutor.data && <div className="card mb row"><Avatar name={tutor.data.display_name} photo={tutor.data.photo} /><div><strong>{tutor.data.display_name}</strong><div className="muted small">{tutor.data.subjects.map((s) => s.name).join(", ")}</div></div></div>}
        {tutor.error && <Alert kind="warning">That tutor is not available. You can still send a request and we will find a match.</Alert>}
        {a.error && <Alert kind="error">{a.error}</Alert>}
        <form className="card" onSubmit={submit} noValidate>
          <Field label="Subject" required error={a.fields.subject}>
            <select className="input" required {...f.bind("subject")}><option value="">Choose a subject</option>{subjects?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
          </Field>
          <Field label="Grade level" required error={a.fields.grade_level}>
            <select className="input" required {...f.bind("grade_level")}><option value="">Choose a grade</option>{ref?.grade_levels.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}</select>
          </Field>
          <Field label="Where should lessons happen?" required error={a.fields.teaching_mode}>
            <select className="input" {...f.bind("teaching_mode")}>{ref?.request_modes.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}</select>
          </Field>
          {!online && (
            <Field label="Area" required error={a.fields.location}>
              <select className="input" required {...f.bind("location")}><option value="">Choose an area</option>{ref?.locations.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}</select>
            </Field>
          )}
          <details className="more">
            <summary>Add more details (optional)</summary>
            {!tutorId && (
              <Field label="Tutor gender preference">
                <select className="input" {...f.bind("preferred_gender")}><option value="">No preference</option><option value="female">Female</option><option value="male">Male</option></select>
              </Field>
            )}
            <Field label="Preferred schedule" error={a.fields.preferred_schedule}><input className="input" placeholder="e.g. weekday evenings" {...f.bind("preferred_schedule")} /></Field>
            <Field label="Budget per hour (ETB)" error={a.fields.budget_amount}><input className="input" type="number" min={0} {...f.bind("budget_amount")} /></Field>
            <Field label="Anything else we should know?" hint="Please do not include your child's full name or address."><textarea className="input" {...f.bind("additional_requirements")} /></Field>
          </details>
          <button className="btn" style={{ width: "100%" }} disabled={a.busy}>{a.busy ? "Sending…" : "Send request"}</button>
          <p className="muted small mt">We will use the contact details on your account. We never share them without your agreement.</p>
        </form>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ introductions
export function MyIntroductions() {
  const f = usePaged<ParentIntro>("/parent/introductions/");
  return (
    <>
      <PageHeader title="My introductions" subtitle="Introductions arranged by the administrator for your requests." />
      <Async f={f}>
        {(d) => d.results.length === 0 ? (
          <Empty title="No introductions yet">When the administrator arranges an introduction to a tutor, it will appear here.</Empty>
        ) : (
          <>
            <div className="stack">
              {d.results.map((i) => (
                <div key={i.id} className="card">
                  <div className="row between"><span className="muted small">Request {i.reference} · {fmtDate(i.created_at)}</span><StatusBadge status={i.status} label={i.status_display} /></div>
                  <div className="mt"><TutorCard t={i.tutor} requestable={false} /></div>
                  {i.introduced_on && <p className="small mt">Introduction date: {fmtDate(i.introduced_on)}</p>}
                  {i.tutor_contact
                    ? <Alert kind="success"><strong>Contact shared with your agreement:</strong> {i.tutor_contact.name}{i.tutor_contact.phone && ` · ${i.tutor_contact.phone}`}{i.tutor_contact.email && ` · ${i.tutor_contact.email}`}</Alert>
                    : <p className="muted small mt">Contact details are shared only once you and the tutor have both agreed.</p>}
                </div>
              ))}
            </div>
            <Pagination page={f.page} count={d.count} onPage={f.setPage} />
          </>
        )}
      </Async>
    </>
  );
}

// ------------------------------------------------------------------ contact administrator
export function ContactAdmin() {
  const [sp] = useSearchParams();
  const tutorId = sp.get("tutor");
  const tutor = useFetch<TutorDetail>(tutorId ? `/tutors/${tutorId}/` : null);
  const list = usePaged<Inquiry>("/parent/inquiries/");
  const f = useForm({ category: tutorId ? "tutor_question" : "other", message: "", preferred_response: "any" });
  const a = useAction();
  const [sent, setSent] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSent(false);
    const body: Record<string, unknown> = { ...f.values };
    if (tutorId) body.about_tutor = Number(tutorId);
    const r = await a.run(() => api.post("/parent/inquiries/", body));
    if (r) {
      f.setValues({ ...f.values, message: "" });
      setSent(true);
      list.reload();
    }
  }

  return (
    <>
      <PageHeader title="Contact the administrator" subtitle="Your message is private. Only administrators can read it." />
      <div className="grid cols-2">
        <form className="card" onSubmit={submit}>
          {sent && <Alert kind="success">Thank you, your message was sent. We will reply here.</Alert>}
          {a.error && <Alert kind="error">{a.error}</Alert>}
          {tutor.data && <Alert>This message is about <strong>{tutor.data.display_name}</strong>.</Alert>}
          <Field label="What is this about?" required>
            <select className="input" {...f.bind("category")}>{INQUIRY_CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}</select>
          </Field>
          <Field label="Your message" required error={a.fields.message}><textarea className="input" required minLength={5} {...f.bind("message")} /></Field>
          <Field label="How should we reply?">
            <select className="input" {...f.bind("preferred_response")}><option value="any">Either is fine</option><option value="email">Email</option><option value="phone">Phone call</option></select>
          </Field>
          <button className="btn" disabled={a.busy}>{a.busy ? "Sending…" : "Send message"}</button>
        </form>

        <div>
          <h3>Your previous messages</h3>
          <Async f={list}>
            {(d) => d.results.length === 0 ? <p className="muted">No messages yet.</p> : (
              <div className="stack">
                {d.results.map((q) => (
                  <div className="card" key={q.id}>
                    <div className="row between"><strong>{q.category_display}</strong><StatusBadge status={q.status} label={q.status_display} /></div>
                    <div className="muted small">{q.reference} · {fmtDate(q.created_at)}{q.about_tutor_name && ` · about ${q.about_tutor_name}`}</div>
                    <p className="mt" style={{ whiteSpace: "pre-line" }}>{q.message}</p>
                    {q.admin_response && <Alert kind="info"><strong>Reply:</strong> <span style={{ whiteSpace: "pre-line" }}>{q.admin_response}</span></Alert>}
                  </div>
                ))}
                <Pagination page={list.page} count={d.count} onPage={list.setPage} />
              </div>
            )}
          </Async>
        </div>
      </div>
    </>
  );
}
