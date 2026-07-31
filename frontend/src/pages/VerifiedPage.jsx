import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { supabase } from "../lib/supabaseClient";

export default function VerifiedPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let active = true;

    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (!active) return;
      setStatus(session ? "verified" : "missing");
      await supabase.auth.signOut();
    });

    const timer = setTimeout(() => navigate("/login", { replace: true }), 3000);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        {status === "missing" ? (
          <>
            <h1 className="text-xl font-semibold text-slate-900">No pudimos verificar el enlace</h1>
            <p className="mt-2 text-sm text-slate-500">
              El link puede haber vencido. Probá iniciar sesión o registrate de nuevo.
            </p>
          </>
        ) : (
          <>
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6 text-emerald-700">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>
            <h1 className="mt-4 text-xl font-semibold text-slate-900">Correo verificado</h1>
            <p className="mt-2 text-sm text-slate-500">Bienvenido a Full Soluciones S.A G&amp;A</p>
          </>
        )}
        <p className="mt-6 text-xs text-slate-400">Te llevamos a iniciar sesión...</p>
      </div>
    </div>
  );
}
