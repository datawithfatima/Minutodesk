import { Users } from "lucide-react";
import { useEffect, useState } from "react";
import { listarClientes } from "../../api";
import Alert from "../../components/ui/Alert";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";

const ROL_LABEL = {
  colaborador: "Colaborador",
  tecnico: "Técnico",
};

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
        title="Clientes / Usuarios"
        subtitle="Colaboradores y técnicos registrados en MinutoDesk."
      />

      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}
      {cargando && <Spinner size="sm" />}

      {!cargando && (
        <Card className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="px-3 py-2">Nombre</th>
                <th className="px-3 py-2">Área</th>
                <th className="px-3 py-2">Correo</th>
                <th className="px-3 py-2">Rol</th>
                <th className="px-3 py-2">Puntos</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {clientes.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium text-gray-900">{c.nombre}</td>
                  <td className="px-3 py-2">{c.area}</td>
                  <td className="px-3 py-2 text-gray-500">{c.email}</td>
                  <td className="px-3 py-2">{ROL_LABEL[c.rol] || c.rol}</td>
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
