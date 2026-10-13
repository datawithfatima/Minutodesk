import { Users } from "lucide-react";
import { useEffect, useState } from "react";
import { listarClientes } from "../../api";
import { ETIQUETA_ROL } from "../../texto";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";

export default function ClientesPage() {
  const [clientes, setClientes] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    listarClientes()
      .then(setClientes)
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }, []);

  return (
    <>
      <PageHeader
        icon={Users}
        title="Usuarios"
        subtitle="Personas registradas en MinutoDesk (solo lectura). La gestión de cuentas la hace el administrador."
      />

      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}
      {cargando && <Spinner size="sm" />}

      {!cargando && (
        <Card className="divide-y divide-gray-100 overflow-hidden md:hidden">
          {clientes.map((c) => (
            <div key={c.id} className="px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate font-medium text-noche">{c.nombre}</div>
                  <div className="truncate text-sm text-gray-500">{c.email}</div>
                </div>
                <Badge color={c.activo ? "green" : "gray"}>{c.activo ? "Activo" : "Inactivo"}</Badge>
              </div>
              <div className="mt-1 text-xs text-gray-500">
                {ETIQUETA_ROL[c.rol] || c.rol} · {c.area} · {c.puntos} pts
              </div>
            </div>
          ))}
        </Card>
      )}

      {!cargando && (
        <Card className="hidden overflow-x-auto md:block">
          <table className="w-full text-left text-sm">
            <thead className="bg-marfil text-xs uppercase tracking-wide text-gray-500 [&_th]:font-medium">
              <tr>
                <th className="px-3 py-2">Nombre</th>
                <th className="px-3 py-2">Área</th>
                <th className="px-3 py-2">Correo</th>
                <th className="px-3 py-2">Rol</th>
                <th className="px-3 py-2">Estado</th>
                <th className="px-3 py-2">Puntos</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {clientes.map((c) => (
                <tr key={c.id} className="hover:bg-marfil">
                  <td className="px-3 py-2 font-medium text-noche">{c.nombre}</td>
                  <td className="px-3 py-2">{c.area}</td>
                  <td className="px-3 py-2 text-gray-500">{c.email}</td>
                  <td className="px-3 py-2">{ETIQUETA_ROL[c.rol] || c.rol}</td>
                  <td className="px-3 py-2">
                    <Badge color={c.activo ? "green" : "gray"}>{c.activo ? "Activo" : "Inactivo"}</Badge>
                  </td>
                  <td className="px-3 py-2">{c.puntos}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </>
  );
}
