import { Link } from "react-router-dom";
import { GENDER_LABEL, MODE_LABEL, initials, money } from "../labels";
import type { TutorCardData } from "../types";

export function Avatar({ name, photo, large }: { name: string; photo: string | null; large?: boolean }) {
  return photo ? (
    <img className={`avatar ${large ? "lg" : ""}`} src={photo} alt={`Photo of ${name}`} />
  ) : (
    <span className={`avatar ${large ? "lg" : ""}`} aria-hidden="true">{initials(name)}</span>
  );
}

/** Precise wording: "approved" is the profile; "checked" counts only qualifications an administrator verified. */
export function VerifyBadge({ checked }: { checked: number }) {
  return checked > 0 ? (
    <span className="badge badge-green verify" title="An administrator has reviewed supporting documents for these qualifications.">
      ✓ {checked} qualification{checked > 1 ? "s" : ""} checked
    </span>
  ) : (
    <span className="badge badge-blue verify" title="The profile was approved by an administrator. No qualification has been individually checked yet.">
      Profile approved
    </span>
  );
}

export default function TutorCard({ t, requestable = true }: { t: TutorCardData; requestable?: boolean }) {
  const rate = money(t.rate_amount, t.rate_unit);
  return (
    <article className="card tutor-card">
      <div className="row" style={{ flexWrap: "nowrap" }}>
        <Avatar name={t.display_name} photo={t.photo} />
        <div>
          <h3 style={{ margin: 0 }}><Link to={`/tutors/${t.id}`}>{t.display_name}</Link></h3>
          <div className="meta">
            {t.location?.label ?? "Location not set"}
            {t.gender && <> · {GENDER_LABEL[t.gender] ?? t.gender}</>}
          </div>
        </div>
      </div>
      <VerifyBadge checked={t.verified_qualifications} />
      <div className="chips" aria-label="Subjects">
        {t.subjects.map((s) => <span className="chip" key={s.id}>{s.name}</span>)}
      </div>
      <div className="meta">
        {t.grade_levels.length > 0 && <div>Grades: {t.grade_levels.map((g) => g.name).join(", ")}</div>}
        <div>
          {t.years_experience} yr{t.years_experience === 1 ? "" : "s"} experience · {MODE_LABEL[t.teaching_mode] ?? t.teaching_mode}
          {rate && <> · {rate}</>}
        </div>
      </div>
      <div className="actions">
        <Link className="btn btn-outline btn-sm" to={`/tutors/${t.id}`}>View profile</Link>
        {requestable && <Link className="btn btn-sm" to={`/request-tutor?tutor=${t.id}`}>Request introduction</Link>}
      </div>
    </article>
  );
}
