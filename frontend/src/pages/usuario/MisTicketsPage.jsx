import { Search, Ticket } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { listarTickets } from "../../api";
import { normalizarTexto } from "../../texto";
import Alert from "../../components/ui/Alert";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";
import { inputClass } from "../../components/ui/formStyles";
import EstadoBadge from "../../components/EstadoBadge";

export default function MisTicketsPage() {
  const [params] = useSearchParams();
  const [tickets, setTickets] = useState([]);
  const [busqueda, setBusqueda] = useState(params.get("q") ?? "");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setBusqueda(params.get("q") ?? "");
  }, [params]);

  useEffect(() => {
    listarTickets()
      .then(setTickets)
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }, []);

  const visibles = useMemo(
    () =>
      tickets.filter(
        (t) => !busqueda || normalizarTexto(t.texto).includes(normalizarTexto(busqueda))
      ),
    [tickets, busqueda]
  );

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

      {!cargando && tickets.length > 0 && (
        <Card className="mb-4">
          <Card.Body>
            <div className="relative max-w-md">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
              <input
                className={`${inputClass} pl-9`}
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                placeholder="Buscar en mis tickets..."
              />
            </div>
          </Card.Body>
        </Card>
      )}

      {!cargando && tickets.length === 0 && (
        <Alert variant="secondary">
          Todavía no has creado ningún ticket. Puedes <Link to="/usuario/nuevo-ticket" className="font-medium underline">crear uno</Link> directamente
          o escribir tu consulta a Minutito en Inicio.
        </Alert>
      )}

      {!cargando && tickets.length > 0 && visibles.length === 0 && (
        <Alert variant="secondary">Ningún ticket coincide con la búsqueda.</Alert>
      )}

      {!cargando && visibles.length > 0 && (
        <Card className="divide-y divide-gray-100 overflow-hidden md:hidden">
          {visibles.map((t) => (
            <Link key={t.id} to={`/usuario/tickets/${t.id}`} className="block px-4 py-3 hover:bg-marfil">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-acento">#{t.id}</span>
                <EstadoBadge estado={t.estado} />
              </div>
              <div className="line-clamp-2 text-sm text-gray-800">{t.texto}</div>
              <div className="mt-1 truncate text-xs text-gray-500">
                {[t.tipo_predicho, t.categoria_predicha].filter(Boolean).join(" · ") || "Sin clasificar"}
              </div>
            </Link>
          ))}
        </Card>
      )}

      {!cargando && visibles.length > 0 && (
        <Card className="hidden overflow-x-auto md:block">
          <table className="w-full text-left text-sm">
            <thead className="bg-marfil text-xs uppercase tracking-wide text-gray-500 [&_th]:font-medium">
              <tr>
                <th className="px-3 py-2">#</th>
                <th className="px-3 py-2">Texto</th>
                <th className="px-3 py-2">Tipo</th>
                <th className="px-3 py-2">Categoría</th>
                <th className="px-3 py-2">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {visibles.map((t) => (
                <tr key={t.id} className="hover:bg-marfil">
                  <td className="px-3 py-2">
                    <Link to={`/usuario/tickets/${t.id}`} className="text-acento hover:underline">
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
