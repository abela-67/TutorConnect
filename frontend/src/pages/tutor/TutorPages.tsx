import { ChangeEvent, FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { Avatar } from "../../components/TutorCard";
import { Alert, Async, BackLink, ConfirmDialog, Empty, Field, PageHeader, Pagination, StatusBadge } from "../../components/ui";
import { idOrNull, numOrNull, useAction, useFetch, useForm, usePaged, useReference } from "../../hooks";
import { DOC_TYPES, LEVEL_LABEL, MODE_LABEL, fmtDate, fmtSize, fmtTime, humanize, money } from "../../labels";
import type { JobSummary, MyDocument, Page, Qualification, SelfProfile, Slot, TutorApplication } from "../../types";

const LOCKED = ["under_review", "suspended"];

const STATUS_HELP: Record<string, string> = {
  draft: "Complete the items below, then submit your application for review.",
  pending_submission: "Your profile is complete. Submit it for administrator review.",
  under_review: "An administrator is reviewing your application. You can't edit it until the review is finished.",
  info_required: "The administrator needs more information. Read the note below, update your profile or documents, then resubmit.",
  approved: "Your profile is approved and visible to parents. You can browse tutoring jobs.",
  rejected: "Your application was not approved. See the reason below.",
  suspended: "Your profile is suspended and hidden from parents. Contact the administrator.",
};

// ------------------------------------------------------------------ overview
export function TutorOverview() {
  const p = useFetch<SelfProfile>("/tutor/profile/");
  const jobs = useFetch<Page<JobSummary>>(p.data?.status === "approved" ? "/tutor/jobs/?page_size=1" : null);
  const nav = useNavigate();
  const a = useAction();

  async function submit() {
    const r = await a.run(() => api.post<SelfProfile>("/tutor/profile/submit/"));
    if (r) p.reload();
  }

  return (
    <>
      <PageHeader title="Tutor overview" />
      <Async f={p}>
        {(t) => (
          <>
            <div className="card mb">
              <div className="row between"><h3 style={{ margin: 0 }}>Application status</h3><StatusBadge status={t.status} label={t.status_display} /></div>
              <p className="mt">{STATUS_HELP[t.status]}</p>
              {t.status_note && ["info_required", "rejected", "suspended"].includes(t.status) && <Alert kind="warning"><strong>Note from the administrator:</strong> {t.status_note}</Alert>}
              {t.has_unreviewed_changes && <Alert kind="info">Your recent changes are waiting for administrator review before they are shown as checked.</Alert>}
              {["draft", "pending_submission", "info_required", "rejected"].includes(t.status) && (
                <>
                  <div className="progress" aria-label={`Profile ${t.completeness}% complete`}><span style={{ width: `${t.completeness}%` }} /></div>
                  <p className="small muted">Profile {t.completeness}% complete</p>
                  {t.missing.length > 0 && <ul className="small">{t.missing.map((m) => <li key={m}>{m}</li>)}</ul>}
                  {a.error && <Alert kind="error">{a.error}</Alert>}
                  <div className="form-actions">
                    <button className="btn btn-outline" onClick={() => nav("/tutor/profile")}>Edit profile</button>
                    <button className="btn" disabled={a.busy || t.missing.length > 0} onClick={submit}>{t.status === "draft" || t.status === "pending_submission" ? "Submit for review" : "Resubmit for review"}</button>
                  </div>
                </>
              )}
            </div>
            <div className="grid cols-3">
              <Link to="/tutor/jobs" className="card card-link">
                <div className="stat">{t.status === "approved" ? jobs.data?.count ?? "–" : "🔒"}</div>
                <div className="muted">{t.status === "approved" ? "Open tutoring jobs" : "Jobs unlock after approval"}</div>
              </Link>
              <Link to="/tutor/applications" className="card card-link"><div className="stat">→</div><div className="muted">My job applications</div></Link>
              <Link to="/tutor/credentials" className="card card-link"><div className="stat">→</div><div className="muted">My credentials</div></Link>
            </div>
          </>
        )}
      </Async>
    </>
  );
}

// ------------------------------------------------------------------ profile + qualifications
export function TutorProfileEdit() {
  const p = useFetch<SelfProfile>("/tutor/profile/");
  return (
    <>
      <PageHeader title="My profile" subtitle="Information you provide is shown on your public profile once approved. Your phone number and email are never shown." />
      <Async f={p}>{(t) => <ProfileForm key={t.id} t={t} reload={p.reload} />}</Async>
    </>
  );
}

function ProfileForm({ t, reload }: { t: SelfProfile; reload: () => void }) {
  const ref = useReference();
  const locked = LOCKED.includes(t.status);
  const f = useForm({
    display_name: t.display_name, bio: t.bio, gender: t.gender, show_gender: t.show_gender,
    location: t.location ? String(t.location) : "", years_experience: String(t.years_experience ?? 0),
    teaching_methods: t.teaching_methods, teaching_mode: t.teaching_mode || "in_person",
    languages: t.languages.join(", "), rate_amount: t.rate_amount ?? "", rate_unit: t.rate_unit || "hour",
    subjects: t.subjects, grade_levels: t.grade_levels,
  });
  const a = useAction();
  const photo = useAction();
  const [saved, setSaved] = useState(false);

  const toggle = (k: "subjects" | "grade_levels", id: number) => {
    const cur = f.values[k] as number[];
    f.set(k, cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]);
  };

  async function save(e: FormEvent) {
    e.preventDefault();
    setSaved(false);
    const v = f.values;
    const r = await a.run(() => api.patch<SelfProfile>("/tutor/profile/", {
      display_name: v.display_name, bio: v.bio, gender: v.gender, show_gender: v.show_gender,
      location: idOrNull(v.location), years_experience: numOrNull(v.years_experience) ?? 0,
      teaching_methods: v.teaching_methods, teaching_mode: v.teaching_mode,
      languages: v.languages.split(",").map((s) => s.trim()).filter(Boolean),
      rate_amount: numOrNull(v.rate_amount), rate_unit: v.rate_unit, subjects: v.subjects, grade_levels: v.grade_levels,
    }));
    if (r) { setSaved(true); reload(); }
  }

  async function upload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("photo", file);
    const r = await photo.run(() => api.post("/tutor/profile/photo/", fd));
    e.target.value = "";
    if (r) reload();
  }

  return (
    <div className="stack">
      {locked && <Alert kind="warning">{t.status === "under_review" ? "Your application is under review, so editing is paused." : "Your profile is suspended, so editing is disabled."}</Alert>}
      <form className="card" onSubmit={save}>
        <fieldset disabled={locked} style={{ border: 0, padding: 0, margin: 0 }}>
          <h3>About you</h3>
          {a.error && <Alert kind="error">{a.error}</Alert>}
          {saved && <Alert kind="success">Profile saved.</Alert>}
          <div className="row mb" style={{ alignItems: "flex-start" }}>
            <Avatar name={t.display_name} photo={t.photo} large />
            <div>
              <Field label="Profile photo" hint="JPG or PNG, up to 2 MB." error={photo.error ?? undefined}><input type="file" accept="image/*" onChange={upload} /></Field>
            </div>
          </div>
          <Field label="Display name" required error={a.fields.display_name}><input className="input" required {...f.bind("display_name")} /></Field>
          <Field label="Professional biography" required error={a.fields.bio}><textarea className="input" rows={5} {...f.bind("bio")} /></Field>
          <div className="grid cols-2">
            <Field label="Gender" hint="You do not have to share this.">
              <select className="input" {...f.bind("gender")}><option value="">Prefer not to say</option><option value="female">Female</option><option value="male">Male</option><option value="other">Other</option></select>
            </Field>
            <label className="check" style={{ alignSelf: "center" }}>
              <input type="checkbox" checked={f.values.show_gender} onChange={(e) => f.set("show_gender", e.target.checked)} /> Show my gender on my public profile
            </label>
          </div>
          <Field label="General location" required hint="Area only. Never enter your home address." error={a.fields.location}>
            <select className="input" {...f.bind("location")}><option value="">Choose an area</option>{ref?.locations.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}</select>
          </Field>

          <h3 className="mt">Teaching</h3>
          <Field label="Subjects you teach" required error={a.fields.subjects}>
            <div className="checks">{ref?.subjects.map((s) => <label className="check" key={s.id}><input type="checkbox" checked={f.values.subjects.includes(s.id)} onChange={() => toggle("subjects", s.id)} />{s.name}</label>)}</div>
          </Field>
          <Field label="Grade levels" required error={a.fields.grade_levels}>
            <div className="checks">{ref?.grade_levels.map((g) => <label className="check" key={g.id}><input type="checkbox" checked={f.values.grade_levels.includes(g.id)} onChange={() => toggle("grade_levels", g.id)} />{g.name}</label>)}</div>
          </Field>
          <div className="grid cols-2">
            <Field label="Years of experience" required error={a.fields.years_experience}><input className="input" type="number" min={0} max={70} {...f.bind("years_experience")} /></Field>
            <Field label="Teaching mode" required>
              <select className="input" {...f.bind("teaching_mode")}>{ref?.teaching_modes.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}</select>
            </Field>
          </div>
          <Field label="Teaching methods"><textarea className="input" {...f.bind("teaching_methods")} /></Field>
          <Field label="Languages" hint="Separate with commas, e.g. Amharic, English"><input className="input" {...f.bind("languages")} /></Field>
          <div className="grid cols-2">
            <Field label="Fee (ETB)" error={a.fields.rate_amount}><input className="input" type="number" min={0} {...f.bind("rate_amount")} /></Field>
            <Field label="Fee period"><select className="input" {...f.bind("rate_unit")}><option value="hour">Per hour</option><option value="month">Per month</option></select></Field>
          </div>
          <button className="btn" disabled={a.busy}>{a.busy ? "Saving…" : "Save profile"}</button>
        </fieldset>
      </form>
      <Qualifications locked={locked} onChange={reload} />
      {!locked && t.missing.length > 0 && <Alert kind="info">Still needed before you can submit: {t.missing.join("; ")}.</Alert>}
      <Link className="btn btn-outline" to="/tutor">← Back to overview to submit</Link>
    </div>
  );
}

function Qualifications({ locked, onChange }: { locked: boolean; onChange: () => void }) {
  const f = useFetch<Qualification[]>("/tutor/qualifications/");
  const [editing, setEditing] = useState<Qualification | null>(null);
  const [del, setDel] = useState<Qualification | null>(null);
  const form = useForm({ level: "bachelor", title: "", institution: "", field_of_study: "", year: "" });
  const a = useAction();

  function edit(q: Qualification | null) {
    setEditing(q);
    form.setValues(q ? { level: q.level, title: q.title, institution: q.institution, field_of_study: q.field_of_study, year: q.year ? String(q.year) : "" }
      : { level: "bachelor", title: "", institution: "", field_of_study: "", year: "" });
  }
  async function save(e: FormEvent) {
    e.preventDefault();
    const body = { ...form.values, year: numOrNull(form.values.year) };
    const r = await a.run(() => editing ? api.patch(`/tutor/qualifications/${editing.id}/`, body) : api.post("/tutor/qualifications/", body));
    if (r) { edit(null); f.reload(); onChange(); }
  }
  async function remove() {
    if (!del) return;
    await a.run(() => api.del(`/tutor/qualifications/${del.id}/`));
    setDel(null); f.reload(); onChange();
  }

  return (
    <div className="card">
      <h3>Educational qualifications</h3>
      <p className="muted small">Add each qualification, then upload supporting documents under "My Credentials". Editing a qualification resets its "checked" status until it is reviewed again.</p>
      <Async f={f}>
        {(list) => list.length === 0 ? <p className="muted">No qualifications added yet.</p> : (
          <ul className="stack" style={{ listStyle: "none", padding: 0 }}>
            {list.map((q) => (
              <li key={q.id} className="row between">
                <span><strong>{q.title}</strong> ({LEVEL_LABEL[q.level]}) – {q.institution}{q.year && `, ${q.year}`} {q.verified ? <span className="badge badge-green">Checked</span> : <span className="badge badge-gray">Not yet checked</span>}</span>
                {!locked && <span className="row"><button className="btn btn-ghost btn-sm" onClick={() => edit(q)}>Edit</button><button className="btn btn-ghost btn-sm" onClick={() => setDel(q)}>Remove</button></span>}
              </li>
            ))}
          </ul>
        )}
      </Async>
      {!locked && (
        <form onSubmit={save} className="mt" style={{ borderTop: "1px solid var(--line)", paddingTop: "1rem" }}>
          <h4>{editing ? "Edit qualification" : "Add a qualification"}</h4>
          {a.error && <Alert kind="error">{a.error}</Alert>}
          <div className="grid cols-2">
            <Field label="Level" required><select className="input" {...form.bind("level")}>{Object.entries(LEVEL_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></Field>
            <Field label="Title / degree" required error={a.fields.title}><input className="input" required {...form.bind("title")} /></Field>
            <Field label="Institution" required error={a.fields.institution}><input className="input" required {...form.bind("institution")} /></Field>
            <Field label="Field of study" error={a.fields.field_of_study}><input className="input" {...form.bind("field_of_study")} /></Field>
            <Field label="Year completed" error={a.fields.year}><input className="input" type="number" min={1950} max={2100} {...form.bind("year")} /></Field>
          </div>
          <div className="form-actions"><button className="btn" disabled={a.busy}>{editing ? "Save changes" : "Add qualification"}</button>{editing && <button type="button" className="btn btn-outline" onClick={() => edit(null)}>Cancel</button>}</div>
        </form>
      )}
      <ConfirmDialog open={!!del} title="Remove this qualification?" confirmLabel="Remove" danger onConfirm={remove} onCancel={() => setDel(null)} />
    </div>
  );
}

// ------------------------------------------------------------------ credentials
export function Credentials() {
  const docs = useFetch<MyDocument[]>("/tutor/documents/");
  const quals = useFetch<Qualification[]>("/tutor/qualifications/");
  const prof = useFetch<SelfProfile>("/tutor/profile/");
  const f = useForm({ doc_type: "education_certificate", qualification: "" });
  const [file, setFile] = useState<File | null>(null);
  const [del, setDel] = useState<MyDocument | null>(null);
  const a = useAction();
  const locked = prof.data ? LOCKED.includes(prof.data.status) : false;

  async function upload(e: FormEvent) {
    e.preventDefault();
    if (!file) return a.setError("Choose a file first.");
    const fd = new FormData();
    fd.append("file", file);
    fd.append("doc_type", f.values.doc_type);
    if (f.values.qualification) fd.append("qualification", f.values.qualification);
    const r = await a.run(() => api.post("/tutor/documents/", fd));
    if (r) { setFile(null); (e.target as HTMLFormElement).reset(); docs.reload(); }
  }
  async function remove() {
    if (!del) return;
    await a.run(() => api.del(`/tutor/documents/${del.id}/`));
    setDel(null); docs.reload();
  }

  return (
    <>
      <PageHeader title="My credentials" subtitle="Documents are stored privately. Only you and authorised administrators can open them." />
      {locked && <Alert kind="warning">Uploads are paused while your application is under review or suspended.</Alert>}
      <div className="grid cols-2">
        <form className="card" onSubmit={upload}>
          <h3>Upload a document</h3>
          {a.error && <Alert kind="error">{a.error}</Alert>}
          {a.fields.file && <Alert kind="error">{a.fields.file}</Alert>}
          <fieldset disabled={locked} style={{ border: 0, padding: 0, margin: 0 }}>
            <Field label="Document type" required><select className="input" {...f.bind("doc_type")}>{DOC_TYPES.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}</select></Field>
            <Field label="Which qualification does it support?" hint="Linking a document lets the administrator mark that qualification as checked.">
              <select className="input" {...f.bind("qualification")}><option value="">Not linked</option>{quals.data?.map((q) => <option key={q.id} value={q.id}>{q.title}</option>)}</select>
            </Field>
            <Field label="File" required hint="PDF, JPG or PNG, up to 5 MB."><input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></Field>
            <button className="btn" disabled={a.busy}>{a.busy ? "Uploading…" : "Upload"}</button>
          </fieldset>
        </form>
        <div>
          <h3>Uploaded documents</h3>
          <Async f={docs}>
            {(list) => list.length === 0 ? <Empty title="No documents yet">Upload your certificates to speed up verification.</Empty> : (
              <div className="stack">
                {list.map((d) => (
                  <div className="card" key={d.id}>
                    <div className="row between"><strong>{d.original_name}</strong><StatusBadge status={d.status} /></div>
                    <div className="muted small">{humanize(d.doc_type)} · {fmtSize(d.size)} · {fmtDate(d.uploaded_at)}</div>
                    {d.reviewer_note && <Alert kind={d.status === "rejected" ? "error" : "info"}>{d.reviewer_note}</Alert>}
                    <div className="form-actions">
                      <button className="btn btn-outline btn-sm" onClick={() => api.download(`/documents/${d.id}/download/`, d.original_name).catch((e) => a.setError(String(e.message)))}>Download</button>
                      {!locked && d.status !== "verified" && <button className="btn btn-ghost btn-sm" onClick={() => setDel(d)}>Remove</button>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Async>
        </div>
      </div>
      <ConfirmDialog open={!!del} title="Remove this document?" confirmLabel="Remove" danger onConfirm={remove} onCancel={() => setDel(null)} />
    </>
  );
}

// ------------------------------------------------------------------ availability
export function Availability() {
  const ref = useReference();
  const f = useFetch<Slot[]>("/tutor/availability/");
  const form = useForm({ weekday: "0", start_time: "16:00", end_time: "18:00" });
  const a = useAction();
  async function add(e: FormEvent) {
    e.preventDefault();
    const r = await a.run(() => api.post("/tutor/availability/", { ...form.values, weekday: Number(form.values.weekday) }));
    if (r) f.reload();
  }
  async function remove(id: number) {
    await a.run(() => api.del(`/tutor/availability/${id}/`));
    f.reload();
  }
  return (
    <>
      <PageHeader title="My availability" subtitle="Your usual teaching days and times. Parents see this on your public profile." />
      <div className="grid cols-2">
        <form className="card" onSubmit={add}>
          <h3>Add a time slot</h3>
          {a.error && <Alert kind="error">{a.error}</Alert>}
          <Field label="Day" required><select className="input" {...form.bind("weekday")}>{ref?.weekdays.map((w) => <option key={w.value} value={w.value}>{w.label}</option>)}</select></Field>
          <div className="grid cols-2">
            <Field label="From" required error={a.fields.start_time}><input className="input" type="time" required {...form.bind("start_time")} /></Field>
            <Field label="Until" required error={a.fields.end_time}><input className="input" type="time" required {...form.bind("end_time")} /></Field>
          </div>
          <button className="btn" disabled={a.busy}>Add slot</button>
        </form>
        <div className="card">
          <h3>Current schedule</h3>
          <Async f={f}>
            {(list) => list.length === 0 ? <p className="muted">No time slots yet.</p> : (
              <ul className="stack" style={{ listStyle: "none", padding: 0 }}>
                {[...list].sort((x, y) => x.weekday - y.weekday || x.start_time.localeCompare(y.start_time)).map((s) => (
                  <li className="row between" key={s.id}>
                    <span><strong>{ref?.weekdays.find((w) => w.value === s.weekday)?.label}</strong> {fmtTime(s.start_time)}–{fmtTime(s.end_time)}</span>
                    <button className="btn btn-ghost btn-sm" onClick={() => remove(s.id)}>Remove</button>
                  </li>
                ))}
              </ul>
            )}
          </Async>
        </div>
      </div>
    </>
  );
}

// ------------------------------------------------------------------ job board
function LockedNotice() {
  return (
    <Empty title="The job board unlocks after approval" action={<Link className="btn" to="/tutor">See my application status</Link>}>
      Tutoring jobs are only visible to approved, active tutors. Complete your profile and submit it for review.
    </Empty>
  );
}

function JobCard({ j, to }: { j: JobSummary; to: string }) {
  return (
    <Link to={to} className="card card-link">
      <div className="row between"><h3 style={{ margin: 0 }}>{j.title}</h3>{j.my_application ? <StatusBadge status={j.my_application.status} /> : <StatusBadge status={j.status} label={j.status_display} />}</div>
      <div className="chips mt">
        {j.subject && <span className="chip">{j.subject.name}</span>}
        {j.grade_level && <span className="chip">{j.grade_level.name}</span>}
        <span className="chip">{MODE_LABEL[j.teaching_mode] ?? "Mode flexible"}</span>
        {j.location && <span className="chip">{j.location.label}</span>}
      </div>
      <p className="muted small mt" style={{ marginBottom: 0 }}>
        {[j.preferred_schedule, j.frequency, money(j.payment_amount) ?? j.payment_note].filter(Boolean).join(" · ") || "Details inside"}
        {j.application_deadline && ` · apply by ${fmtDate(j.application_deadline)}`}
      </p>
    </Link>
  );
}

export function JobBoard() {
  const { user } = useAuth();
  const ref = useReference();
  const [filters, setFilters] = useState({ q: "", subject: "", grade_level: "", location: "", teaching_mode: "", max_pay: "" });
  const approved = user?.tutor_status === "approved";
  const f = usePaged<JobSummary>("/tutor/jobs/", approved ? filters : { __skip: 1 });
  const set = (k: keyof typeof filters, v: string) => setFilters((p) => ({ ...p, [k]: v }));

  if (!approved) return <><PageHeader title="Find tutoring jobs" /><LockedNotice /></>;
  const active = Object.values(filters).some(Boolean);
  return (
    <>
      <PageHeader title="Find tutoring jobs" subtitle="Open opportunities from families we are helping. Parent details are never shown." />
      <div className="card mb">
        <div className="grid cols-4">
          <label className="field"><span className="label">Search</span><input className="input" value={filters.q} onChange={(e) => set("q", e.target.value)} /></label>
          <label className="field"><span className="label">Subject</span><select className="input" value={filters.subject} onChange={(e) => set("subject", e.target.value)}><option value="">Any</option>{ref?.subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
          <label className="field"><span className="label">Grade</span><select className="input" value={filters.grade_level} onChange={(e) => set("grade_level", e.target.value)}><option value="">Any</option>{ref?.grade_levels.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}</select></label>
          <label className="field"><span className="label">Location</span><select className="input" value={filters.location} onChange={(e) => set("location", e.target.value)}><option value="">Anywhere</option>{ref?.locations.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}</select></label>
          <label className="field"><span className="label">Mode</span><select className="input" value={filters.teaching_mode} onChange={(e) => set("teaching_mode", e.target.value)}><option value="">Any</option><option value="online">Online</option><option value="in_person">In person</option></select></label>
          <label className="field"><span className="label">Pay up to (ETB)</span><input className="input" type="number" min={0} value={filters.max_pay} onChange={(e) => set("max_pay", e.target.value)} /></label>
        </div>
        {active && <button className="btn btn-outline btn-sm" onClick={() => setFilters({ q: "", subject: "", grade_level: "", location: "", teaching_mode: "", max_pay: "" })}>Clear filters</button>}
      </div>
      <Async f={f}>
        {(d) => d.results.length === 0 ? (
          <Empty title={active ? "No jobs match your filters" : "No open jobs right now"}>{active ? "Try removing a filter." : "New opportunities are posted as families request tutors. Check back soon."}</Empty>
        ) : (
          <>
            <div className="grid cols-2">{d.results.map((j) => <JobCard key={j.id} j={j} to={`/tutor/jobs/${j.id}`} />)}</div>
            <Pagination page={f.page} count={d.count} onPage={f.setPage} />
          </>
        )}
      </Async>
    </>
  );
}

export function JobDetail() {
  const { id } = useParams();
  const f = useFetch<JobSummary>(`/tutor/jobs/${id}/`);
  const [message, setMessage] = useState("");
  const [withdraw, setWithdraw] = useState(false);
  const a = useAction();

  async function apply() {
    const r = await a.run(() => api.post(`/tutor/jobs/${id}/apply/`, { message }));
    if (r) f.reload();
  }
  async function doWithdraw(appId: number) {
    await a.run(() => api.post(`/tutor/applications/${appId}/withdraw/`));
    setWithdraw(false);
    f.reload();
  }

  return (
    <>
      <BackLink to="/tutor/jobs">All jobs</BackLink>
      <Async f={f}>
        {(j) => {
          const app = j.my_application;
          const canApply = j.accepting_applications && (!app || app.status === "withdrawn");
          return (
            <div className="grid" style={{ gridTemplateColumns: "minmax(0,2fr) minmax(260px,1fr)", alignItems: "start" }}>
              <div className="card">
                <div className="row between"><h1 style={{ fontSize: "1.6rem", margin: 0 }}>{j.title}</h1><StatusBadge status={j.status} label={j.status_display} /></div>
                <p className="muted small">{j.reference}</p>
                <dl className="kv">
                  <dt>Subject</dt><dd>{j.subject?.name ?? "-"}</dd>
                  <dt>Grade level</dt><dd>{j.grade_level?.name ?? "-"}</dd>
                  <dt>Location</dt><dd>{j.location?.label ?? "-"}</dd>
                  <dt>Teaching mode</dt><dd>{MODE_LABEL[j.teaching_mode] ?? "-"}</dd>
                  <dt>Schedule</dt><dd>{j.preferred_schedule || "-"}</dd>
                  <dt>Frequency</dt><dd>{j.frequency || "-"}</dd>
                  <dt>Duration</dt><dd>{j.duration || "-"}</dd>
                  <dt>Payment</dt><dd>{[money(j.payment_amount), j.payment_note].filter(Boolean).join(" · ") || "Negotiable"}</dd>
                  {j.application_deadline && <><dt>Apply by</dt><dd>{fmtDate(j.application_deadline)}</dd></>}
                </dl>
                {j.required_qualifications && <><h3 className="mt">Required qualifications</h3><p style={{ whiteSpace: "pre-line" }}>{j.required_qualifications}</p></>}
                {j.additional_requirements && <><h3>Additional requirements</h3><p style={{ whiteSpace: "pre-line" }}>{j.additional_requirements}</p></>}
              </div>
              <aside className="card">
                <h3>Your application</h3>
                {a.error && <Alert kind="error">{a.error}</Alert>}
                {app && app.status !== "withdrawn" && <p>Status: <StatusBadge status={app.status} /></p>}
                {app && app.status === "selected" && <Alert kind="success">You were selected. The administrator will contact you to arrange the introduction.</Alert>}
                {canApply ? (
                  <>
                    <p className="small muted">Your profile and verified qualifications are shared with the administrator automatically.</p>
                    <Field label="Short message" hint="Anything that makes you a good fit."><textarea className="input" maxLength={500} value={message} onChange={(e) => setMessage(e.target.value)} /></Field>
                    <button className="btn" style={{ width: "100%" }} disabled={a.busy} onClick={apply}>{a.busy ? "Sending…" : app ? "Express interest again" : "Express interest"}</button>
                  </>
                ) : !app ? <Alert kind="warning">This job is not accepting applications.</Alert> : null}
                {app && ["submitted", "under_review", "shortlisted"].includes(app.status) && (
                  <><button className="btn btn-outline btn-sm" onClick={() => setWithdraw(true)}>Withdraw application</button>
                  <ConfirmDialog open={withdraw} title="Withdraw your application?" confirmLabel="Withdraw" danger onConfirm={() => doWithdraw(app.id)} onCancel={() => setWithdraw(false)} /></>
                )}
                <p className="small muted mt">Applying does not mean you are selected. The administrator coordinates the final match.</p>
              </aside>
            </div>
          );
        }}
      </Async>
    </>
  );
}

// ------------------------------------------------------------------ applications / selected jobs
export function MyApplications({ selectedOnly = false }: { selectedOnly?: boolean }) {
  const [status, setStatus] = useState("");
  const f = usePaged<TutorApplication>("/tutor/applications/", { status: selectedOnly ? "selected" : status });
  return (
    <>
      <PageHeader title={selectedOnly ? "My selected jobs" : "My job applications"} subtitle={selectedOnly ? "Jobs where the administrator selected you." : undefined}
        actions={!selectedOnly && (
          <select className="input" style={{ width: "auto" }} value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
            <option value="">All statuses</option>
            {["submitted", "under_review", "shortlisted", "selected", "not_selected", "withdrawn"].map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
          </select>
        )} />
      <Async f={f}>
        {(d) => d.results.length === 0 ? (
          <Empty title={selectedOnly ? "No selected jobs yet" : "No applications yet"} action={<Link className="btn" to="/tutor/jobs">Browse jobs</Link>}>
            {selectedOnly ? "When the administrator selects you for a job it will appear here." : "Express interest in a job to see it here."}
          </Empty>
        ) : (
          <>
            <div className="stack">
              {d.results.map((a) => (
                <div key={a.id}>
                  <JobCard j={{ ...a.job, my_application: { id: a.id, status: a.status } }} to={`/tutor/jobs/${a.job.id}`} />
                  <p className="muted small" style={{ margin: "0.3rem 0 0 0.5rem" }}>Applied {fmtDate(a.created_at)} · last update {fmtDate(a.updated_at)}</p>
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
