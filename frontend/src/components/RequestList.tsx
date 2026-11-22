import { useEffect, useState } from "react";
import { api, KIND_LABEL, type HelpRequest } from "../api";

// Inbox = requests sent TO me (recipient_id = me). Sent = requests FROM me (sender_id = me).
export default function RequestList({ box }: { box: "inbox" | "sent" }) {
  const [items, setItems] = useState<HelpRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setItems(null);
    (box === "inbox" ? api.inbox() : api.sent())
      .then(setItems)
      .catch((e: Error) => setError(e.message));
  }, [box]);

  if (error) return <p className="error">{error}</p>;
  if (items === null) return <p className="muted">Loading…</p>;
  if (items.length === 0) {
    return <p className="muted">{box === "inbox" ? "No requests yet." : "You haven't sent any requests."}</p>;
  }

  return (
    <section>
      {items.map((r) => (
        <article key={r.id} className="card">
          <div className="row spread">
            <strong>
              {box === "inbox" ? `From ${r.sender.display_name}` : `To ${r.recipient.display_name}`}
            </strong>
            <span className="muted">{new Date(r.created_at).toLocaleString()}</span>
          </div>
          <div className="chips">
            <span className="chip kind">{KIND_LABEL[r.kind]}</span>
            <span className="chip match">{r.skill.name}</span>
          </div>
          <p className="message">{r.message}</p>
        </article>
      ))}
    </section>
  );
}
