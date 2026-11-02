import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { qs } from "../api";
import TutorCard from "../components/TutorCard";
import { Spinner } from "../components/ui";
import { useFetch, useReference } from "../hooks";
import type { TutorCardData } from "../types";

const CONTACT_PHONE = import.meta.env.VITE_CONTACT_PHONE as string | undefined;

export default function Home() {
  const ref = useReference();
  const nav = useNavigate();
  const [subject, setSubject] = useState("");
  const [location, setLocation] = useState("");
  const featured = useFetch<TutorCardData[]>("/tutors/featured/");

  function search(e: FormEvent) {
    e.preventDefault();
    nav(`/tutors${qs({ subject, location })}`);
  }

  return (
    <>
      <section className="hero">
        <div className="container">
          <h1>Find the Right Tutor for Your Learning Needs.</h1>
          <p className="lead">
            Discover qualified tutors, explore their experience, and get help finding the right match. Our team helps
            coordinate introductions between parents and tutors.
          </p>
          <form className="search-box" onSubmit={search} aria-label="Search tutors">
            <label className="field">
              <span className="label">Subject</span>
              <select className="input" value={subject} onChange={(e) => setSubject(e.target.value)}>
                <option value="">Any subject</option>
                {ref?.subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </label>
            <label className="field">
              <span className="label">Area</span>
              <select className="input" value={location} onChange={(e) => setLocation(e.target.value)}>
                <option value="">Anywhere</option>
                {ref?.locations.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
              </select>
            </label>
            <button className="btn btn-accent" type="submit">Search tutors</button>
          </form>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <h2>How TutorConnect works</h2>
          <div className="grid cols-3">
            <div className="card"><div className="step-num">1</div><h3>Browse or tell us what you need</h3><p>Search approved tutors by subject, grade, area and more, or send a short request and let us suggest candidates.</p></div>
            <div className="card"><div className="step-num">2</div><h3>We coordinate the introduction</h3><p>Our administrator checks availability and fit with the tutor and with you. There is no unsupervised messaging on the platform.</p></div>
            <div className="card"><div className="step-num">3</div><h3>Contact details are shared with consent</h3><p>Only after you and the tutor have both agreed do we share contact details to start lessons.</p></div>
          </div>
        </div>
      </section>

      <section className="section alt">
        <div className="container">
          <div className="row between">
            <h2 style={{ margin: 0 }}>Featured tutors</h2>
            <Link to="/tutors">See all tutors →</Link>
          </div>
          <div className="mt">
            {featured.loading ? <Spinner /> : featured.data && featured.data.length > 0 ? (
              <div className="grid cols-3">{featured.data.map((t) => <TutorCard key={t.id} t={t} />)}</div>
            ) : (
              <p className="muted">Approved tutors will appear here as soon as they are verified.</p>
            )}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container grid cols-2">
          <div>
            <h2>What "verified" means here</h2>
            <p>Every tutor applies with a profile and supporting documents. An administrator reviews the application before the profile is shown publicly.</p>
            <ul>
              <li><strong>Profile approved</strong> – the application was reviewed and accepted.</li>
              <li><strong>Qualifications checked</strong> – we reviewed documents for that specific qualification.</li>
              <li>Everything else on a profile (such as the biography and teaching style) is supplied by the tutor.</li>
            </ul>
            <p className="muted small">We do not state that a tutor has passed a background check unless one has been completed and recorded.</p>
          </div>
          <div className="card">
            <h2>Not sure who to choose?</h2>
            <p>Send us a short request: subject, grade and where lessons should happen. We search the approved tutors, speak to candidates, and come back with a suggestion. Prefer to talk? Parents can also ask us to take the request by telephone.</p>
            <div className="form-actions">
              <Link className="btn" to="/request-tutor">Ask us to find a tutor</Link>
              <Link className="btn btn-outline" to="/tutors">Browse tutors myself</Link>
            </div>
          </div>
        </div>
      </section>

      <section className="section alt">
        <div className="container grid cols-2">
          <div className="card">
            <h3>Are you a tutor?</h3>
            <p>Create a profile, upload your qualifications and, once approved, see tutoring opportunities from families we are helping.</p>
            <Link className="btn btn-accent" to="/register/tutor">Apply to become a tutor</Link>
          </div>
          <div className="card">
            <h3>Contact the administrator</h3>
            <p>Questions about scheduling, a tutor, or how verification works? Send us a private message{CONTACT_PHONE ? <> or call <strong>{CONTACT_PHONE}</strong></> : ""}.</p>
            <Link className="btn btn-outline" to="/parent/contact">Send a message</Link>
          </div>
        </div>
      </section>
    </>
  );
}
