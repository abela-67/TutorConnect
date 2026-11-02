import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import { Async, Empty, PageHeader, Pagination } from "../../components/ui";
import { useAction, usePaged } from "../../hooks";
import { fmtDateTime } from "../../labels";
import type { Notification } from "../../types";

export default function Notifications() {
  const f = usePaged<Notification>("/notifications/");
  const nav = useNavigate();
  const a = useAction();

  async function open(n: Notification) {
    if (!n.is_read) await api.post(`/notifications/${n.id}/read/`).catch(() => undefined);
    if (n.link) nav(n.link);
    else f.reload();
  }
  async function readAll() {
    await a.run(() => api.post("/notifications/read-all/"));
    f.reload();
  }

  return (
    <>
      <PageHeader title="Notifications" actions={<button className="btn btn-outline btn-sm" onClick={readAll} disabled={a.busy}>Mark all as read</button>} />
      <Async f={f}>
        {(d) =>
          d.results.length === 0 ? (
            <Empty title="You're all caught up">New updates about your requests, applications and account will appear here.</Empty>
          ) : (
            <>
              <div className="stack">
                {d.results.map((n) => (
                  <button key={n.id} onClick={() => open(n)} className="card card-link" style={{ width: "100%", textAlign: "left", font: "inherit", cursor: "pointer", borderLeft: n.is_read ? undefined : "4px solid var(--accent)" }}>
                    <div className="row between">
                      <strong>{n.title}</strong>
                      <span className="muted small">{fmtDateTime(n.created_at)}</span>
                    </div>
                    {n.body && <div className="muted">{n.body}</div>}
                  </button>
                ))}
              </div>
              <Pagination page={f.page} count={d.count} onPage={f.setPage} />
            </>
          )
        }
      </Async>
    </>
  );
}
