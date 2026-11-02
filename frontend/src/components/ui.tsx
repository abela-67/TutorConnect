import { ReactNode, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { FetchState } from "../hooks";
import { statusLabel, toneFor } from "../labels";

export function Alert({ kind = "info", children }: { kind?: "info" | "success" | "error" | "warning"; children: ReactNode }) {
  return (
    <div className={`alert alert-${kind}`} role={kind === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="loading" role="status">
      <span className="spinner" aria-hidden="true" /> {label}
    </div>
  );
}

export function Empty({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  return <span className={`badge badge-${toneFor(status)}`}>{label ?? statusLabel(status)}</span>;
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted" style={{ margin: "0.25rem 0 0" }}>{subtitle}</p>}
      </div>
      {actions && <div className="row">{actions}</div>}
    </div>
  );
}

/** Renders loading / error states for a useFetch result, then the content. */
export function Async<T>({ f, children }: { f: FetchState<T>; children: (data: T) => ReactNode }) {
  if (f.loading && !f.data) return <Spinner />;
  if (f.error) return <Alert kind="error">{f.error}</Alert>;
  if (!f.data) return null;
  return <>{children(f.data)}</>;
}

export function Field({
  label, required, hint, error, children,
}: { label: string; required?: boolean; hint?: string; error?: string; children: ReactNode }) {
  return (
    <label className="field">
      <span className="label">
        {label} {required ? <span className="req" aria-label="required">*</span> : <span className="opt">(optional)</span>}
      </span>
      {children}
      {hint && <span className="hint" style={{ display: "block" }}>{hint}</span>}
      {error && <span className="err" role="alert" style={{ display: "block" }}>{error}</span>}
    </label>
  );
}

export function Pagination({ page, count, pageSize = 12, onPage }: { page: number; count: number; pageSize?: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (pages <= 1) return null;
  return (
    <nav className="pagination" aria-label="Pagination">
      <button className="btn btn-outline btn-sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button>
      <span className="muted small">Page {page} of {pages}</span>
      <button className="btn btn-outline btn-sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</button>
    </nav>
  );
}

export function Modal({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="modal-back" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title}>
        <h3>{title}</h3>
        {children}
      </div>
    </div>
  );
}

/** Confirmation dialog with an optional (or required) explanation, e.g. for rejections and closures. */
export function ConfirmDialog({
  open, title, message, confirmLabel = "Confirm", danger, noteLabel, noteRequired, busy, onConfirm, onCancel,
}: {
  open: boolean; title: string; message?: ReactNode; confirmLabel?: string; danger?: boolean; noteLabel?: string;
  noteRequired?: boolean; busy?: boolean; onConfirm: (note: string) => void; onCancel: () => void;
}) {
  const [note, setNote] = useState("");
  useEffect(() => {
    if (open) setNote("");
  }, [open]);
  const blocked = Boolean(noteLabel && noteRequired && !note.trim());
  return (
    <Modal open={open} title={title} onClose={onCancel}>
      {message && <div className="mb">{message}</div>}
      {noteLabel && (
        <Field label={noteLabel} required={noteRequired}>
          <textarea className="input" value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} />
        </Field>
      )}
      <div className="form-actions">
        <button className={`btn ${danger ? "btn-danger" : ""}`} disabled={blocked || busy} onClick={() => onConfirm(note.trim())}>
          {busy ? "Working…" : confirmLabel}
        </button>
        <button className="btn btn-outline" onClick={onCancel}>Cancel</button>
      </div>
    </Modal>
  );
}

export function Tabs({ tabs, value, onChange }: { tabs: { value: string; label: string }[]; value: string; onChange: (v: string) => void }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button key={t.value} role="tab" aria-selected={value === t.value} className={value === t.value ? "active" : ""} onClick={() => onChange(t.value)}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function BarList({ data }: { data: Record<string, number> | { label: string; value: number }[] }) {
  const rows = Array.isArray(data) ? data : Object.entries(data).map(([label, value]) => ({ label, value }));
  const max = Math.max(1, ...rows.map((r) => r.value));
  if (!rows.length) return <p className="muted small">No data in this period.</p>;
  return (
    <div>
      {rows.map((r) => (
        <div className="bar-row" key={r.label}>
          <span>{statusLabel(r.label)}</span>
          <span className="bar"><span style={{ width: `${(100 * r.value) / max}%` }} /></span>
          <strong>{r.value}</strong>
        </div>
      ))}
    </div>
  );
}

export function Timeline({ items }: { items: { id: number; from_status: string; to_status: string; changed_by_name: string; note: string; created_at: string }[] }) {
  if (!items?.length) return <p className="muted small">No history yet.</p>;
  return (
    <ul className="timeline">
      {items.map((h) => (
        <li key={h.id}>
          <strong>{h.from_status ? `${statusLabel(h.from_status)} → ` : ""}{statusLabel(h.to_status)}</strong>
          <span className="muted"> · {h.changed_by_name} · {new Date(h.created_at).toLocaleString()}</span>
          {h.note && <div className="small">{h.note}</div>}
        </li>
      ))}
    </ul>
  );
}

export function BackLink({ to, children }: { to: string; children: ReactNode }) {
  return <p><Link to={to}>← {children}</Link></p>;
}
