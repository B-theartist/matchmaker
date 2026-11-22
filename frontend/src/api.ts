// Typed wrapper around fetch(). Every screen talks to the backend through here.
// These types mirror server/models.py - they are the same contract on both sides.

export type RequestKind = "knowledge_sharing" | "technical_review";

export interface Skill { id: number; name: string }
export interface SkillWithCount extends Skill { consultant_count: number }
export interface Consultant {
  id: number;
  display_name: string;
  project_context: string;
  skills: Skill[];
}
export interface Me { email: string; profile: Consultant | null }
export interface PersonRef { id: number; display_name: string }
export interface HelpRequest {
  id: number;
  kind: RequestKind;
  message: string;
  created_at: string;
  skill: Skill;
  sender: PersonRef;
  recipient: PersonRef;
}

export const KIND_LABEL: Record<RequestKind, string> = {
  knowledge_sharing: "Knowledge sharing",
  technical_review: "Technical review",
};

// Local development only: lets you switch between pretend users (Maya / Jordan).
// When deployed, Databricks signs the user in and this header is ignored.
export const DEV_USER_KEY = "matchmaker.devUser";
function devHeaders(): Record<string, string> {
  if (!import.meta.env.DEV) return {};
  const user = localStorage.getItem(DEV_USER_KEY);
  return user ? { "X-Dev-User": user } : {};
}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...devHeaders() },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const detail = Array.isArray(data.detail)
      ? data.detail.map((d: { msg: string }) => d.msg).join("; ")
      : data.detail;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  me: () => call<Me>("GET", "/me"),
  saveMe: (p: { display_name: string; project_context: string; skills: string[] }) =>
    call<Consultant>("PUT", "/me", p),
  skills: () => call<SkillWithCount[]>("GET", "/skills"),
  consultants: (skillId?: number) =>
    call<Consultant[]>("GET", skillId ? `/consultants?skill_id=${skillId}` : "/consultants"),
  sendRequest: (r: { recipient_id: number; skill_id: number; kind: RequestKind; message: string }) =>
    call<HelpRequest>("POST", "/requests", r),
  inbox: () => call<HelpRequest[]>("GET", "/requests/inbox"),
  sent: () => call<HelpRequest[]>("GET", "/requests/sent"),
};
