import { FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { qs } from "../api";
import TutorCard from "../components/TutorCard";
import { Empty, Pagination, Spinner, Alert } from "../components/ui";
import { useFetch, useReference } from "../hooks";
import type { Page, TutorCardData } from "../types";

const FILTER_KEYS = ["q", "subject", "grade_level", "location", "gender", "teaching_mode", "available_day", "min_experience", "max_rate", "rate_unit"];

export default function Directory() {
  const ref = useReference();
  const [sp, setSp] = useSearchParams();
  const get = (k: string) => sp.get(k) || "";
  const [q, setQ] = useState(get("q"));
  useEffect(() => setQ(sp.get("q") || ""), [sp]);

  const set = (k: string, v: string) => {
    const n = new URLSearchParams(sp);
    if (v) n.set(k, v);
    else n.delete(k);
    n.delete("page");
    setSp(n, { replace: true });
  };
  const page = Number(sp.get("page") || 1);
  const params: Record<string, string> = {};
  FILTER_KEYS.forEach((k) => (params[k] = get(k)));
  const f = useFetch<Page<TutorCardData>>(`/tutors/${qs({ ...params, ordering: get("ordering"), page })}`);
  const active = FILTER_KEYS.some((k) => get(k));

  const submitQ = (e: FormEvent) => {
    e.preventDefault();
    set("q", q.trim());
  };

  return (
    <div className="container section">
      <h1>Find a tutor</h1>
      <p className="muted">Only approved, active tutors are listed. Combine any filters; leave a filter on "No preference" to ignore it.</p>
      <div className="layout-filters">
        <aside className="card filters" aria-label="Filters">
          <form onSubmit={submitQ}>
            <label className="field">
              <span className="label">Search</span>
              <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name or keyword" />
            </label>
            <button className="btn btn-sm" type="submit" style={{ marginBottom: "1rem" }}>Search</button>
          </form>
          <Select label="Subject" value={get("subject")} onChange={(v) => set("subject", v)} empty="Any subject"
            options={ref?.subjects.map((s) => ({ value: s.id, label: s.name })) ?? []} />
          <Select label="Location" value={get("location")} onChange={(v) => set("location", v)} empty="Anywhere"
            options={ref?.locations.map((l) => ({ value: l.id, label: l.label })) ?? []} />
          <Select label="Grade level" value={get("grade_level")} onChange={(v) => set("grade_level", v)} empty="Any grade"
            options={ref?.grade_levels.map((g) => ({ value: g.id, label: g.name })) ?? []} />
          <Select label="Gender" value={get("gender")} onChange={(v) => set("gender", v)} empty="No preference"
            options={ref?.genders.filter((g) => g.value !== "other").map((g) => ({ value: g.value, label: g.label })) ?? []} />
          <Select label="Teaching mode" value={get("teaching_mode")} onChange={(v) => set("teaching_mode", v)} empty="Online or in person"
            options={[{ value: "online", label: "Online" }, { value: "in_person", label: "In person" }]} />
          <Select label="Available on" value={get("available_day")} onChange={(v) => set("available_day", v)} empty="Any day"
            options={ref?.weekdays ?? []} />
          <Select label="Experience" value={get("min_experience")} onChange={(v) => set("min_experience", v)} empty="Any"
            options={[1, 3, 5, 10].map((n) => ({ value: n, label: `${n}+ years` }))} />
          <label className="field">
            <span className="label">Maximum fee (ETB)</span>
            <input className="input" type="number" min={0} inputMode="numeric" value={get("max_rate")} onChange={(e) => set("max_rate", e.target.value)} />
          </label>
          {get("max_rate") && (
            <Select label="Fee period" value={get("rate_unit")} onChange={(v) => set("rate_unit", v)} empty="Either"
              options={[{ value: "hour", label: "Per hour" }, { value: "month", label: "Per month" }]} />
          )}
          {active && <button className="btn btn-outline btn-sm" onClick={() => setSp({}, { replace: true })}>Clear all filters</button>}
        </aside>

        <section aria-live="polite">
          {f.loading && !f.data ? <Spinner label="Searching…" /> : f.error ? (
            <Alert kind="error">{f.error.includes("fields") ? "One of the filters has an invalid value. Clear the filters and try again." : f.error}</Alert>
          ) : f.data && f.data.results.length > 0 ? (
            <>
              <div className="row between mb">
                <strong>{f.data.count} tutor{f.data.count === 1 ? "" : "s"} found</strong>
                <label className="row small">
                  Sort by
                  <select className="input" style={{ width: "auto", minHeight: 34 }} value={get("ordering")} onChange={(e) => set("ordering", e.target.value)}>
                    <option value="">Most experienced</option>
                    <option value="rate_amount">Lowest fee</option>
                    <option value="-rate_amount">Highest fee</option>
                    <option value="-created_at">Newest</option>
                  </select>
                </label>
              </div>
              <div className="grid cols-2">{f.data.results.map((t) => <TutorCard key={t.id} t={t} />)}</div>
              <Pagination page={page} count={f.data.count} onPage={(p) => { const n = new URLSearchParams(sp); n.set("page", String(p)); setSp(n); window.scrollTo({ top: 0 }); }} />
            </>
          ) : (
            <Empty
              title="No tutors match these filters"
              action={
                <div className="form-actions" style={{ justifyContent: "center" }}>
                  {active && <button className="btn" onClick={() => setSp({}, { replace: true })}>Remove all filters</button>}
                  <Link className="btn btn-outline" to="/request-tutor">Ask the administrator to find a tutor</Link>
                </div>
              }
            >
              Try removing a filter, or tell us what you need and we will search for you.
            </Empty>
          )}
        </section>
      </div>
    </div>
  );
}

function Select({ label, value, onChange, options, empty }: {
  label: string; value: string; onChange: (v: string) => void; empty: string; options: { value: string | number; label: string }[];
}) {
  return (
    <label className="field">
      <span className="label">{label}</span>
      <select className="input" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{empty}</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
