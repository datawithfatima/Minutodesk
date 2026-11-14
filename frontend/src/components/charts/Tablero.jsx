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
        <span className="mt-0.5 rounded-[3px] bg-grafito px-1.5 py-0.5 font-mono text-[11px] font-medium text-casco">
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
        oscuro ? "bg-grafito text-white shadow-[0_1px_0_rgb(0_0_0/0.2)]" : "lamina border border-linea bg-superficie"
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

/* ───────────── Medidor de obra: un edificio que se levanta piso a piso hasta el valor ─────────────
   10 pisos = 100 %. La meta es una cota de nivel (el símbolo ▽ de los planos de corte) y el
   valor alcanzado es la losa donde llegó la obra. Mantiene la misma interfaz que el medidor anterior. */

export function Medidor({ valor, meta, etiqueta, color = "#c2410c", tamano = 260 }) {
  const v = Math.max(0, Math.min(100, Number(valor) || 0));
  const PISOS = 10;
  const base = 158; // nivel del terreno
  const alto = 140; // altura total del edificio (100 %)
  const x0 = 70;
  const ancho = 116;
  const y = (pct) => base - (pct / 100) * alto;
  const hPiso = alto / PISOS;
  const yValor = y(v);
  const pisosLlenos = Math.floor((v / 100) * PISOS + 1e-9);
  return (
    <svg
      viewBox="0 0 270 172"
      width={tamano}
      className="block h-auto max-w-full overflow-visible"
      role="img"
      aria-label={`${etiqueta ?? "Valor"}: ${valor}%${meta != null ? `, meta ${meta}%` : ""}`}
    >
      {/* Terreno */}
      <path d={`M58 ${base}H254`} stroke="#9b968c" strokeWidth="1.5" />
      <path d={`M58 ${base + 5}H254`} stroke="#c3c2b7" strokeDasharray="2 5" />

      {/* Estructura completa (pisos por construir, en gris) */}
      {Array.from({ length: PISOS }, (_, i) => (
        <rect
          key={i}
          x={x0}
          y={base - (i + 1) * hPiso + 1}
          width={ancho}
          height={hPiso - 2}
          rx="1"
          fill="#efede8"
          stroke="#c3c2b7"
          strokeDasharray={i >= pisosLlenos ? "3 3" : undefined}
          strokeWidth="0.8"
        />
      ))}

      {/* Lo construido: se «vacía» desde la base hasta el valor */}
      <g className="anim-vaciar-y">
        <rect x={x0} y={yValor} width={ancho} height={base - yValor} rx="1" fill={color} />
        {/* losas y ventanas sobre lo construido */}
        {Array.from({ length: Math.ceil((v / 100) * PISOS) }, (_, i) => {
          const yp = base - (i + 1) * hPiso;
          return (
            <g key={i}>
              {i > 0 && <path d={`M${x0} ${base - i * hPiso}H${x0 + ancho}`} stroke="#ffffff" strokeOpacity=".55" />}
              {[0, 1, 2, 3].map((k) => {
                const vy = yp + 4;
                return vy >= yValor ? (
                  <rect key={k} x={x0 + 10 + k * 27} y={vy} width="15" height="6" rx=".5" fill="#ffffff" fillOpacity=".35" />
                ) : null;
              })}
            </g>
          );
        })}
      </g>

      {/* Cota lateral 0–100 % */}
      <g stroke="#9b968c">
        <path d={`M58 ${base}V${y(100)}M54 ${base}H62M54 ${y(100)}H62M56 ${y(50)}H60`} />
      </g>
      {[0, 50, 100].map((m) => (
        <text key={m} x="50" y={y(m) + 3} textAnchor="end" fontSize="9" fill="#6f6b63" fontFamily="IBM Plex Mono, monospace">
          {m}%
        </text>
      ))}

      {/* Nivel alcanzado: triángulo naranja junto a la última losa */}
      <path className="anim-grua-sube" style={{ "--subida": `${base - yValor}px` }} d={`M${x0 - 12} ${yValor - 5}l6 5l-6 5z`} fill={color} />

      {/* Cota de la meta: línea de nivel y símbolo ▽ */}
      {meta != null && (
        <g>
          <path d={`M${x0 - 8} ${y(meta)}H${x0 + ancho + 12}`} stroke="#1b1e22" strokeWidth="1.5" strokeDasharray="5 3" />
          <path
            d={`M${x0 + ancho + 14} ${y(meta) - 8}h10l-5 8z`}
            fill="#f5b800"
            stroke="#1b1e22"
            strokeWidth="1"
          />
          <text
            x={x0 + ancho + 28}
            y={y(meta) + 3}
            fontSize="9.5"
            fontWeight="600"
            fill="#1b1e22"
            fontFamily="IBM Plex Mono, monospace"
          >
            META {meta}%
          </text>
        </g>
      )}

      {/* Grúa torre sobre la última losa: su gancho marca hasta dónde va la obra */}
      <g className="anim-grua-sube" style={{ "--subida": `${base - yValor}px` }}>
        <g transform={`translate(0 ${yValor - base})`}>
          {/* mástil con celosía, punta, pluma y contrapluma con contrapeso */}
          <path d={`M${x0 + ancho - 19} ${base}V${base - 22}M${x0 + ancho - 13} ${base}V${base - 22}`} stroke="#f5b800" strokeWidth="1.4" />
          <path d={`M${x0 + ancho - 19} ${base}L${x0 + ancho - 13} ${base - 7}L${x0 + ancho - 19} ${base - 14}L${x0 + ancho - 13} ${base - 21}`} stroke="#f5b800" strokeWidth=".8" fill="none" />
          <path d={`M${x0 + ancho - 16} ${base - 30}L${x0 + 18} ${base - 22}M${x0 + ancho - 16} ${base - 30}L${x0 + ancho + 6} ${base - 22}M${x0 + ancho - 16} ${base - 30}V${base - 22}`} stroke="#f5b800" strokeWidth=".8" fill="none" />
          <path d={`M${x0 + 18} ${base - 22}H${x0 + ancho + 6}`} stroke="#f5b800" strokeWidth="2" />
          <rect x={x0 + ancho} y={base - 22} width="7" height="5" fill="#9b968c" />
          <path d={`M${x0 + 42} ${base - 22}V${base - 11}`} stroke="#9b968c" strokeWidth=".8" />
          <rect x={x0 + 37} y={base - 11} width="10" height="7" rx="1" fill="#f5b800" />
        </g>
      </g>
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
