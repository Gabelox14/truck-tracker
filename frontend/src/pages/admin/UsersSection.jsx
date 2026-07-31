import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../../lib/apiClient";
import { Badge, Card, EmptyState } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";

const ROLES = ["admin", "dispatcher", "driver"];

export default function UsersSection() {
  const { profile: myProfile } = useAuth();
  const isAdmin = myProfile?.role === "admin";
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { data: profiles, isLoading } = useQuery({
    queryKey: ["profiles"],
    queryFn: async () => (await apiClient.get("/profiles")).data,
  });

  const changeRole = useMutation({
    mutationFn: async ({ id, role }) => (await apiClient.patch(`/profiles/${id}`, { role })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profiles"] });
      showToast("Rol actualizado");
    },
    onError: (err) => showToast(err.response?.data?.detail ?? "No se pudo cambiar el rol", "error"),
  });

  return (
    <Card title="Usuarios">
      {isLoading ? (
        <p className="text-sm text-slate-400">Cargando...</p>
      ) : profiles?.length ? (
        <ul className="divide-y divide-slate-100">
          {profiles.map((p) => (
            <li key={p.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-900">{p.full_name}</p>
                <p className="truncate text-xs text-slate-400">
                  {p.email} · CI {p.cedula}
                </p>
              </div>
              {isAdmin ? (
                <select
                  value={p.role}
                  onChange={(e) => changeRole.mutate({ id: p.id, role: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm outline-none focus:border-slate-900 sm:w-auto"
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              ) : (
                <Badge>{p.role}</Badge>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState>No hay usuarios registrados todavía.</EmptyState>
      )}
    </Card>
  );
}
