// Los choferes que crea el admin entran con un usuario ("carlos"); Supabase necesita
// un email, que es usuario@este-dominio. Debe coincidir con DRIVER_EMAIL_DOMAIN del backend.
export const DRIVER_EMAIL_DOMAIN =
  import.meta.env.VITE_DRIVER_EMAIL_DOMAIN || "choferes.fullsoluciones.app";

// "Carlos" → "carlos@choferes…"; un email se usa tal cual.
export function toLoginEmail(value) {
  const login = value.trim().toLowerCase();
  return login.includes("@") ? login : `${login}@${DRIVER_EMAIL_DOMAIN}`;
}
