import { useCallback, useEffect, useState } from "react";
import { api, DEV_USER_KEY, type Me } from "./api";
import ProfileForm from "./components/ProfileForm";
import FindPeers from "./components/FindPeers";
import RequestList from "./components/RequestList";

type Tab = "profile" | "peers" | "inbox" | "sent";

const TABS: { id: Tab; label: string }[] = [
  { id: "profile", label: "My Profile" },
  { id: "peers", label: "Find Peers" },
  { id: "inbox", label: "Inbox" },
  { id: "sent", label: "Sent" },
];

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("peers");

  const loadMe = useCallback(() => {
    setError(null);
    api.me()
      .then((m) => {
        setMe(m);
        if (!m.profile) setTab("profile"); // new users start by creating a profile
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(loadMe, [loadMe]);

  if (error) return <main className="page"><p className="error">Couldn't load: {error}</p></main>;
  if (!me) return <main className="page"><p className="muted">Loading…</p></main>;

  const hasProfile = me.profile !== null;

  return (
    <main className="page">
      <header className="header">
        <div>
          <h1>Skill &amp; Knowledge Matchmaker</h1>
          <p className="muted">Find someone on another engagement who's solved it before.</p>
        </div>
        <div className="whoami">
          Signed in as <strong>{me.email}</strong>
          {import.meta.env.DEV && <DevUserSwitcher current={me.email} />}
        </div>
      </header>

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? "tab active" : "tab"}
            disabled={!hasProfile && t.id !== "profile"}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "profile" && (
        <ProfileForm
          profile={me.profile}
          onSaved={(profile) => setMe({ ...me, profile })}
        />
      )}
      {tab === "peers" && <FindPeers onSent={() => setTab("sent")} />}
      {tab === "inbox" && <RequestList box="inbox" />}
      {tab === "sent" && <RequestList box="sent" />}
    </main>
  );
}

// Only rendered in local development (npm run dev). Lets one person act as Maya or Jordan.
function DevUserSwitcher({ current }: { current: string }) {
  const users = ["maya@example.com", "jordan@example.com", "sam@example.com"];
  return (
    <select
      className="dev-switch"
      value={current}
      onChange={(e) => {
        localStorage.setItem(DEV_USER_KEY, e.target.value);
        window.location.reload();
      }}
    >
      {users.map((u) => <option key={u} value={u}>dev: {u}</option>)}
    </select>
  );
}
