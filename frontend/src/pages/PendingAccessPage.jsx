import { useAuth } from "../context/AuthContext";

export default function PendingAccessPage() {
  const { signOut } = useAuth();

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6 text-slate-500">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8v4" />
            <path d="M12 16h.01" />
          </svg>
        </div>
        <h1 className="mt-4 text-xl font-semibold text-slate-900">Cuenta sin asignar</h1>
        <p className="mt-2 text-sm text-slate-500">
          Tu correo está verificado, pero todavía no te asignaron como chofer. Pedile a un
          administrador o despachante que te agregue desde la sección Choferes.
        </p>
        <button
          onClick={signOut}
          className="mt-6 text-sm font-medium text-slate-500 hover:text-slate-900"
        >
          Salir
        </button>
      </div>
    </div>
  );
}
