import { Link, useParams } from "react-router-dom";
import { Avatar, VerifyBadge } from "../components/TutorCard";
import { Alert, Async } from "../components/ui";
import { useFetch, useReference } from "../hooks";
import { GENDER_LABEL, LEVEL_LABEL, MODE_LABEL, fmtDate, fmtTime, money } from "../labels";
import type { TutorDetail } from "../types";

export default function TutorProfilePage() {
  const { id } = useParams();
  const ref = useReference();
  const f = useFetch<TutorDetail>(`/tutors/${id}/`);
  const day = (n: number) => ref?.weekdays.find((w) => w.value === n)?.label ?? String(n);

  return (
    <div className="container section">
      <p><Link to="/tutors">← Back to tutors</Link></p>
      <Async f={f}>
        {(t) => {
          const rate = money(t.rate_amount, t.rate_unit);
          return (
            <div className="grid" style={{ gridTemplateColumns: "minmax(0,2fr) minmax(260px,1fr)", alignItems: "start" }}>
              <div className="stack">
                <div className="card">
                  <div className="row" style={{ flexWrap: "nowrap", alignItems: "flex-start" }}>
                    <Avatar name={t.display_name} photo={t.photo} large />
                    <div>
                      <h1 style={{ marginBottom: "0.3rem" }}>{t.display_name}</h1>
                      <p className="muted" style={{ margin: 0 }}>
                        {t.location?.label ?? "Location not set"}{t.gender && <> · {GENDER_LABEL[t.gender] ?? t.gender}</>}
                      </p>
                      <div className="mt"><VerifyBadge checked={t.verified_qualifications} /></div>
                    </div>
                  </div>
                  {t.bio && <><h3 className="mt">About</h3><p style={{ whiteSpace: "pre-line" }}>{t.bio}</p></>}
                  {t.teaching_methods && <><h3>Teaching methods</h3><p style={{ whiteSpace: "pre-line" }}>{t.teaching_methods}</p></>}
                </div>

                <div className="card">
                  <h3>Teaching</h3>
                  <dl className="kv">
                    <dt>Subjects</dt><dd><div className="chips">{t.subjects.map((s) => <span className="chip" key={s.id}>{s.name}</span>)}</div></dd>
                    <dt>Grade levels</dt><dd>{t.grade_levels.map((g) => g.name).join(", ") || "-"}</dd>
                    <dt>Experience</dt><dd>{t.years_experience} year{t.years_experience === 1 ? "" : "s"}</dd>
                    <dt>Mode</dt><dd>{MODE_LABEL[t.teaching_mode] ?? t.teaching_mode}</dd>
                    <dt>Languages</dt><dd>{t.languages.join(", ") || "-"}</dd>
                    <dt>Fee</dt><dd>{rate ?? "Ask the administrator"}</dd>
                  </dl>
                </div>

                <div className="card">
                  <h3>Qualifications</h3>
                  {t.qualifications.length === 0 ? <p className="muted">No qualifications listed.</p> : (
                    <ul style={{ paddingLeft: "1.1rem" }}>
                      {t.qualifications.map((q) => (
                        <li key={q.id} style={{ marginBottom: "0.5rem" }}>
                          <strong>{q.title}</strong> <span className="muted">({LEVEL_LABEL[q.level] ?? q.level})</span><br />
                          {q.institution}{q.field_of_study && `, ${q.field_of_study}`}{q.year && ` · ${q.year}`}{" "}
                          {q.verified ? <span className="badge badge-green">Checked by TutorConnect</span> : <span className="badge badge-gray">Provided by tutor</span>}
                        </li>
                      ))}
                    </ul>
                  )}
                  <p className="muted small">
                    {t.verification.verified_qualifications} of {t.verification.total_qualifications} qualification(s) have been checked against documents by an administrator
                    {t.verification.reviewed_at && <> (profile approved {fmtDate(t.verification.reviewed_at)})</>}. All other information is supplied by the tutor. This is not a background check.
                  </p>
                  {t.verification.has_changes_awaiting_review && <Alert kind="warning">This tutor recently updated their profile. The changes are awaiting administrator review.</Alert>}
                </div>

                {t.availability.length > 0 && (
                  <div className="card">
                    <h3>Usual availability</h3>
                    <ul style={{ paddingLeft: "1.1rem" }}>
                      {t.availability.map((s) => <li key={s.id}>{day(s.weekday)}: {fmtTime(s.start_time)}–{fmtTime(s.end_time)}</li>)}
                    </ul>
                  </div>
                )}
              </div>

              <aside className="card" style={{ position: "sticky", top: 80 }}>
                <h3>Interested?</h3>
                <p className="small muted">TutorConnect coordinates every introduction. You cannot message tutors directly, and contact details are only shared once you and the tutor both agree.</p>
                <div className="stack">
                  <Link className="btn" style={{ width: "100%" }} to={`/request-tutor?tutor=${t.id}`}>Request This Tutor</Link>
                  <Link className="btn btn-outline" style={{ width: "100%" }} to={`/parent/contact?tutor=${t.id}`}>Ask the Administrator</Link>
                </div>
              </aside>
            </div>
          );
        }}
      </Async>
    </div>
  );
}
