import { BarChart3, Table2 } from "lucide-react";
import { useLayoutEffect, useState } from "react";
import {
  AZUL_PISTA,
  GRIS_SIN_DATO,
  INK,
  SERIES,
  escala,
  formatoCompacto,
  formatoNumero,
  hexA,
} from "./tokens";
import { useTooltip } from "./Tooltip";

// Ancho real del contenedor: el gráfico se dibuja en píxeles reales, así los textos
// mantienen su tamaño en tarjetas anchas y angostas (no se escalan con el viewBox).
function useAncho(ref, minimo = 200) {
  const [ancho, setAncho] = useState(560);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const medir = () => setAncho(Math.max(minimo, Math.round(el.getBoundingClientRect().width)));
    medir();
    const observador = new ResizeObserver(medir);
    observador.observe(el);
    return () => observador.disconnect();
  }, [ref, minimo]);
  return ancho;
}

/* ───────────── Tarjeta con vista de tabla (cada gráfico tiene su gemela accesible) ───────────── */

export function Panel({ className = "", relleno = "p-4 sm:p-5", children }) {
  return (
    <div className={`min-w-0 rounded-xl border border-linea bg-white shadow-sm ${relleno} ${className}`}>
      {children}
    </div>
  );
}

export function ChartCard({ titulo, subtitulo, tabla, className = "", children }) {
  const [verTabla, setVerTabla] = useState(false);
  return (
    <Panel className={className}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-noche">{titulo}</h3>
          {subtitulo && <p className="mt-0.5 text-xs text-gray-500">{subtitulo}</p>}
        </div>
        {tabla && (
          <button
            type="button"
            onClick={() => setVerTabla((v) => !v)}
            className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-linea px-2 py-1 text-xs text-gray-500 hover:bg-marfil"
          >
            {verTabla ? <BarChart3 size={13} /> : <Table2 size={13} />}
            {verTabla ? "Ver gráfico" : "Ver tabla"}
          </button>
        )}
      </div>
      {verTabla && tabla ? <TablaDatos columnas={tabla.columnas} filas={tabla.filas} /> : children}
    </Panel>
  );
}

function TablaDatos({ columnas, filas }) {
  return (
    <div className="max-h-64 overflow-auto">
      <table className="w-full text-left text-sm">
        <thead className="sticky top-0 bg-white text-xs text-gray-500">
          <tr>
            {columnas.map((c, i) => (
              <th key={c} className={`border-b border-linea py-1.5 font-medium ${i ? "text-right" : ""}`}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.map((fila, i) => (
            <tr key={i} className="border-b border-gray-100 last:border-0">
              {fila.map((celda, j) => (
                <td key={j} className={`py-1.5 text-gray-700 ${j ? "text-right tabular-nums" : ""}`}>
                  {celda}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SinDatos({ texto = "Todavía no hay datos para mostrar." }) {
  return (
    <div className="flex h-40 items-center justify-center rounded-lg bg-marfil text-sm text-gray-400">
      {texto}
    </div>
  );
}

/* ───────────── KPI: icono con tinte, valor, detalle y minigráfico ───────────── */

export function Sparkline({ valores, color = SERIES[0], ancho = 96, alto = 36 }) {
  if (!valores || valores.length < 2) return null;
  const max = Math.max(...valores, 1);
  const x = (i) => 4 + (i * (ancho - 8)) / (valores.length - 1);
  const y = (v) => alto - 6 - (v / max) * (alto - 14);
  const puntos = valores.map((v, i) => `${x(i)},${y(v)}`);
  const ultimo = valores.length - 1;
  const area = `M${x(0)},${alto - 2} L${puntos.join(" L")} L${x(ultimo)},${alto - 2} Z`;
  return (
    <svg width={ancho} height={alto} viewBox={`0 0 ${ancho} ${alto}`} aria-hidden="true">
      <path d={area} fill={color} opacity="0.1" />
      <polyline
        points={puntos.join(" ")}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={x(ultimo)} cy={y(valores[ultimo])} r="4" fill={color} stroke={INK.surface} strokeWidth="2" />
    </svg>
  );
}

export function StatTile({ icono: Icono, tono = 0, titulo, valor, detalle, tendencia }) {
  const color = SERIES[tono];
  return (
    <Panel relleno="p-4">
      <div className="flex items-start justify-between gap-2">
        <div
          className="flex h-10 w-10 items-center justify-center rounded-xl"
          style={{ background: hexA(color, 0.12), color }}
        >
          {Icono && <Icono size={20} />}
        </div>
        {/* En móvil, con dos tarjetas por fila, el minigráfico no cabe junto al icono. */}
        <div className="hidden min-[420px]:block">
          <Sparkline valores={tendencia} color={color} />
        </div>
      </div>
      <div className="mt-3 text-xs font-medium text-gray-500">{titulo}</div>
      <div className="mt-0.5 break-words text-2xl font-semibold tracking-tight text-noche sm:text-3xl">{valor}</div>
      {detalle && <div className="mt-0.5 text-xs text-gray-400">{detalle}</div>}
    </Panel>
  );
}

/* ───────────── Medidor: relleno con la serie, pista en el paso claro del mismo azul ───────────── */

export function Meter({ valor, meta, color = SERIES[0], pista = AZUL_PISTA, etiquetaMeta }) {
  const pct = Math.max(0, Math.min(100, valor));
  return (
    <div className="relative pt-5">
      {meta != null && (
        <div className="absolute top-0 text-[11px] text-gray-500" style={{ left: `${meta}%`, transform: "translateX(-50%)" }}>
          {etiquetaMeta ?? `Meta ${meta}%`}
        </div>
      )}
      <div className="relative h-2.5 w-full rounded-lg" style={{ background: pista }}>
        <div className="h-full rounded-lg" style={{ width: `${pct}%`, background: color }} />
        {meta != null && (
          <div
            className="absolute -top-1.5 h-5 w-0.5 rounded bg-noche"
            style={{ left: `${meta}%`, transform: "translateX(-50%)" }}
          />
        )}
      </div>
    </div>
  );
}

/* ───────────── Barra apilada horizontal (parte de un todo, hasta ~5 partes) ───────────── */

export function StackedBar({ segmentos, formato = formatoNumero }) {
  const tt = useTooltip();
  const total = segmentos.reduce((s, x) => s + x.valor, 0);
  const visibles = segmentos.filter((s) => s.valor > 0);
  return (
    <div ref={tt.ref} className="relative">
      <div className="flex h-3.5 w-full gap-0.5 overflow-hidden rounded-lg bg-gray-100">
        {total > 0 &&
          visibles.map((s, i) => (
            <div
              key={s.etiqueta}
              tabIndex={0}
              aria-label={`${s.etiqueta}: ${formato(s.valor)}`}
              className="h-full transition-opacity hover:opacity-80 focus:opacity-80 focus:outline-none"
              style={{
                width: `${(s.valor / total) * 100}%`,
                background: s.color,
                borderRadius: `${i === 0 ? 4 : 0}px ${i === visibles.length - 1 ? 4 : 0}px ${i === visibles.length - 1 ? 4 : 0}px ${i === 0 ? 4 : 0}px`,
              }}
              onPointerMove={(e) =>
                tt.mostrar(e, {
                  filas: [
                    { color: s.color, etiqueta: s.etiqueta, valor: `${formato(s.valor)} · ${Math.round((s.valor / total) * 100)}%` },
                  ],
                })
              }
              onPointerLeave={tt.ocultar}
              onFocus={(e) => tt.mostrar(e, { filas: [{ color: s.color, etiqueta: s.etiqueta, valor: formato(s.valor) }] })}
              onBlur={tt.ocultar}
            />
          ))}
      </div>
      <Leyenda items={segmentos} total={total} formato={formato} className="mt-3" />
      {tt.capa}
    </div>
  );
}

export function Leyenda({ items, total, formato = formatoNumero, className = "" }) {
  return (
    <ul className={`flex flex-wrap gap-x-5 gap-y-1.5 text-xs ${className}`}>
      {items.map((s) => (
        <li key={s.etiqueta} className="flex items-center gap-1.5 text-gray-600">
          <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} />
          <span>{s.etiqueta}</span>
          <span className="font-semibold text-noche">{formato(s.valor)}</span>
          {total > 0 && <span className="text-gray-400">({Math.round((s.valor / total) * 100)}%)</span>}
        </li>
      ))}
    </ul>
  );
}

/* ───────────── Anillo (parte de un todo, máximo 6 partes) ───────────── */

export function Donut({ datos, centroValor, centroTitulo }) {
  const tt = useTooltip();
  const [activo, setActivo] = useState(null);
  const total = datos.reduce((s, d) => s + d.valor, 0);
  const R = 60;
  const GROSOR = 15;
  const C = 2 * Math.PI * R;
  const HUECO = 2.5; // separación en el color de la superficie entre partes
  let acumulado = 0;

  return (
    <div className="flex flex-wrap items-center gap-6">
      <div ref={tt.ref} className="relative shrink-0">
        <svg viewBox="0 0 160 160" className="h-40 w-40" role="img" aria-label={`${centroTitulo}: ${centroValor}`}>
          <circle cx="80" cy="80" r={R} fill="none" stroke="#f1f1ee" strokeWidth={GROSOR} />
          {total > 0 &&
            datos.map((d, i) => {
              if (d.valor <= 0) return null;
              const largo = (d.valor / total) * C;
              const dash = Math.max(largo - (datos.filter((x) => x.valor > 0).length > 1 ? HUECO : 0), 0.5);
              const desfase = -acumulado;
              acumulado += largo;
              return (
                <circle
                  key={d.etiqueta}
                  cx="80"
                  cy="80"
                  r={R}
                  fill="none"
                  stroke={d.color}
                  strokeWidth={activo === i ? GROSOR + 3 : GROSOR}
                  strokeDasharray={`${dash} ${C - dash}`}
                  strokeDashoffset={desfase}
                  transform="rotate(-90 80 80)"
                  opacity={activo === null || activo === i ? 1 : 0.5}
                  tabIndex={0}
                  aria-label={`${d.etiqueta}: ${formatoNumero(d.valor)}`}
                  style={{ transition: "stroke-width 120ms, opacity 120ms", outline: "none", cursor: "default" }}
                  onPointerMove={(e) => {
                    setActivo(i);
                    tt.mostrar(e, {
                      filas: [{ color: d.color, etiqueta: d.etiqueta, valor: `${formatoNumero(d.valor)} · ${Math.round((d.valor / total) * 100)}%` }],
                    });
                  }}
                  onPointerLeave={() => {
                    setActivo(null);
                    tt.ocultar();
                  }}
                  onFocus={(e) => {
                    setActivo(i);
                    tt.mostrar(e, { filas: [{ color: d.color, etiqueta: d.etiqueta, valor: formatoNumero(d.valor) }] });
                  }}
                  onBlur={() => {
                    setActivo(null);
                    tt.ocultar();
                  }}
                />
              );
            })}
          <text x="80" y="78" textAnchor="middle" fontSize="26" fontWeight="600" fill={INK.primary}>
            {centroValor}
          </text>
          <text x="80" y="96" textAnchor="middle" fontSize="10" fill={INK.muted}>
            {centroTitulo}
          </text>
        </svg>
        {tt.capa}
      </div>
      <ul className="min-w-[150px] flex-1 space-y-2 text-sm">
        {datos.map((d, i) => (
          <li
            key={d.etiqueta}
            className="flex items-center gap-2"
            onPointerEnter={() => setActivo(i)}
            onPointerLeave={() => setActivo(null)}
          >
            <span className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: d.color }} />
            <span className="flex-1 text-gray-600">{d.etiqueta}</span>
            <span className="font-semibold text-noche">{formatoNumero(d.valor)}</span>
            <span className="w-9 text-right text-xs text-gray-400">
              {total > 0 ? `${Math.round((d.valor / total) * 100)}%` : "—"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ───────────── Barras horizontales (comparar magnitudes de categorías) ───────────── */

export function HBars({ datos, color = SERIES[0], nombreValor = "Tickets" }) {
  const tt = useTooltip();
  const max = Math.max(...datos.map((d) => d.valor), 1);
  const total = datos.reduce((s, d) => s + d.valor, 0);
  return (
    <div ref={tt.ref} className="relative space-y-2.5">
      {datos.map((d) => (
        <div
          key={d.etiqueta}
          tabIndex={0}
          aria-label={`${d.etiqueta}: ${formatoNumero(d.valor)}`}
          className="group -mx-1 flex items-center gap-3 rounded px-1 py-0.5 focus:bg-marfil focus:outline-none hover:bg-marfil"
          onPointerMove={(e) =>
            tt.mostrar(e, {
              titulo: d.etiqueta,
              filas: [{ color, etiqueta: nombreValor, valor: `${formatoNumero(d.valor)} · ${Math.round((d.valor / total) * 100)}%` }],
            })
          }
          onPointerLeave={tt.ocultar}
          onFocus={(e) => tt.mostrar(e, { titulo: d.etiqueta, filas: [{ color, etiqueta: nombreValor, valor: formatoNumero(d.valor) }] })}
          onBlur={tt.ocultar}
        >
          <span className="w-24 shrink-0 truncate text-sm text-gray-600 sm:w-36" title={d.etiqueta}>
            {d.etiqueta}
          </span>
          <div className="flex flex-1 items-center gap-2">
            <div
              className="h-2.5 rounded-r-[4px] transition-opacity group-hover:opacity-80"
              style={{ width: `${(d.valor / max) * 100}%`, minWidth: 3, background: color }}
            />
            <span className="text-sm font-semibold text-noche">{formatoNumero(d.valor)}</span>
          </div>
        </div>
      ))}
      {tt.capa}
    </div>
  );
}

/* ───────────── Columnas (volumen por periodo) ───────────── */

function trazoColumna(x, y, w, h, r) {
  if (h <= 0) return "";
  const rr = Math.min(r, h, w / 2);
  return `M${x},${y + h} V${y + rr} Q${x},${y} ${x + rr},${y} H${x + w - rr} Q${x + w},${y} ${x + w},${y + rr} V${y + h} Z`;
}

export function ColumnChart({ datos, etiquetaX, color = SERIES[0], parcialUltimo = false, nombreValor = "Tickets" }) {
  const tt = useTooltip();
  const [activo, setActivo] = useState(null);
  const W = useAncho(tt.ref);
  const H = 240, ml = 40, mr = 8, mt = 18, mb = 30;
  const iw = W - ml - mr, ih = H - mt - mb;
  const { max, pasos } = escala(Math.max(...datos.map((d) => d.valor), 0));
  const banda = iw / datos.length;
  const ancho = Math.min(24, banda * 0.62);
  const y = (v) => mt + ih - (v / max) * ih;
  const iMax = datos.reduce((m, d, i) => (d.valor > datos[m].valor ? i : m), 0);
  // En gráficos angostos se rotula una de cada N columnas para que las etiquetas no se encimen.
  const pasoEtiqueta = Math.max(1, Math.ceil(40 / banda));

  return (
    <div ref={tt.ref} className="relative">
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="block" role="img" aria-label={`${nombreValor} por periodo`}>
        {pasos.map((p) => (
          <g key={p}>
            <line x1={ml} x2={W - mr} y1={y(p)} y2={y(p)} stroke={p === 0 ? INK.axis : INK.grid} strokeWidth="1" />
            <text x={ml - 7} y={y(p) + 3.5} textAnchor="end" fontSize="10" fill={INK.muted}>
              {formatoCompacto(p)}
            </text>
          </g>
        ))}
        {datos.map((d, i) => {
          const x = ml + banda * i + (banda - ancho) / 2;
          const h = (d.valor / max) * ih;
          const parcial = parcialUltimo && i === datos.length - 1;
          const filaTooltip = {
            titulo: etiquetaX(d.etiqueta) + (parcial ? " · mes incompleto" : ""),
            filas: [{ color, etiqueta: nombreValor, valor: formatoNumero(d.valor) }],
          };
          return (
            <g key={d.etiqueta}>
              <path
                d={trazoColumna(x, y(d.valor), ancho, h, 4)}
                fill={color}
                opacity={parcial ? 0.45 : activo === null || activo === i ? 1 : 0.55}
                style={{ transition: "opacity 120ms" }}
              />
              {i === iMax && (
                <text x={x + ancho / 2} y={y(d.valor) - 6} textAnchor="middle" fontSize="11" fontWeight="600" fill={INK.primary}>
                  {formatoNumero(d.valor)}
                </text>
              )}
              {(i % pasoEtiqueta === 0 || i === datos.length - 1) &&
                (i === datos.length - 1 || datos.length - 1 - i >= pasoEtiqueta) && (
                  <text x={x + ancho / 2} y={H - 10} textAnchor="middle" fontSize="10" fill={INK.muted}>
                    {etiquetaX(d.etiqueta)}
                  </text>
                )}
              <rect
                x={ml + banda * i}
                y={mt}
                width={banda}
                height={ih + mb}
                fill="transparent"
                tabIndex={0}
                aria-label={`${etiquetaX(d.etiqueta)}: ${formatoNumero(d.valor)}`}
                style={{ outline: "none" }}
                onPointerMove={(e) => {
                  setActivo(i);
                  tt.mostrar(e, filaTooltip);
                }}
                onPointerLeave={() => {
                  setActivo(null);
                  tt.ocultar();
                }}
                onFocus={(e) => {
                  setActivo(i);
                  tt.mostrar(e, filaTooltip);
                }}
                onBlur={() => {
                  setActivo(null);
                  tt.ocultar();
                }}
              />
            </g>
          );
        })}
      </svg>
      {tt.capa}
    </div>
  );
}

/* ───────────── Líneas (tendencia; una o varias series en un mismo eje) ───────────── */

export function LineChart({ etiquetas, series, etiquetaX = (x) => x, formatoValor = formatoNumero, yMax, referencia, sinAreaSiVarias = true }) {
  const tt = useTooltip();
  const [activo, setActivo] = useState(null);
  const W = useAncho(tt.ref);
  const H = 240, ml = 40, mr = 20, mt = 18, mb = 30;
  const iw = W - ml - mr, ih = H - mt - mb;
  const n = etiquetas.length;
  const maxDato = Math.max(0, ...series.flatMap((s) => s.valores.filter((v) => v != null)));
  const { max, pasos } = yMax != null ? escala(yMax) : escala(maxDato);
  const x = (i) => ml + (n === 1 ? iw / 2 : (i * iw) / (n - 1));
  const y = (v) => mt + ih - (v / max) * ih;
  // Pocas etiquetas en el eje para que respiren: como máximo 8, y menos si el gráfico es angosto.
  const pasoX = Math.max(1, Math.ceil(n / Math.max(2, Math.min(8, Math.floor(iw / 56)))));

  function trazo(valores) {
    let d = "";
    let abierto = false;
    valores.forEach((v, i) => {
      if (v == null) {
        abierto = false;
        return;
      }
      d += `${abierto ? "L" : "M"}${x(i)},${y(v)} `;
      abierto = true;
    });
    return d.trim();
  }

  function mover(e) {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const i = Math.max(0, Math.min(n - 1, Math.round(((px - ml) / iw) * (n - 1))));
    setActivo(i);
    tt.mostrar(e, {
      titulo: etiquetaX(etiquetas[i]),
      filas: series.map((s) => ({ color: s.color, etiqueta: s.nombre, valor: s.valores[i] == null ? "—" : formatoValor(s.valores[i]) })),
    });
  }

  if (n < 2) return <SinDatos texto="Se necesitan al menos dos periodos para mostrar la tendencia." />;

  return (
    <div>
      <div ref={tt.ref} className="relative">
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="block" role="img" aria-label={series.map((s) => s.nombre).join(", ")}>
          {pasos.map((p) => (
            <g key={p}>
              <line x1={ml} x2={W - mr} y1={y(p)} y2={y(p)} stroke={p === 0 ? INK.axis : INK.grid} strokeWidth="1" />
              <text x={ml - 7} y={y(p) + 3.5} textAnchor="end" fontSize="10" fill={INK.muted}>
                {formatoValor(p)}
              </text>
            </g>
          ))}
          {referencia && (
            <g>
              <line x1={ml} x2={W - mr} y1={y(referencia.valor)} y2={y(referencia.valor)} stroke={INK.secondary} strokeWidth="1" />
              <text x={W - mr} y={y(referencia.valor) - 5} textAnchor="end" fontSize="10" fontWeight="600" fill={INK.secondary}>
                {referencia.etiqueta}
              </text>
            </g>
          )}
          {etiquetas.map((e, i) =>
            (i % pasoX === 0 && n - 1 - i >= pasoX) || i === n - 1 ? (
              <text key={e} x={x(i)} y={H - 10} textAnchor="middle" fontSize="10" fill={INK.muted}>
                {etiquetaX(e)}
              </text>
            ) : null
          )}
          {activo !== null && <line x1={x(activo)} x2={x(activo)} y1={mt} y2={mt + ih} stroke={INK.axis} strokeWidth="1" />}
          {series.map((s) => {
            const idx = s.valores.map((v, i) => (v != null ? i : -1)).filter((i) => i >= 0);
            if (!idx.length) return null;
            const ult = idx[idx.length - 1];
            const area = series.length === 1 || !sinAreaSiVarias;
            return (
              <g key={s.nombre}>
                {area && (
                  <path d={`${trazo(s.valores)} L${x(ult)},${y(0)} L${x(idx[0])},${y(0)} Z`} fill={s.color} opacity="0.1" />
                )}
                <path d={trazo(s.valores)} fill="none" stroke={s.color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
                <circle cx={x(ult)} cy={y(s.valores[ult])} r="4" fill={s.color} stroke={INK.surface} strokeWidth="2" />
                {activo !== null && s.valores[activo] != null && (
                  <circle cx={x(activo)} cy={y(s.valores[activo])} r="4.5" fill={s.color} stroke={INK.surface} strokeWidth="2" />
                )}
                {series.length === 1 && (
                  <text x={x(ult)} y={y(s.valores[ult]) - 10} textAnchor="end" fontSize="11" fontWeight="600" fill={INK.primary}>
                    {formatoValor(s.valores[ult])}
                  </text>
                )}
              </g>
            );
          })}
          <rect
            x={ml}
            y={mt}
            width={iw}
            height={ih + mb}
            fill="transparent"
            onPointerMove={mover}
            onPointerLeave={() => {
              setActivo(null);
              tt.ocultar();
            }}
          />
        </svg>
        {tt.capa}
      </div>
      {series.length > 1 && (
        <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-gray-600">
          {series.map((s) => (
            <li key={s.nombre} className="flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4 rounded" style={{ background: s.color }} />
              {s.nombre}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export { GRIS_SIN_DATO };
