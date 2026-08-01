import { useAuth } from "../context/AuthContext";
import { Badge } from "./ui";

const ROLE_LABEL = {
  admin: "Administrador",
  dispatcher: "Despachante",
  driver: "Chofer",
};

export function Layout({ children }) {
  const { profile, signOut } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="" className="h-9 w-auto" />
            <h1 className="text-base font-semibold tracking-tight text-slate-900">Full Soluciones S.A G&amp;A</h1>
          </div>
          <div className="flex items-center gap-3">
            {profile && <Badge>{ROLE_LABEL[profile.role] ?? profile.role}</Badge>}
            <button onClick={signOut} className="text-sm text-slate-500 hover:text-slate-900">
              Salir
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
    </div>
  );
}
