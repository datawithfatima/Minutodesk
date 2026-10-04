import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Inbox,
  Search,
  UserCog,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Outlet, useMatch, useSearchParams } from "react-router-dom";
import { listarClientes, listarTickets } from "../../api";
import { obtenerUsuario } from "../../auth";
import { normalizarTexto } from "../../texto";
import Alert from "../../components/ui/Alert";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";
import { inputClass, labelClass } from "../../components/ui/formStyles";
import EstadoBadge from "../../components/EstadoBadge";
import MinutitoPanelProximamente from "../../components/MinutitoPanelProximamente";

const TABS = [
  { key: "todos", label: "Todos", estado: null },
  { key: "en_proceso", label: "En proceso", estado: "en_proceso" },
  { key: "abierto", label: "Pendientes", estado: "abierto" },
  { key: "resuelto", label: "Resueltos", estado: "resuelto" },
];

const POR_PAGINA = 10;

function StatCard({ icon: Icon, label, valor }) {
  return (
    <Card>
      <Card.Body className="flex items-center gap-3">
        <Icon className="shrink-0 text-gray-700" size={20} />
        <div>
          <div className="text-lg font-bold text-gray-900">{valor}</div>
          <div className="text-xs text-gray-500">{label}</div>
        </div>
      </Card.Body>
    </Card>
  );
}

function FilaCompacta({ base, ticket, cliente, seleccionado }) {
  return (
    <Link
      to={`${base}/${ticket.id}`}
      className={`block px-3 py-2.5 transition-colors ${
        seleccionado ? "bg-gray-100" : "hover:bg-gray-50"
      }`}
    >
      <div className="mb-0.5 flex items-center justify-between gap-2">
        <span className="truncate text-xs text-gray-500">
          #{ticket.id} · {cliente?.nombre || "—"}
        </span>
        <EstadoBadge estado={ticket.estado} />
      </div>
      <div className="truncate text-sm text-gray-900">{ticket.texto}</div>
      <div className="text-xs text-gray-400">
        {ticket.categoria_predicha || "Sin categoría"} ·{" "}
        {new Date(ticket.creado_en).toLocaleDateString()}
      </div>
    </Link>
  );
}

export default function TicketsWorkspace({
  base = "/tecnico/tickets",
  soloAsignados = false,
  titulo = "Tickets",
  subtitulo = "Gestiona y da seguimiento a las solicitudes de soporte.",
}) {
  const match = useMatch(`${base}/:id`);
  const seleccionadoId = match ? Number(match.params.id) : null;
  const compacto = seleccionadoId != null;

  const [params] = useSearchParams();
  const yoId = obtenerUsuario()?.id;

  const [tickets, setTickets] = useState([]);
  const [clientesPorId, setClientesPorId] = useState({});
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("todos");
  const [categoria, setCategoria] = useState("");
  const [busqueda, setBusqueda] = useState(params.get("q") ?? "");
  const [pagina, setPagina] = useState(1);

  const qUrl = params.get("q");
  useEffect(() => {
    if (qUrl !== null) {
      setBusqueda(qUrl);
      setPagina(1);
    }
  }, [qUrl]);

  const cargarTickets = useCallback(
    () => listarTickets(soloAsignados ? { tecnico_id: yoId } : {}),
    [soloAsignados, yoId]
  );

  useEffect(() => {
    Promise.all([cargarTickets(), listarClientes()])
      .then(([listaTickets, listaClientes]) => {
        setTickets(listaTickets);
        setClientesPorId(Object.fromEntries(listaClientes.map((c) => [c.id, c])));
      })
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }, [cargarTickets]);

  const recargar = useCallback(() => cargarTickets().then(setTickets), [cargarTickets]);

  const categorias = useMemo(
    () => [...new Set(tickets.map((t) => t.categoria_predicha).filter(Boolean))].sort(),
    [tickets]
  );

  const hoy = new Date().toDateString();
  const stats = useMemo(
    () => ({
      total: tickets.length,
      enProceso: tickets.filter((t) => t.estado === "en_proceso").length,
      pendientes: tickets.filter((t) => t.estado === "abierto").length,
      resueltosHoy: tickets.filter(
        (t) =>
          t.estado === "resuelto" &&
          t.cerrado_en &&
          new Date(t.cerrado_en).toDateString() === hoy
      ).length,
    }),
    [tickets, hoy]
  );

  const filtrados = useMemo(() => {
    const tabActual = TABS.find((t) => t.key === tab);
    return tickets.filter((t) => {
      if (tabActual.estado && t.estado !== tabActual.estado) return false;
      if (categoria && t.categoria_predicha !== categoria) return false;
      if (busqueda && !normalizarTexto(t.texto).includes(normalizarTexto(busqueda))) return false;
      return true;
    });
  }, [tickets, tab, categoria, busqueda]);

  const totalPaginas = Math.max(1, Math.ceil(filtrados.length / POR_PAGINA));
  const paginaSegura = Math.min(pagina, totalPaginas);
  const visibles = filtrados.slice((paginaSegura - 1) * POR_PAGINA, paginaSegura * POR_PAGINA);

  function cambiarTab(key) {
    setTab(key);
    setPagina(1);
  }

  return (
    <div className="flex flex-col items-start gap-4 lg:flex-row">
      <div
        className={`w-full min-w-0 ${compacto ? "lg:w-[360px] lg:shrink-0 xl:w-[420px]" : ""}`}
      >
        <PageHeader
          icon={soloAsignados ? UserCog : Inbox}
          title={titulo}
          subtitle={subtitulo}
        />

        {error && (
          <Alert variant="danger" className="mb-3">
            {error}
          </Alert>
        )}
        {cargando && <Spinner size="sm" />}

        {!cargando && (
          <>
            <div
              className={`mb-4 grid gap-4 ${
                compacto ? "grid-cols-2" : "grid-cols-2 sm:grid-cols-4"
              }`}
            >
              <StatCard icon={Inbox} label="Total" valor={stats.total} />
              <StatCard icon={Clock} label="En proceso" valor={stats.enProceso} />
              <StatCard icon={Clock} label="Pendientes" valor={stats.pendientes} />
              <StatCard icon={CheckCircle2} label="Resueltos hoy" valor={stats.resueltosHoy} />
            </div>

            <div className="mb-4 flex flex-wrap gap-2">
              {TABS.map((t) => {
                const conteo = t.estado
                  ? tickets.filter((x) => x.estado === t.estado).length
                  : tickets.length;
                return (
                  <button
                    key={t.key}
                    onClick={() => cambiarTab(t.key)}
                    className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      tab === t.key
                        ? "bg-gray-900 text-white"
                        : "border border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
                    }`}
                  >
                    {t.label} ({conteo})
                  </button>
                );
              })}
            </div>

            <Card className="mb-4">
              <Card.Body className="flex flex-wrap items-end gap-3">
                <div>
                  <label className={labelClass}>Categoría</label>
                  <select
                    className={`${inputClass} w-44`}
                    value={categoria}
                    onChange={(e) => {
                      setCategoria(e.target.value);
                      setPagina(1);
                    }}
                  >
                    <option value="">Todas</option>
                    {categorias.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="min-w-[180px] flex-1">
                  <label className={labelClass}>Buscar</label>
                  <div className="relative">
                    <Search
                      size={16}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                    />
                    <input
                      className={`${inputClass} pl-9`}
                      value={busqueda}
                      onChange={(e) => {
                        setBusqueda(e.target.value);
                        setPagina(1);
                      }}
                      placeholder="Buscar por texto del ticket..."
                    />
                  </div>
                </div>
              </Card.Body>
            </Card>

            {visibles.length === 0 && (
              <Alert variant="secondary">No hay tickets para este filtro.</Alert>
            )}

            {visibles.length > 0 && compacto && (
              <Card className="mb-3 divide-y divide-gray-100 overflow-hidden">
                {visibles.map((t) => (
                  <FilaCompacta
                    key={t.id}
                    base={base}
                    ticket={t}
                    cliente={clientesPorId[t.cliente_id]}
                    seleccionado={t.id === seleccionadoId}
                  />
                ))}
              </Card>
            )}

            {visibles.length > 0 && !compacto && (
              <Card className="mb-3 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-50 text-gray-600">
                    <tr>
                      <th className="px-3 py-2">#</th>
                      <th className="px-3 py-2">Texto</th>
                      <th className="px-3 py-2">Usuario</th>
                      <th className="px-3 py-2">Categoría</th>
                      <th className="px-3 py-2">Estado</th>
                      <th className="px-3 py-2">Fecha</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {visibles.map((t) => (
                      <tr key={t.id} className="hover:bg-gray-50">
                        <td className="px-3 py-2">
                          <Link
                            to={`${base}/${t.id}`}
                            className="text-blue-600 hover:underline"
                          >
                            {t.id}
                          </Link>
                        </td>
                        <td className="max-w-xs truncate px-3 py-2">{t.texto}</td>
                        <td className="px-3 py-2">{clientesPorId[t.cliente_id]?.nombre || "—"}</td>
                        <td className="px-3 py-2">{t.categoria_predicha || "—"}</td>
                        <td className="px-3 py-2">
                          <EstadoBadge estado={t.estado} />
                        </td>
                        <td className="px-3 py-2 text-gray-500">
                          {new Date(t.creado_en).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            )}

            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>
                Mostrando {visibles.length} de {filtrados.length} tickets
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={paginaSegura <= 1}
                  onClick={() => setPagina((p) => p - 1)}
                  className="rounded-md border border-gray-200 p-1 disabled:opacity-40"
                >
                  <ChevronLeft size={16} />
                </button>
                <span>
                  {paginaSegura} / {totalPaginas}
                </span>
                <button
                  disabled={paginaSegura >= totalPaginas}
                  onClick={() => setPagina((p) => p + 1)}
                  className="rounded-md border border-gray-200 p-1 disabled:opacity-40"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {compacto && (
        <div className="w-full min-w-0 lg:sticky lg:top-6 lg:max-h-[calc(100vh-3rem)] lg:flex-1 lg:overflow-y-auto">
          <Outlet context={{ recargar, base }} />
        </div>
      )}

      {compacto && (
        <div className="hidden w-72 shrink-0 2xl:sticky 2xl:top-6 2xl:block 2xl:h-[calc(100vh-3rem)]">
          <MinutitoPanelProximamente />
        </div>
      )}
    </div>
  );
}
