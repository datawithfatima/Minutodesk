import { History, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { listarTickets, obtenerGamificacion } from "../../api";
import { obtenerUsuario } from "../../auth";
import { formatearDuracion, normalizarTexto } from "../../texto";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";
import { inputClass } from "../../components/ui/formStyles";

const SUBTITULOS = {
  usuario:
    "Tus consultas ya resueltas: quién las resolvió, cuánto tardó y los puntos que ganaste.",
  tecnico: "Los tickets que atendiste y que ya están resueltos.",
  administrador: "Todos los tickets resueltos del sistema.",
};

export default function HistoricoPage() {
  const usuario = obtenerUsuario();
  const seccion = useLocation().pathname.split("/")[1]; // usuario | tecnico | admin
  const esUsuario = usuario.rol === "usuario";

  const [tickets, setTickets] = useState([]);
  const [puntosPorTicket, setPuntosPorTicket] = useState({});
  const [busqueda, setBusqueda] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const filtros = { estado: "resuelto" };
    if (usuario.rol === "tecnico") filtros.tecnico_id = usuario.id;
    Promise.all([listarTickets(filtros), esUsuario ? obtenerGamificacion(usuario.id) : null])
      .then(([lista, gamificacion]) => {
        setTickets(lista);
        if (gamificacion) {
          const mapa = {};
          gamificacion.historial.forEach((e) => {
            if (e.ticket_id != null) mapa[e.ticket_id] = (mapa[e.ticket_id] || 0) + e.puntos_otorgados;
          });
          setPuntosPorTicket(mapa);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }, [usuario.id, usuario.rol, esUsuario]);

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
        icon={History}
        title={usuario.rol === "administrador" ? "Histórico" : "Mi histórico"}
        subtitle={SUBTITULOS[usuario.rol]}
      />

      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}
      {cargando && <Spinner size="sm" />}

      {!cargando && (
        <>
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
                  placeholder="Buscar en el histórico..."
                />
              </div>
            </Card.Body>
          </Card>

          {visibles.length === 0 ? (
            <Alert variant="secondary">Todavía no hay tickets resueltos para mostrar.</Alert>
          ) : (
            <Card className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-gray-600">
                  <tr>
                    <th className="px-3 py-2">#</th>
                    <th className="px-3 py-2">Consulta</th>
                    <th className="px-3 py-2">Categoría</th>
                    <th className="px-3 py-2">Resuelto por</th>
                    <th className="px-3 py-2">Cerrado</th>
                    <th className="px-3 py-2">Duración</th>
                    {esUsuario && <th className="px-3 py-2">Puntos</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {visibles.map((t) => (
                    <tr key={t.id} className="hover:bg-gray-50">
                      <td className="px-3 py-2">
                        <Link
                          to={`/${seccion}/tickets/${t.id}`}
                          className="text-blue-600 hover:underline"
                        >
                          {t.id}
                        </Link>
                      </td>
                      <td className="max-w-xs truncate px-3 py-2">{t.texto}</td>
                      <td className="px-3 py-2">{t.categoria_predicha || "—"}</td>
                      <td className="px-3 py-2">
                        {t.resuelto_por === "minutito" ? (
                          <Badge color="sky">Minutito</Badge>
                        ) : (
                          <Badge color="green">Equipo de soporte</Badge>
                        )}
                      </td>
                      <td className="px-3 py-2 text-gray-500">
                        {t.cerrado_en ? new Date(t.cerrado_en).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-3 py-2 text-gray-500">
                        {t.cerrado_en ? formatearDuracion(t.creado_en, t.cerrado_en) : "—"}
                      </td>
                      {esUsuario && (
                        <td className="px-3 py-2">
                          {puntosPorTicket[t.id] ? `+${puntosPorTicket[t.id]}` : "—"}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </>
      )}
    </>
  );
}
