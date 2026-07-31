import { useState } from "react";

export function Button({ variant = "primary", className = "", ...props }) {
  const variants = {
    primary: "bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50",
    danger: "bg-red-50 text-red-700 hover:bg-red-100 disabled:opacity-50",
    ghost: "text-slate-600 hover:bg-slate-100 disabled:opacity-50",
  };
  return (
    <button
      className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${variants[variant]} ${className}`}
      {...props}
    />
  );
}

export function ConfirmButton({ onConfirm, pending = false, children = "Eliminar", className = "" }) {
  const [confirming, setConfirming] = useState(false);

  if (confirming) {
    return (
      <span className="inline-flex items-center gap-2">
        <span className="text-sm text-slate-500">¿Eliminar?</span>
        <Button
          variant="danger"
          disabled={pending}
          onClick={() => {
            onConfirm();
            setConfirming(false);
          }}
        >
          Sí
        </Button>
        <Button variant="ghost" onClick={() => setConfirming(false)}>
          No
        </Button>
      </span>
    );
  }

  return (
    <Button variant="danger" className={className} onClick={() => setConfirming(true)}>
      {children}
    </Button>
  );
}

export function Input({ className = "", ...props }) {
  return (
    <input
      className={`w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900 ${className}`}
      {...props}
    />
  );
}

export function Select({ className = "", ...props }) {
  return (
    <select
      className={`w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900 ${className}`}
      {...props}
    />
  );
}

export function Card({ title, children, action }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      {(title || action) && (
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          {title && <h2 className="text-sm font-semibold text-slate-900">{title}</h2>}
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

export function Badge({ children, tone = "slate" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    amber: "bg-amber-100 text-amber-800",
    emerald: "bg-emerald-100 text-emerald-800",
    red: "bg-red-100 text-red-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function ErrorText({ children }) {
  if (!children) return null;
  return <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{children}</p>;
}

export function EmptyState({ children }) {
  return <p className="py-6 text-center text-sm text-slate-400">{children}</p>;
}
