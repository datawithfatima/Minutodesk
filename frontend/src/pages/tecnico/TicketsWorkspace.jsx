import {
  ArrowLeft,
  CheckCircle2,
  ChevronLeft,
  CircleDot,
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
import { inputClass } from "../../components/ui/formStyles";
import EstadoBadge from "../../components/EstadoBadge";
import { PrioridadPastilla } from "../../components/tickets/Pastillas";

const TABS = [
  { key: "todos", label: "Todos", estado: null },
  { key: "abierto", label: "Nuevos", estado: "abierto" },
  { key: "en_proceso", label: "En proceso", estado: "en_proceso" },
  { key: "resuelto", label: "Resueltos", estado: "resuelto" },
  { key: "cancelado", label: "Cancelados", estado: "cancelado" },
];

const POR_PAGINA = 10;

function StatCard({ icon: Icon, label, valor }) {
  return (
    <Card>
      <Card.Body className="flex items-center gap-3">
        <Icon className="shrink-0 text-gray-700" size={20} />
        <div>
          <div className="text-lg font-bold text-noche">{valor}</div>
          <div className="text-xs text-gray-500">{label}</div>
        </div>
      </Card.Body>
    </Card>
  );
}

function FilaCompacta({ base, ticket, cliente }) {
  return (
    <Link to={`${base}/${ticket.id}`} className="block px-4 py-3 transition-colors duration-150 hover:bg-marfil">
      <div className="mb-0.5 flex items-center justify-between gap-2">
        <span className="truncate text-xs text-gray-500">
          #{ticket.id} · {cliente?.nombre || "—"}
        </span>
        <EstadoBadge estado={ticket.estado} />
      </div>
      <div className="truncate text-sm text-noche">{ticket.texto}</div>
      <div className="flex items-center gap-2 text-xs text-gray-400">
        <span className="truncate">
          {ticket.categoria || ticket.categoria_predicha || "Sin categoría"} ·{" "}
          {new Date(ticket.creado_en).toLocaleDateString()}
        </span>
        <PrioridadPastilla prioridad={ticket.prioridad} />
      </div>
    </Link>
  );
}

function PasoTicket({ ticket, base, etiqueta, Icono, alFinal = false }) {
  const contenido = (
    <>
      {!alFinal && <Icono size={16} aria-hidden="true" />}
      <span className="hidden sm:inline">{etiqueta}</span>
      {alFinal && <Icono size={16} aria-hidden="true" />}
    </>
  );
  const cls =
    "inline-flex h-9 items-center gap-1 rounded-lg border border-linea px-2.5 text-sm font-medium transition-colors duration-150";
  if (!ticket) {
    return (
      <span aria-disabled="true" aria-label={etiqueta} className={`${cls} cursor-not-allowed text-gray-300`}>
        {contenido}
      </span>
    );
  }
  return (
    <Link
      to={`${base}/${ticket.id}`}
      aria-label={`${etiqueta}: ticket #${ticket.id}`}
      title={`#${ticket.id} · ${ticket.texto}`}
      className={`${cls} bg-white text-noche hover:bg-marfil`}
    >
      {contenido}
    </Link>
  );
}

function BarraDetalle({ base, titulo, lista, seleccionadoId, filtro }) {
  const i = lista.findIndex((t) => t.id === seleccionadoId);
  const anterior = i > 0 ? lista[i - 1] : null;
  const siguiente = i >= 0 && i < lista.length - 1 ? lista[i + 1] : null;
  return (
    <nav
      aria-label="Navegación entre tickets"
      className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-linea bg-white px-2 py-2 sm:px-3"
    >
      <div className="flex min-w-0 items-center gap-2">
        <Link
          to={base}
          className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-lg px-2.5 text-sm font-medium text-noche transition-colors duration-150 hover:bg-marfil"
        >
          <ArrowLeft size={16} aria-hidden="true" />
          {titulo}
        </Link>
        {i >= 0 && (
          <span className="hidden min-w-0 truncate text-sm text-gray-500 md:inline">
            Ticket {i + 1} de {lista.length}
            {filtro && <> · {filtro}</>}
          </span>
        )}
      </div>
      {i >= 0 && (
        <div className="flex shrink-0 items-center gap-1.5">
          <span className="mr-1 text-xs text-gray-500 md:hidden">
            {i + 1} / {lista.length}
          </span>
          <PasoTicket ticket={anterior} base={base} etiqueta="Anterior" Icono={ChevronLeft} />
          <PasoTicket ticket={siguiente} base={base} etiqueta="Siguiente" Icono={ChevronRight} alFinal />
        </div>
      )}
    </nav>
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
      nuevos: tickets.filter((t) => t.estado === "abierto").length,
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

  // Con un ticket abierto se ve solo su detalle; arriba queda lo necesario para moverse:
  // volver a la lista (con los mismos filtros) y pasar al anterior o al siguiente.
  if (compacto) {
    const tabActual = TABS.find((t) => t.key === tab);
    const filtroActivo = [
      tab !== "todos" && tabActual.label,
      categoria,
      busqueda && `«${busqueda}»`,
    ]
      .filter(Boolean)
      .join(" · ");
    return (
      <div className="mx-auto w-full max-w-[1200px]">
        <BarraDetalle
          base={base}
          titulo={titulo}
          lista={filtrados}
          seleccionadoId={seleccionadoId}
          filtro={filtroActivo}
        />
        <Outlet context={{ recargar, base }} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader icon={soloAsignados ? UserCog : Inbox} title={titulo} subtitle={subtitulo} />

      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}
      {cargando && <Spinner size="sm" />}

      {!cargando && (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-4">
            <StatCard icon={Inbox} label="Total" valor={stats.total} />
            <StatCard icon={CircleDot} label="Nuevos" valor={stats.nuevos} />
            <StatCard icon={Clock} label="En proceso" valor={stats.enProceso} />
            <StatCard icon={CheckCircle2} label="Resueltos hoy" valor={stats.resueltosHoy} />
          </div>

          <Card className="mb-4">
            <Card.Body className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div
                role="tablist"
                aria-label="Filtrar por estado"
                className="-mx-1 flex gap-1.5 overflow-x-auto px-1 py-0.5"
              >
                {TABS.map((t) => {
                  const conteo = t.estado
                    ? tickets.filter((x) => x.estado === t.estado).length
                    : tickets.length;
                  return (
                    <button
                      key={t.key}
                      role="tab"
                      aria-selected={tab === t.key}
                      onClick={() => cambiarTab(t.key)}
                      className={`shrink-0 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition-colors duration-150 ${
                        tab === t.key
                          ? "bg-noche text-white"
                          : "text-gray-600 ring-1 ring-inset ring-linea hover:bg-marfil"
                      }`}
                    >
                      {t.label}{" "}
                      <span className={tab === t.key ? "text-white/70" : "text-gray-400"}>{conteo}</span>
                    </button>
                  );
                })}
              </div>
              <div className="flex flex-col gap-3 sm:flex-row">
                <div className="sm:w-52">
                  <label htmlFor="filtro-categoria" className="sr-only">
                    Categoría
                  </label>
                  <select
                    id="filtro-categoria"
                    className={inputClass}
                    value={categoria}
                    onChange={(e) => {
                      setCategoria(e.target.value);
                      setPagina(1);
                    }}
                  >
                    <option value="">Todas las categorías</option>
                    {categorias.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="relative min-w-0 sm:w-64">
                  <label htmlFor="filtro-busqueda" className="sr-only">
                    Buscar
                  </label>
                  <Search
                    size={16}
                    aria-hidden="true"
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                  />
                  <input
                    id="filtro-busqueda"
                    className={`${inputClass} pl-9`}
                    value={busqueda}
                    onChange={(e) => {
                      setBusqueda(e.target.value);
                      setPagina(1);
                    }}
                    placeholder="Buscar por texto del ticket…"
                  />
                </div>
              </div>
            </Card.Body>
          </Card>

          {visibles.length === 0 && (
            <Alert variant="secondary">No hay tickets para este filtro.</Alert>
          )}

          {/* Móvil: tarjetas. Tablet y escritorio: tabla. */}
          {visibles.length > 0 && (
            <Card className="mb-3 divide-y divide-gray-100 overflow-hidden md:hidden">
              {visibles.map((t) => (
                <FilaCompacta key={t.id} base={base} ticket={t} cliente={clientesPorId[t.cliente_id]} />
              ))}
            </Card>
          )}

          {visibles.length > 0 && (
            <Card className="mb-3 hidden overflow-x-auto md:block">
              <table className="w-full text-left text-sm">
                <thead className="bg-marfil text-xs uppercase tracking-wide text-gray-500 [&_th]:font-medium">
                  <tr>
                    <th className="px-4 py-2.5">#</th>
                    <th className="px-3 py-2.5">Solicitud</th>
                    <th className="px-3 py-2.5">Usuario</th>
                    <th className="px-3 py-2.5">Categoría</th>
                    <th className="px-3 py-2.5">Prioridad</th>
                    <th className="px-3 py-2.5">Estado</th>
                    <th className="px-4 py-2.5">Fecha</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {visibles.map((t) => (
                    <tr key={t.id} className="transition-colors duration-150 hover:bg-marfil">
                      <td className="px-4 py-3 text-gray-500">{t.id}</td>
                      <td className="max-w-xs px-3 py-3">
                        <Link
                          to={`${base}/${t.id}`}
                          className="block truncate rounded font-medium text-noche hover:text-acento"
                        >
                          {t.texto}
                        </Link>
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-gray-600">
                        {clientesPorId[t.cliente_id]?.nombre || "—"}
                      </td>
                      <td className="px-3 py-3 text-gray-600">{t.categoria || t.categoria_predicha || "—"}</td>
                      <td className="px-3 py-3">
                        <PrioridadPastilla prioridad={t.prioridad} />
                      </td>
                      <td className="px-3 py-3">
                        <EstadoBadge estado={t.estado} />
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-gray-500">
                        {new Date(t.creado_en).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}

          <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-gray-500">
            <span>
              Mostrando {visibles.length} de {filtrados.length} tickets
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={paginaSegura <= 1}
                onClick={() => setPagina((p) => p - 1)}
                aria-label="Página anterior"
                className="rounded-lg border border-linea bg-white p-1.5 hover:bg-marfil disabled:opacity-40"
              >
                <ChevronLeft size={16} aria-hidden="true" />
              </button>
              <span>
                {paginaSegura} / {totalPaginas}
              </span>
              <button
                disabled={paginaSegura >= totalPaginas}
                onClick={() => setPagina((p) => p + 1)}
                aria-label="Página siguiente"
                className="rounded-lg border border-linea bg-white p-1.5 hover:bg-marfil disabled:opacity-40"
              >
                <ChevronRight size={16} aria-hidden="true" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
