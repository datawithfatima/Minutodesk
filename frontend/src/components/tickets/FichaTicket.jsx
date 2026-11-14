import { Ban, CheckCircle2, CircleDot, Clock3 } from "lucide-react";

/*
 * Piezas visuales de la ficha de un ticket (técnico y usuario).
 * Solo presentan los datos que ya tiene la pantalla; no piden ni cambian nada.
 */

/** Encabezado en grafito con la cuadrícula de plano: número, insignias, acciones y solicitante. */
export function CabeceraTicket({ ticket, etiqueta = "Ficha del ticket", insignias, acciones, children }) {
  return (
    <div className="relative overflow-hidden rounded-t-lg bg-grafito px-5 pb-5 pt-4 text-white sm:px-6">
      <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full">
        <defs>
          <pattern id="trama-ficha" width="24" height="24" patternUnits="userSpaceOnUse">
            <path d="M24 0H0v24" fill="none" stroke="#fff" strokeOpacity=".05" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#trama-ficha)" />
      </svg>
      <span aria-hidden="true" className="franja-obra absolute inset-x-0 bottom-0 h-1" />
      <div className="relative flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-casco">
            {etiqueta} · {new Date(ticket.creado_en).toLocaleDateString()}
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-2">
            <h1 className="text-2xl font-bold text-white sm:text-[28px]">
              Ticket <span className="font-mono text-casco">#{ticket.id}</span>
            </h1>
            {insignias}
          </div>
        </div>
        {acciones && <div className="flex shrink-0 items-center gap-1.5">{acciones}</div>}
      </div>
      {children && <div className="relative mt-4">{children}</div>}
    </div>
  );
}

/** Botón claro para usar sobre la cabecera grafito. */
export function BotonCabecera({ children, className = "", ...props }) {
  return (
    <button
      type="button"
      className={`btn-obra inline-flex h-8 items-center gap-1.5 rounded-md border border-white/15 bg-white/[0.06] px-2.5 text-xs font-medium text-white/85 hover:border-white/30 hover:bg-white/10 hover:text-white ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

const PASOS = [
  { clave: "abierto", etiqueta: "Nuevo", Icono: CircleDot },
  { clave: "en_proceso", etiqueta: "En proceso", Icono: Clock3 },
  { clave: "resuelto", etiqueta: "Resuelto", Icono: CheckCircle2 },
];

/** Ciclo de vida del ticket como etapas de obra: lo hecho, lo actual y lo que falta. */
export function CicloEstado({ estado }) {
  if (estado === "cancelado") {
    return (
      <div className="flex items-center gap-2 rounded-md border border-dashed border-white/20 bg-white/[0.04] px-3 py-2 text-sm text-white/80">
        <Ban size={15} aria-hidden="true" className="text-white/60" />
        Ticket cancelado: la obra se detuvo.
      </div>
    );
  }
  const actual = Math.max(0, PASOS.findIndex((p) => p.clave === estado));
  return (
    <ol className="grid grid-cols-3 gap-2" aria-label="Avance del ticket">
      {PASOS.map(({ clave, etiqueta, Icono }, i) => {
        const hecho = i < actual || (i === actual && estado === "resuelto");
        const enCurso = i === actual && estado !== "resuelto";
        return (
          <li key={clave} className="min-w-0" aria-current={i === actual ? "step" : undefined}>
            <div
              className={`h-1.5 rounded-[2px] ${
                hecho ? "anim-vaciar-x bg-casco" : enCurso ? "franja-obra cinta-avanza" : "bg-white/10"
              }`}
              style={{ animationDelay: `${i * 120}ms` }}
            />
            <div className="mt-2 flex items-center gap-1.5">
              <Icono
                size={14}
                aria-hidden="true"
                className={hecho || enCurso ? "text-casco" : "text-white/35"}
              />
              <span className={`truncate text-xs ${hecho || enCurso ? "font-semibold text-white" : "text-white/45"}`}>
                {etiqueta}
              </span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

/** Pestañas como control segmentado, con icono y un indicador que se desliza. */
export function PestanasTicket({ pestanas, activa, onCambiar }) {
  const indice = Math.max(0, pestanas.findIndex((p) => p.nombre === activa));
  return (
    <div
      role="tablist"
      className="relative mb-4 grid rounded-lg border border-linea bg-gray-100 p-1"
      style={{ gridTemplateColumns: `repeat(${pestanas.length}, minmax(0, 1fr))` }}
    >
      <span
        aria-hidden="true"
        className="absolute inset-y-1 left-1 rounded-md bg-superficie shadow-[0_1px_2px_rgb(27_30_34/0.12)] ring-1 ring-linea transition-transform duration-300 ease-[cubic-bezier(.34,1.4,.64,1)]"
        style={{
          width: `calc((100% - 0.5rem) / ${pestanas.length})`,
          transform: `translateX(${indice * 100}%)`,
        }}
      >
        <span className="absolute inset-x-3 bottom-0 h-0.5 rounded-full bg-acento" />
      </span>
      {pestanas.map(({ nombre, Icono, contador }) => (
        <button
          key={nombre}
          type="button"
          role="tab"
          aria-selected={activa === nombre}
          onClick={() => onCambiar(nombre)}
          className={`relative z-10 inline-flex min-w-0 items-center justify-center gap-1.5 rounded-md px-2 py-2 text-sm font-medium transition-colors duration-150 ${
            activa === nombre ? "text-noche" : "text-gray-500 hover:text-noche"
          }`}
        >
          {Icono && <Icono size={15} aria-hidden="true" className="shrink-0" />}
          <span className="truncate">{nombre}</span>
          {contador != null && (
            <span className="rounded-[3px] bg-gray-200 px-1 font-mono text-[10px] text-gray-600">{contador}</span>
          )}
        </button>
      ))}
    </div>
  );
}

/** Tarjeta de la columna lateral, con cabecera rotulada. */
export function PanelFicha({ icono: Icono, titulo, children, className = "", acento = false }) {
  return (
    <section className={`lamina overflow-hidden rounded-lg border border-linea bg-superficie ${className}`}>
      <header className="flex items-center gap-2 border-b border-linea bg-gray-50 px-4 py-2.5">
        {Icono && (
          <span
            className={`flex h-6 w-6 items-center justify-center rounded-[4px] ${
              acento ? "bg-acento text-white" : "bg-grafito text-casco"
            }`}
          >
            <Icono size={13} aria-hidden="true" />
          </span>
        )}
        <h2 className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-gray-600">{titulo}</h2>
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

/** Fila de la ficha técnica: icono, rótulo y valor. */
export function FilaFicha({ icono: Icono, etiqueta, children }) {
  return (
    <div className="flex items-start gap-3 py-2.5">
      {Icono && (
        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-[4px] bg-gray-100 text-gray-500">
          <Icono size={13} aria-hidden="true" />
        </span>
      )}
      <dt className="mt-1 shrink-0 text-xs text-gray-500">{etiqueta}</dt>
      <dd className="mt-0.5 min-w-0 flex-1 text-right text-sm font-semibold text-noche">{children}</dd>
    </div>
  );
}

/** Barra de confianza del clasificador (0–1), con la marca del umbral si se conoce. */
export function BarraConfianza({ valor, umbral }) {
  const pct = Math.round(valor * 100);
  return (
    <span className="mt-1.5 block">
      <span className="relative block h-1.5 w-full rounded-full bg-gray-100">
        <span
          className={`anim-vaciar-x absolute inset-y-0 left-0 rounded-full ${
            umbral != null && valor < umbral ? "bg-amber-500" : "bg-acento"
          }`}
          style={{ width: `${pct}%` }}
        />
        {umbral != null && (
          <span
            className="absolute -top-1 h-3.5 w-0.5 rounded bg-grafito"
            style={{ left: `${Math.round(umbral * 100)}%` }}
            title={`Umbral ${Math.round(umbral * 100)}%`}
          />
        )}
      </span>
      <span className="mt-1 block font-mono text-[10.5px] font-normal text-gray-500">Confianza {pct}%</span>
    </span>
  );
}
