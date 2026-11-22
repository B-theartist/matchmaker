import { useEffect, useState } from "react";
import { api, type Consultant, type SkillWithCount } from "../api";
import RequestForm from "./RequestForm";

// "Find Peers": pick a skill, see who on other engagements lists it, ask them for help.
export default function FindPeers({ onSent }: { onSent: () => void }) {
  const [skills, setSkills] = useState<SkillWithCount[]>([]);
  const [skillId, setSkillId] = useState<number | undefined>(undefined);
  const [peers, setPeers] = useState<Consultant[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [askingId, setAskingId] = useState<number | null>(null);

  useEffect(() => { api.skills().then(setSkills).catch((e: Error) => setError(e.message)); }, []);

  // Re-run the search whenever the chosen skill changes.
  useEffect(() => {
    setPeers(null);
    setAskingId(null);
    api.consultants(skillId).then(setPeers).catch((e: Error) => setError(e.message));
  }, [skillId]);

  return (
    <section>
      <div className="card row">
        <label className="inline">
          Who can help with
          <select
            value={skillId ?? ""}
            onChange={(e) => setSkillId(e.target.value ? Number(e.target.value) : undefined)}
          >
            <option value="">any skill</option>
            {skills.map((s) => (
              <option key={s.id} value={s.id}>{s.name} ({s.consultant_count})</option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="error">{error}</p>}
      {peers === null && !error && <p className="muted">Searching…</p>}
      {peers?.length === 0 && <p className="muted">No one else lists that skill yet.</p>}

      {peers?.map((p) => (
        <article key={p.id} className="card">
          <div className="row spread">
            <h3>{p.display_name}</h3>
            {askingId !== p.id && (
              <button className="primary" onClick={() => setAskingId(p.id)}>Request help</button>
            )}
          </div>
          <p>{p.project_context || <span className="muted">No project context yet</span>}</p>
          <div className="chips">
            {p.skills.map((s) => (
              <span key={s.id} className={s.id === skillId ? "chip match" : "chip"}>{s.name}</span>
            ))}
          </div>
          {askingId === p.id && (
            <RequestForm
              recipient={p}
              defaultSkillId={skillId}
              onCancel={() => setAskingId(null)}
              onSent={onSent}
            />
          )}
        </article>
      ))}
    </section>
  );
}
