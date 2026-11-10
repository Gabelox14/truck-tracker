import { useAuth } from "../context/AuthContext";
import { icons } from "./icons";
import { Badge } from "./ui";

export const ROLE_LABEL = {
  admin: "Administrador",
  dispatcher: "Despachante",
  driver: "Chofer",
};

// bottomNav: barra de secciones fija abajo en el celular (panel admin). El contenido deja
// espacio para que la barra no tape lo último de la página.
export function Layout({ children, bottomNav = null }) {
  const { profile, signOut } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="pt-safe sticky top-0 z-30 border-b border-slate-200 bg-white md:static">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-1.5 md:py-3">
          <div className="flex min-w-0 items-center gap-2">
            <img src="/logo.png" alt="" className="h-9 w-auto shrink-0 md:h-11" />
            <h1 className="truncate text-sm font-semibold tracking-tight text-slate-900 md:text-base">
              Full Soluciones G&amp;A S.A
            </h1>
          </div>
          <div className="flex shrink-0 items-center gap-1 md:gap-3">
            {profile && (
              <span className="hidden sm:inline-flex">
                <Badge>{ROLE_LABEL[profile.role] ?? profile.role}</Badge>
              </span>
            )}
            <button
              onClick={signOut}
              aria-label="Salir"
              className="-mr-2 inline-flex h-11 w-11 items-center justify-center rounded-lg text-slate-500 transition hover:text-slate-900 active:bg-slate-100 md:mr-0 md:h-auto md:w-auto"
            >
              <icons.logout className="h-5 w-5 md:hidden" />
              <span className="hidden text-sm md:inline">Salir</span>
            </button>
          </div>
        </div>
      </header>
      <main
        className={`mx-auto max-w-5xl px-4 py-5 md:py-6 ${
          bottomNav ? "pb-[calc(6rem+env(safe-area-inset-bottom))] md:pb-6" : ""
        }`}
      >
        {children}
      </main>
      {bottomNav}
    </div>
  );
}
