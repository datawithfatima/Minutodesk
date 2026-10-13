import { Archive, ChevronLeft, ChevronRight, Lock, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { listarTicketsHistoricos, obtenerTicketHistorico } from "../../api";
import Alert from "../../components/ui/Alert";
import Spinner from "../../components/ui/Spinner";
import { inputClass, labelClass } from "../../components/ui/formStyles";
import { COLOR_ESTADO_HISTORICO, COLOR_PRIORIDAD, GRIS_SIN_DATO, hexA } from "../../components/charts/tokens";

const POR_PAGINA = 25;

function fecha(iso) {
  return iso ? new Date(iso).toLocaleDateString("es-EC") : "—";
}

// Identificador visual de los tickets importados: el prefijo H- los separa de los de la plataforma (#12).
function IdHistorico({ id }) {
  return (
    <span className="inline-flex items-center whitespace-nowrap rounded-lg bg-gray-100 px-1.5 py-0.5 font-mono text-xs font-semibold text-gray-600">
      H-{id}
    </span>
  );
}

function Pastilla({ texto, color }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium text-gray-700"
      style={{ background: hexA(color, 0.14) }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      {texto}
    </span>
  );
}

function PastillaEstado({ estado }) {
  return <Pastilla texto={estado} color={COLOR_ESTADO_HISTORICO[estado] ?? GRIS_SIN_DATO} />;
}

function PastillaPrioridad({ prioridad }) {
  if (!prioridad) return <span className="text-xs text-gray-400">—</span>;
  return <Pastilla texto={prioridad} color={COLOR_PRIORIDAD[prioridad] ?? GRIS_SIN_DATO} />;
}

/* ───────────── Panel lateral con el detalle de un ticket ───────────── */

function Detalle({ id, onCerrar }) {
  const [t, setT] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setT(null);
    obtenerTicketHistorico(id)
      .then(setT)
      .catch((e) => setError(e.message));
  }, [id]);

  useEffect(() => {
    const alTeclear = (e) => e.key === "Escape" && onCerrar();
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [onCerrar]);

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <button aria-label="Cerrar" className="absolute inset-0 bg-noche/30" onClick={onCerrar} />
      <aside className="relative flex h-full w-full max-w-lg flex-col overflow-y-auto bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-3 border-b border-linea p-5">
          <div>
            <div className="flex items-center gap-2">
              {t && <IdHistorico id={t.id_externo} />}
              <span className="inline-flex items-center gap-1 rounded-lg bg-amber-50 px-1.5 py-0.5 text-xs font-medium text-amber-800">
                <Lock size={11} /> Histórico · solo lectura
              </span>
            </div>
            <h2 className="mt-2 text-base font-semibold text-noche">Ticket importado</h2>
          </div>
          <button onClick={onCerrar} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700" aria-label="Cerrar">
            <X size={18} />
          </button>
        </div>

        <div className="space-y-5 p-5">
          {error && <Alert variant="danger">{error}</Alert>}
          {!t && !error && <Spinner size="sm" />}
          {t && (
            <>
              <div className="flex flex-wrap gap-2">
                <PastillaEstado estado={t.estado} />
                <PastillaPrioridad prioridad={t.prioridad} />
                {t.categoria && (
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">{t.categoria}</span>
                )}
              </div>

              <div>
                <div className="mb-1 text-xs font-medium text-gray-500">Descripción</div>
                {t.descripcion ? (
                  <p className="whitespace-pre-wrap rounded-lg bg-marfil p-3 text-sm leading-relaxed text-gray-800">
                    {t.descripcion}
                  </p>
                ) : (
                  <p className="text-sm text-gray-400">Este ticket no tiene descripción en el CSV.</p>
                )}
              </div>

              <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                {[
                  ["Tipo", t.tipo],
                  ["Solicitante", t.solicitante],
                  ["Atendido por", t.asignado_a],
                  ["Creado", fecha(t.creado_en)],
                  ["Solución", fecha(t.resuelto_en)],
                ].map(([etiqueta, valor]) => (
                  <div key={etiqueta} className={etiqueta === "Tipo" ? "col-span-2" : ""}>
                    <dt className="text-xs text-gray-500">{etiqueta}</dt>
                    <dd className="text-noche">{valor || "—"}</dd>
                  </div>
                ))}
              </dl>

              <p className="rounded-lg border border-linea p-3 text-xs text-gray-500">
                Viene del CSV de la herramienta anterior. No es un ticket de MinutoDesk: no se puede
                editar ni asignar, y no cuenta en los indicadores, el ranking ni los puntos.
              </p>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}

/* ───────────── Lista ───────────── */

export default function TicketsImportados() {
  const [busqueda, setBusqueda] = useState("");
  const [q, setQ] = useState(""); // la búsqueda se aplica un instante después de teclear
  const [estado, setEstado] = useState("");
  const [categoria, setCategoria] = useState("");
  const [prioridad, setPrioridad] = useState("");
  const [pagina, setPagina] = useState(1);
  const [datos, setDatos] = useState(null);
  const [filtros, setFiltros] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [abierto, setAbierto] = useState(null);

  useEffect(() => {
    const espera = setTimeout(() => {
      setQ(busqueda.trim());
      setPagina(1);
    }, 300);
    return () => clearTimeout(espera);
  }, [busqueda]);

  useEffect(() => {
    let vigente = true;
    setCargando(true);
    listarTicketsHistoricos({ q, estado, categoria, prioridad, pagina, por_pagina: POR_PAGINA })
      .then((r) => {
        if (!vigente) return;
        setDatos(r);
        setFiltros((anterior) => anterior ?? r.filtros);
        setError(null);
      })
      .catch((e) => vigente && setError(e.message))
      .finally(() => vigente && setCargando(false));
    return () => {
      vigente = false;
    };
  }, [q, estado, categoria, prioridad, pagina]);

  const hayFiltros = busqueda || estado || categoria || prioridad;
  const limpiar = () => {
    setBusqueda("");
    setQ("");
    setEstado("");
    setCategoria("");
    setPrioridad("");
    setPagina(1);
  };
  const cambiar = (poner) => (e) => {
    poner(e.target.value);
    setPagina(1);
  };

  const total = datos?.total ?? 0;
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA));
  const desde = total === 0 ? 0 : (pagina - 1) * POR_PAGINA + 1;
  const hasta = Math.min(pagina * POR_PAGINA, total);

  return (
    <>
      <div className="mb-4 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <Archive size={20} className="mt-0.5 shrink-0 text-amber-700" />
        <div className="text-sm text-amber-900">
          <strong className="font-semibold">Archivo histórico · solo lectura.</strong> Son los tickets del
          CSV de la herramienta anterior. Se identifican con el prefijo <strong>H-</strong> y no forman parte de
          MinutoDesk: no cuentan en los indicadores, el ranking ni los puntos, y no se pueden editar. Los
          tickets de la plataforma están en el menú <strong>Tickets</strong>.
        </div>
      </div>

      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}

      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-linea bg-white p-4 shadow-sm">
        <div className="w-full min-w-0 lg:w-auto lg:min-w-[220px] lg:flex-1">
          <label className={labelClass}>Buscar</label>
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              className={`${inputClass} pl-9`}
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="ID, descripción, solicitante o quien atendió…"
            />
          </div>
        </div>
        {[
          ["Estado", estado, setEstado, filtros?.estados],
          ["Categoría", categoria, setCategoria, filtros?.categorias],
          ["Prioridad", prioridad, setPrioridad, filtros?.prioridades],
        ].map(([etiqueta, valor, poner, opciones]) => (
          <div key={etiqueta} className="min-w-[140px] flex-1 lg:flex-none">
            <label className={labelClass}>{etiqueta}</label>
            <select className={`${inputClass} lg:w-44`} value={valor} onChange={cambiar(poner)}>
              <option value="">Todas</option>
              {(opciones ?? []).map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </div>
        ))}
        {hayFiltros && (
          <button onClick={limpiar} className="pb-2 text-sm text-acento hover:underline">
            Limpiar filtros
          </button>
        )}
      </div>

      <div className={`overflow-x-auto rounded-xl border border-linea bg-white shadow-sm transition-opacity ${cargando ? "opacity-60" : ""}`}>
        {/* Móvil y tablet: tarjetas; escritorio: tabla completa. */}
        <ul className="divide-y divide-gray-100 lg:hidden">
          {(datos?.items ?? []).map((t) => (
            <li key={t.id}>
              <button
                type="button"
                onClick={() => setAbierto(t.id)}
                className="block w-full px-4 py-3 text-left hover:bg-marfil focus:bg-marfil focus:outline-none"
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <IdHistorico id={t.id_externo} />
                  <PastillaEstado estado={t.estado} />
                </div>
                <div className="line-clamp-2 text-sm text-gray-800">
                  {t.extracto || <span className="text-gray-400">Sin descripción</span>}
                </div>
                <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
                  <span>{fecha(t.creado_en)}</span>
                  {t.categoria && <span>{t.categoria}</span>}
                  <PastillaPrioridad prioridad={t.prioridad} />
                </div>
                {(t.solicitante || t.asignado_a) && (
                  <div className="mt-1 truncate text-xs text-gray-400">
                    {[t.solicitante, t.asignado_a && `Atendió: ${t.asignado_a}`].filter(Boolean).join(" · ")}
                  </div>
                )}
              </button>
            </li>
          ))}
        </ul>
        <table className="hidden w-full min-w-[820px] text-left text-sm lg:table">
          <thead className="bg-marfil text-xs text-gray-500">
            <tr>
              <th className="px-3 py-2.5 font-medium">ID</th>
              <th className="px-3 py-2.5 font-medium">Creado</th>
              <th className="px-3 py-2.5 font-medium">Descripción</th>
              <th className="px-3 py-2.5 font-medium">Categoría</th>
              <th className="px-3 py-2.5 font-medium">Prioridad</th>
              <th className="px-3 py-2.5 font-medium">Estado</th>
              <th className="px-3 py-2.5 font-medium">Atendió</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {(datos?.items ?? []).map((t) => (
              <tr
                key={t.id}
                tabIndex={0}
                onClick={() => setAbierto(t.id)}
                onKeyDown={(e) => e.key === "Enter" && setAbierto(t.id)}
                className="cursor-pointer hover:bg-marfil focus:bg-marfil focus:outline-none"
              >
                <td className="px-3 py-2.5">
                  <IdHistorico id={t.id_externo} />
                </td>
                <td className="whitespace-nowrap px-3 py-2.5 text-gray-600">{fecha(t.creado_en)}</td>
                <td className="px-3 py-2.5 text-gray-700">
                  <div className="w-[260px] max-w-[26vw] min-w-[180px]">
                    <div className="truncate" title={t.extracto ?? ""}>
                      {t.extracto || <span className="text-gray-400">Sin descripción</span>}
                    </div>
                    {t.solicitante && <div className="truncate text-xs text-gray-400">{t.solicitante}</div>}
                  </div>
                </td>
                <td className="whitespace-nowrap px-3 py-2.5 text-gray-600">{t.categoria || "—"}</td>
                <td className="px-3 py-2.5">
                  <PastillaPrioridad prioridad={t.prioridad} />
                </td>
                <td className="px-3 py-2.5">
                  <PastillaEstado estado={t.estado} />
                </td>
                <td className="whitespace-nowrap px-3 py-2.5 text-gray-600">{t.asignado_a || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {datos && datos.items.length === 0 && (
          <p className="p-6 text-center text-sm text-gray-500">
            {datos.total === 0 && !hayFiltros
              ? "Todavía no hay tickets importados. Sube el CSV en la pestaña «Importar CSV»."
              : "Ningún ticket coincide con los filtros."}
          </p>
        )}
        {!datos && !error && (
          <div className="p-6">
            <Spinner size="sm" />
          </div>
        )}
      </div>

      {datos && total > 0 && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-gray-500">
          <span>
            Mostrando {desde}–{hasta} de {total.toLocaleString("es-EC")} tickets importados
          </span>
          <div className="flex items-center gap-2">
            <button
              disabled={pagina <= 1}
              onClick={() => setPagina((p) => p - 1)}
              aria-label="Página anterior"
              className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-gray-700 hover:bg-marfil disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronLeft size={14} /> <span className="hidden sm:inline">Anterior</span>
            </button>
            <span className="whitespace-nowrap">
              Página {pagina} de {paginas}
            </span>
            <button
              disabled={pagina >= paginas}
              onClick={() => setPagina((p) => p + 1)}
              aria-label="Página siguiente"
              className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-gray-700 hover:bg-marfil disabled:cursor-not-allowed disabled:opacity-40"
            >
              <span className="hidden sm:inline">Siguiente</span> <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {abierto !== null && <Detalle id={abierto} onCerrar={() => setAbierto(null)} />}
    </>
  );
}
