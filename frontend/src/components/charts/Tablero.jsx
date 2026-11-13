import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Sparkline } from "./Charts";
import { formatoNumero } from "./tokens";

/*
 * Piezas de composición de los tableros (Inicio, Reportes, Datos históricos, Tickets).
 * Solo cambian cómo se presentan las cifras: reciben los mismos valores ya calculados.
 */

/* ───────────── Encabezado de sección numerado, como el índice de un juego de planos ───────────── */

export function EncabezadoSeccion({ numero, titulo, subtitulo, children }) {
  return (
    <div className="mb-4 mt-10 flex flex-wrap items-end justify-between gap-3 first:mt-0">
      <div className="flex min-w-0 items-start gap-3">
        <span className="mt-0.5 rounded-[3px] bg-noche px-1.5 py-0.5 font-mono text-[11px] font-medium text-casco">
          {String(numero).padStart(2, "0")}
        </span>
        <div className="min-w-0">
          <h2 className="text-lg font-bold leading-tight text-noche">{titulo}</h2>
          {subtitulo && <p className="mt-0.5 max-w-3xl text-sm text-gray-500">{subtitulo}</p>}
        </div>
      </div>
      {children}
    </div>
  );
}

/* ───────────── Franja de indicadores: una sola banda con celdas separadas por cotas ───────────── */

function CeldaIndicador({ icono: Icono, titulo, valor, detalle, tendencia, to, oscuro, indice }) {
  const contenido = (
    <>
      <div className="flex items-center justify-between gap-2">
        <span
          className={`flex items-center gap-1.5 font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] ${
            oscuro ? "text-noche-300" : "text-gray-500"
          }`}
        >
          {Icono && <Icono size={13} aria-hidden="true" className={oscuro ? "text-casco" : "text-acento"} />}
          {titulo}
        </span>
        {to && (
          <ChevronRight
            size={15}
            aria-hidden="true"
            className={`shrink-0 transition-transform duration-200 group-hover:translate-x-0.5 ${
              oscuro ? "text-noche-300" : "text-gray-400"
            }`}
          />
        )}
      </div>
      <div className="mt-2 flex items-end justify-between gap-3">
        <span
          className={`anim-cifra block break-words text-[28px] font-bold leading-none tabular-nums [font-variation-settings:'wdth'_112] sm:text-[34px] ${
            oscuro ? "text-white" : "text-noche"
          }`}
          style={{ animationDelay: `${120 + indice * 70}ms` }}
        >
          {valor}
        </span>
        {tendencia && (
          <span className="hidden shrink-0 min-[460px]:block">
            <Sparkline valores={tendencia} color={oscuro ? "#f5b800" : undefined} ancho={78} alto={30} />
          </span>
        )}
      </div>
      {detalle && <div className={`mt-1.5 text-xs ${oscuro ? "text-white/60" : "text-gray-500"}`}>{detalle}</div>}
    </>
  );
  const clase = `group relative block min-w-0 p-4 sm:p-5 ${
    to ? (oscuro ? "transition-colors hover:bg-white/[0.04]" : "transition-colors hover:bg-gray-50") : ""
  }`;
  return to ? (
    <Link to={to} className={clase}>
      {contenido}
    </Link>
  ) : (
    <div className={clase}>{contenido}</div>
  );
}

export function FranjaIndicadores({ items, oscuro = true, className = "" }) {
  return (
    <div
      className={`relative overflow-hidden rounded-lg ${
        oscuro ? "bg-noche text-white shadow-[0_1px_0_rgb(0_0_0/0.2)]" : "lamina border border-linea bg-white"
      } ${className}`}
    >
      {oscuro && (
        <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full">
          <defs>
            <pattern id="trama-franja" width="24" height="24" patternUnits="userSpaceOnUse">
              <path d="M24 0H0v24" fill="none" stroke="#fff" strokeOpacity=".04" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#trama-franja)" />
        </svg>
      )}
      <div className="relative grid grid-cols-2 lg:grid-cols-4">
        {items.map((item, i) => (
          <div
            key={item.titulo}
            className={`min-w-0 border-dashed ${oscuro ? "border-white/15" : "border-linea"} ${i > 0 ? "lg:border-l" : ""} ${
              i % 2 === 1 ? "border-l" : ""
            } ${i < 2 ? "max-lg:border-b" : ""}`}
          >
            <CeldaIndicador {...item} oscuro={oscuro} indice={i} />
          </div>
        ))}
      </div>
      <span aria-hidden="true" className={`franja-obra absolute inset-x-0 bottom-0 h-1 ${oscuro ? "" : "opacity-80"}`} />
    </div>
  );
}

/* ───────────── Medidor semicircular, como el manómetro de una máquina de obra ───────────── */

export function Medidor({ valor, meta, etiqueta, color = "#c2410c", tamano = 260 }) {
  const v = Math.max(0, Math.min(100, Number(valor) || 0));
  const R = 100;
  const cx = 120;
  const cy = 118;
  const punto = (pct, r = R) => {
    const a = Math.PI * (1 - pct / 100);
    return [cx + r * Math.cos(a), cy - r * Math.sin(a)];
  };
  const arco = `M${cx - R} ${cy} A${R} ${R} 0 0 1 ${cx + R} ${cy}`;
  const marcas = Array.from({ length: 21 }, (_, i) => i * 5);
  const anguloAguja = -90 + (v / 100) * 180;
  return (
    <svg
      viewBox="0 0 240 142"
      width={tamano}
      className="block h-auto max-w-full overflow-visible"
      role="img"
      aria-label={`${etiqueta ?? "Valor"}: ${valor}%${meta != null ? `, meta ${meta}%` : ""}`}
    >
      <path d={arco} fill="none" stroke="#efede8" strokeWidth="16" />
      <path
        d={arco}
        fill="none"
        stroke={color}
        strokeWidth="16"
        pathLength={100}
        strokeDasharray={`${v} 100`}
        className="anim-medidor"
        style={{ "--valor": v }}
      />
      {marcas.map((m) => {
        const [x1, y1] = punto(m, R - 13);
        const [x2, y2] = punto(m, m % 25 === 0 ? R - 22 : R - 17);
        return <line key={m} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#9b968c" strokeWidth={m % 25 === 0 ? 1.4 : 0.8} />;
      })}
      {[0, 100].map((m) => {
        const [x] = punto(m, R);
        return (
          <text key={m} x={x} y={cy + 16} textAnchor="middle" fontSize="9" fill="#6f6b63" fontFamily="IBM Plex Mono, monospace">
            {m}%
          </text>
        );
      })}
      {meta != null &&
        (() => {
          const [x1, y1] = punto(meta, R + 12);
          const [x2, y2] = punto(meta, R - 10);
          const [tx, ty] = punto(meta, R + 22);
          return (
            <g>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#1b1e22" strokeWidth="2.5" />
              <text x={tx} y={ty} textAnchor="middle" fontSize="9" fontWeight="600" fill="#1b1e22" fontFamily="IBM Plex Mono, monospace">
                META {meta}%
              </text>
            </g>
          );
        })()}
      <g className="anim-aguja" style={{ "--angulo": `${anguloAguja}deg`, transformOrigin: `${cx}px ${cy}px` }}>
        <path d={`M${cx - 3.5} ${cy} L${cx} ${cy - R + 26} L${cx + 3.5} ${cy} Z`} fill="#1b1e22" />
      </g>
      <circle cx={cx} cy={cy} r="8" fill="#1b1e22" />
      <circle cx={cx} cy={cy} r="3" fill="#f5b800" />
    </svg>
  );
}

/* ───────────── Flujo por etapas: el avance de las solicitudes como un cronograma de obra ───────────── */

export function FlujoEtapas({ etapas, total }) {
  const suma = total ?? etapas.reduce((s, e) => s + e.valor, 0);
  const pct = (v) => (suma > 0 ? Math.round((100 * v) / suma) : 0);
  return (
    <div>
      {/* Barra de avance total, por etapas */}
      <div className="anim-vaciar-x flex h-3 w-full gap-[3px] overflow-hidden rounded-[3px] bg-gray-100">
        {suma > 0 &&
          etapas
            .filter((e) => e.valor > 0)
            .map((e) => (
              <div
                key={e.etiqueta}
                title={`${e.etiqueta}: ${formatoNumero(e.valor)}`}
                className="h-full first:rounded-l-[3px] last:rounded-r-[3px]"
                style={{ width: `${(e.valor / suma) * 100}%`, background: e.color }}
              />
            ))}
      </div>

      <ol className="mt-5 grid grid-cols-2 gap-x-4 gap-y-5 sm:grid-cols-4 sm:gap-0">
        {etapas.map((e, i) => {
          const Icono = e.icono;
          return (
            <li key={e.etiqueta} className="relative min-w-0 sm:px-4 sm:first:pl-0 sm:[&:not(:first-child)]:border-l sm:[&:not(:first-child)]:border-dashed sm:[&:not(:first-child)]:border-linea">
              <div className="flex items-center gap-2">
                <span
                  className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[4px] text-white"
                  style={{ background: e.color }}
                >
                  {Icono ? <Icono size={13} aria-hidden="true" /> : <span className="font-mono text-[10px]">{i + 1}</span>}
                </span>
                <span className="truncate text-sm font-semibold text-noche">{e.etiqueta}</span>
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span
                  className="anim-cifra text-3xl font-bold tabular-nums text-noche [font-variation-settings:'wdth'_112]"
                  style={{ animationDelay: `${150 + i * 80}ms` }}
                >
                  {formatoNumero(e.valor)}
                </span>
                <span className="font-mono text-xs text-gray-500">{suma > 0 ? `${pct(e.valor)}%` : "—"}</span>
              </div>
              <div className="mt-2 h-1 w-full rounded-full bg-gray-100">
                <div
                  className="anim-vaciar-x h-full rounded-full"
                  style={{ width: `${pct(e.valor)}%`, background: e.color, animationDelay: `${200 + i * 80}ms` }}
                />
              </div>
              {e.nota && <p className="mt-1.5 text-xs text-gray-500">{e.nota}</p>}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
