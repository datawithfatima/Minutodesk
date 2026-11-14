import { Ban, CheckCircle2, CircleDot, Clock3, Columns3, LayoutGrid, Table2 } from "lucide-react";
import { Link } from "react-router-dom";
import { COLOR_PRIORIDAD, GRIS_SIN_DATO, SERIES } from "../charts/tokens";
import EstadoBadge from "../EstadoBadge";
import { PrioridadPastilla } from "./Pastillas";
import { SlaPastilla } from "./TemporizadorSla";

/*
 * Otras formas de ver la bandeja de tickets: un tablero por estado (como el tablero de
 * avance de una obra) y una cuadrícula de tarjetas. Reciben la misma lista ya filtrada.
 */

export const VISTAS_TICKETS = [
  { clave: "tabla", etiqueta: "Tabla", Icono: Table2 },
  { clave: "tablero", etiqueta: "Tablero", Icono: Columns3 },
  { clave: "tarjetas", etiqueta: "Tarjetas", Icono: LayoutGrid },
];

/** Selector de vista como control segmentado, con un indicador que se desliza. */
export function SelectorVista({ vista, onCambiar }) {
  const indice = Math.max(0, VISTAS_TICKETS.findIndex((v) => v.clave === vista));
  return (
    <div
      role="radiogroup"
      aria-label="Forma de ver los tickets"
      className="relative grid grid-cols-3 rounded-lg border border-linea bg-gray-100 p-1"
    >
      <span
        aria-hidden="true"
        className="absolute inset-y-1 left-1 w-[calc((100%-0.5rem)/3)] rounded-md bg-superficie shadow-[0_1px_2px_rgb(27_30_34/0.12)] ring-1 ring-linea transition-transform duration-300 ease-[cubic-bezier(.34,1.4,.64,1)]"
        style={{ transform: `translateX(${indice * 100}%)` }}
      />
      {VISTAS_TICKETS.map(({ clave, etiqueta, Icono }) => (
        <button
          key={clave}
          type="button"
          role="radio"
          aria-checked={vista === clave}
          onClick={() => onCambiar(clave)}
          className={`relative z-10 inline-flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            vista === clave ? "text-noche" : "text-gray-500 hover:text-noche"
          }`}
        >
          <Icono size={15} aria-hidden="true" />
          <span className="hidden sm:inline">{etiqueta}</span>
        </button>
      ))}
    </div>
  );
}

function iniciales(nombre) {
  return (nombre || "?")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();
}

/** «hace 3 días», «hoy»… a partir de la fecha de creación. */
function haceCuanto(fecha) {
  const dias = Math.floor((Date.now() - new Date(fecha).getTime()) / 86_400_000);
  if (dias <= 0) return "hoy";
  if (dias === 1) return "ayer";
  if (dias < 30) return `hace ${dias} días`;
  return new Date(fecha).toLocaleDateString();
}

/** Tarjeta de un ticket: franja de prioridad, número, texto, persona y categoría. */
export function TarjetaTicket({ base, ticket, nombre, indice = 0, conEstado = false, lineas = 2 }) {
  const color = COLOR_PRIORIDAD[ticket.prioridad] ?? GRIS_SIN_DATO;
  return (
    <Link
      to={`${base}/${ticket.id}`}
      className="anim-tarjeta group relative block overflow-hidden rounded-md border border-linea bg-superficie p-3 pl-4 shadow-[0_1px_0_rgb(27_30_34/0.04)] transition-[transform,box-shadow,border-color] duration-200 hover:-translate-y-0.5 hover:border-gray-300 hover:shadow-[0_10px_24px_-14px_rgb(27_30_34/0.45)]"
      style={{ animationDelay: `${Math.min(indice, 12) * 35}ms` }}
    >
      {/* Franja de prioridad: el color de la escala de urgencia */}
      <span aria-hidden="true" className="absolute inset-y-0 left-0 w-1" style={{ background: color }} />
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] font-medium text-acento">#{ticket.id}</span>
        {conEstado ? <EstadoBadge estado={ticket.estado} /> : <PrioridadPastilla prioridad={ticket.prioridad} />}
      </div>
      <p
        className={`mt-1.5 break-words text-sm font-medium leading-snug text-noche group-hover:text-acento ${
          lineas === 3 ? "line-clamp-3" : "line-clamp-2"
        }`}
      >
        {ticket.texto}
      </p>
      <div className="mt-3 flex items-center justify-between gap-2 border-t border-dashed border-linea pt-2.5">
        <span className="flex min-w-0 items-center gap-2">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[4px] bg-grafito text-[10px] font-semibold text-casco">
            {iniciales(nombre)}
          </span>
          <span className="min-w-0">
            <span className="block truncate text-xs font-medium text-gray-700">{nombre || "—"}</span>
            <span className="block truncate text-[11px] text-gray-500">
              {ticket.categoria || ticket.categoria_predicha || "Sin categoría"}
            </span>
          </span>
        </span>
        <span className="flex shrink-0 items-center gap-2">
          <SlaPastilla sla={ticket.sla} />
          <span className="font-mono text-[10.5px] text-gray-500">{haceCuanto(ticket.creado_en)}</span>
        </span>
      </div>
      {conEstado && (
        <div className="mt-2">
          <PrioridadPastilla prioridad={ticket.prioridad} />
        </div>
      )}
    </Link>
  );
}

const COLUMNAS = [
  { estado: "abierto", etiqueta: "Nuevos", Icono: CircleDot, color: SERIES[0] },
  { estado: "en_proceso", etiqueta: "En proceso", Icono: Clock3, color: SERIES[1] },
  { estado: "resuelto", etiqueta: "Resueltos", Icono: CheckCircle2, color: SERIES[2] },
  { estado: "cancelado", etiqueta: "Cancelados", Icono: Ban, color: GRIS_SIN_DATO },
];

/** Tablero por estado: una columna por etapa, con su conteo y su parte del total. */
export function TableroTickets({ base, tickets, nombreDe, soloEstado }) {
  const columnas = soloEstado ? COLUMNAS.filter((c) => c.estado === soloEstado) : COLUMNAS;
  const total = tickets.length;
  return (
    <div className={`grid gap-4 ${columnas.length > 1 ? "md:grid-cols-2 xl:grid-cols-4" : ""}`}>
      {columnas.map(({ estado, etiqueta, Icono, color }, k) => {
        const lista = tickets.filter((t) => t.estado === estado);
        const pct = total ? Math.round((100 * lista.length) / total) : 0;
        return (
          <section
            key={estado}
            className="anim-columna flex min-w-0 flex-col rounded-lg border border-linea bg-gray-50"
            style={{ animationDelay: `${k * 70}ms` }}
            aria-label={`${etiqueta}: ${lista.length}`}
          >
            <header className="border-b border-linea px-3 pb-2.5 pt-3">
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2">
                  <span
                    className="flex h-6 w-6 items-center justify-center rounded-[4px] text-white"
                    style={{ background: color }}
                  >
                    <Icono size={13} aria-hidden="true" />
                  </span>
                  <span className="text-sm font-bold text-noche">{etiqueta}</span>
                </span>
                <span className="rounded-[3px] bg-superficie px-1.5 py-0.5 font-mono text-xs font-medium text-noche ring-1 ring-linea">
                  {lista.length}
                </span>
              </div>
              <div className="mt-2.5 h-1 w-full rounded-full bg-gray-200">
                <div
                  className="anim-vaciar-x h-full rounded-full"
                  style={{ width: `${pct}%`, background: color, animationDelay: `${150 + k * 70}ms` }}
                />
              </div>
            </header>
            <div
              className={`flex-1 space-y-2.5 overflow-y-auto p-2.5 ${
                columnas.length > 1 ? "max-h-[min(70vh,720px)]" : "grid gap-2.5 space-y-0 sm:grid-cols-2 xl:grid-cols-3"
              }`}
            >
              {lista.length === 0 ? (
                <p className="rounded-md border border-dashed border-gray-300 px-3 py-6 text-center text-xs text-gray-500">
                  Sin tickets en esta etapa
                </p>
              ) : (
                lista.map((t, i) => (
                  <TarjetaTicket key={t.id} base={base} ticket={t} nombre={nombreDe(t)} indice={i} />
                ))
              )}
            </div>
          </section>
        );
      })}
    </div>
  );
}

/** Cuadrícula de tarjetas (paginada como la tabla). */
export function CuadriculaTickets({ base, tickets, nombreDe }) {
  return (
    <div className="mb-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {tickets.map((t, i) => (
        <TarjetaTicket key={t.id} base={base} ticket={t} nombre={nombreDe(t)} indice={i} conEstado lineas={3} />
      ))}
    </div>
  );
}
