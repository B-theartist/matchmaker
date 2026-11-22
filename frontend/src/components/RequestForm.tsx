import { useState, type FormEvent } from "react";
import { api, KIND_LABEL, type Consultant, type RequestKind } from "../api";

interface Props {
  recipient: Consultant;
  defaultSkillId?: number;
  onCancel: () => void;
  onSent: () => void;
}

// Sends one help request. The browser chooses WHO (recipient), WHICH skill, WHAT kind and
// the message. It never sends the sender - the backend takes that from the sign-in.
export default function RequestForm({ recipient, defaultSkillId, onCancel, onSent }: Props) {
  // Pre-select the skill Jordan searched for; he can switch to any other skill Maya offers.
  const initialSkill =
    recipient.skills.find((s) => s.id === defaultSkillId)?.id ?? recipient.skills[0]?.id;
  const [skillId, setSkillId] = useState<number | undefined>(initialSkill);
  const [kind, setKind] = useState<RequestKind>("technical_review");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function send(e: FormEvent) {
    e.preventDefault();
    if (skillId === undefined) return;
    setSending(true);
    setError(null);
    try {
      await api.sendRequest({ recipient_id: recipient.id, skill_id: skillId, kind, message });
      onSent();
    } catch (err) {
      setError((err as Error).message);
      setSending(false);
    }
  }

  if (recipient.skills.length === 0) {
    return <p className="muted">{recipient.display_name} hasn't listed any skills yet.</p>;
  }

  return (
    <form className="form nested" onSubmit={send}>
      <div className="row">
        <label className="inline">
          Topic
          <select value={skillId} onChange={(e) => setSkillId(Number(e.target.value))}>
            {recipient.skills.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </label>
        {(Object.keys(KIND_LABEL) as RequestKind[]).map((k) => (
          <label key={k} className="inline radio">
            <input type="radio" name="kind" checked={kind === k} onChange={() => setKind(k)} />
            {KIND_LABEL[k]}
          </label>
        ))}
      </div>
      <label>
        Message to {recipient.display_name}
        <textarea
          rows={3}
          required
          maxLength={4000}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="What do you need, and by when? They'll reply when they can."
        />
      </label>
      <div className="row">
        <button className="primary" disabled={sending}>{sending ? "Sending…" : "Send request"}</button>
        <button type="button" onClick={onCancel}>Cancel</button>
        {error && <span className="error">{error}</span>}
      </div>
    </form>
  );
}
