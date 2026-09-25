import { Ticket } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listarTickets } from "../../api";
import Alert from "../../components/ui/Alert";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";
import EstadoBadge from "../../components/EstadoBadge";

export default function MisTicketsPage() {
  const [tickets, setTickets] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    listarTickets()
      .then(setTickets)
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }, []);

  return (
    <>
      <PageHeader
        icon={Ticket}
        title="Mis tickets"
        subtitle="Consulta el estado de tus solicitudes e incidencias."
      />

      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}
      {cargando && <Spinner size="sm" />}

      {!cargando && tickets.length === 0 && (
        <Alert variant="secondary">
          Todavía no has creado ningún ticket. Usa "Hablar con Minutito" en el menú.
        </Alert>
      )}

      {!cargando && tickets.length > 0 && (
        <Card className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="px-3 py-2">#</th>
                <th className="px-3 py-2">Texto</th>
                <th className="px-3 py-2">Tipo</th>
                <th className="px-3 py-2">Categoría</th>
                <th className="px-3 py-2">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tickets.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2">
                    <Link to={`/usuario/tickets/${t.id}`} className="text-blue-600 hover:underline">
                      {t.id}
                    </Link>
                  </td>
                  <td className="max-w-xs truncate px-3 py-2">{t.texto}</td>
                  <td className="px-3 py-2">{t.tipo_predicho || "—"}</td>
                  <td className="px-3 py-2">{t.categoria_predicha || "—"}</td>
                  <td className="px-3 py-2">
                    <EstadoBadge estado={t.estado} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </>
  );
}
