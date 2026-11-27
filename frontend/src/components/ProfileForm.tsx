import { useEffect, useState, type FormEvent } from "react";
import { api, type Consultant, type SkillWithCount } from "../api";

interface Props {
  profile: Consultant | null;
  onSaved: (profile: Consultant) => void;
}

// "My Profile": who I am, what I'm working on now, and what I can help with.
export default function ProfileForm({ profile, onSaved }: Props) {
  const [displayName, setDisplayName] = useState(profile?.display_name ?? "");
  const [projectContext, setProjectContext] = useState(profile?.project_context ?? "");
  const [skills, setSkills] = useState<string[]>(profile?.skills.map((s) => s.name) ?? []);
  const [draftSkill, setDraftSkill] = useState("");
  const [knownSkills, setKnownSkills] = useState<SkillWithCount[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Existing skills power the autocomplete, so people pick "SQL tuning" instead of retyping it.
  useEffect(() => { api.skills().then(setKnownSkills).catch(() => {}); }, []);

  function addSkill() {
    const name = draftSkill.trim();
    if (name && !skills.some((s) => s.toLowerCase() === name.toLowerCase())) {
      setSkills([...skills, name]);
    }
    setDraftSkill("");
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setStatus(null);
    try {
      const saved = await api.saveMe({
        display_name: displayName,
        project_context: projectContext,
        skills: draftSkill.trim() ? [...skills, draftSkill.trim()] : skills,
      });
      setSkills(saved.skills.map((s) => s.name));
      setDraftSkill("");
      onSaved(saved);
      setStatus("Saved ✓");
    } catch (err) {
      setStatus((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="card form" onSubmit={save}>
      {!profile && <p className="callout">Welcome! Create your profile so colleagues can find you.</p>}

      <label>
        Your name
        <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} required maxLength={100} />
      </label>

      <label>
        What are you working on right now?
        <textarea
          rows={3}
          value={projectContext}
          onChange={(e) => setProjectContext(e.target.value)}
          placeholder="e.g. Retail client: migrating nightly sales ETL to Delta Live Tables"
          maxLength={2000}
        />
      </label>

      <label>
        Skills you can help with
        <div className="chips">
          {skills.map((s) => (
            <span key={s} className="chip skill">
              {s}
              <button type="button" aria-label={`Remove ${s}`} onClick={() => setSkills(skills.filter((x) => x !== s))}>×</button>
            </span>
          ))}
        </div>
        <div className="row">
          <input
            list="known-skills"
            value={draftSkill}
            onChange={(e) => setDraftSkill(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addSkill(); } }}
            placeholder="Type a skill and press Enter"
          />
          <button type="button" onClick={addSkill}>Add</button>
        </div>
        <datalist id="known-skills">
          {knownSkills.map((s) => <option key={s.id} value={s.name} />)}
        </datalist>
      </label>

      <div className="row">
        <button className="primary" disabled={saving}>{saving ? "Saving…" : "Save profile"}</button>
        {status && <span className={status.startsWith("Saved") ? "ok" : "error"}>{status}</span>}
      </div>
    </form>
  );
}
