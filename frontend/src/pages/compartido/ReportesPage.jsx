import {
  AlertTriangle,
  Ban,
  BarChart3,
  CircleDot,
  CheckCircle2,
  Clock,
  FileSpreadsheet,
  FileText,
  Inbox,
  MessagesSquare,
  Target,
  Ticket,
  TimerReset,
} from "lucide-react";
import { useEffect, useState } from "react";
import { exportarReportes, obtenerClasificador, obtenerResumen, obtenerSatisfaccion } from "../../api";
import { Estrellas } from "../../components/tickets/EncuestaSatisfaccion";
import { obtenerUsuario } from "../../auth";
import Alert from "../../components/ui/Alert";
import Button from "../../components/ui/Button";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";
import {
  ChartCard,
  HBars,
  LineChart,
  Meter,
  Panel,
  SinDatos,
  StackedBar,
} from "../../components/charts/Charts";
import { EncabezadoSeccion, FlujoEtapas, FranjaIndicadores, Medidor } from "../../components/charts/Tablero";
import {
  ESTADO_AVISO,
  ESTADO_OK,
  SERIES,
  GRIS_SIN_DATO,
  formatoNumero,
} from "../../components/charts/tokens";

const META_AUTONOMIA = 30;

function formatearHoras(horas) {
  if (horas == null) return "—";
  if (horas < 1) return "< 1 h";
  if (horas >= 48) return `${(horas / 24).toFixed(1)} d`;
  return `${horas} h`;
}

function Seccion({ numero, titulo, subtitulo }) {
  return <EncabezadoSeccion numero={numero} titulo={titulo} subtitulo={subtitulo} />;
}

function Estado({ icono: Icono, color, texto }) {
  // Los colores de estado nunca van solos: siempre con icono y texto.
  return (
    <div className="mt-2 inline-flex items-center gap-1.5 text-sm text-gray-700">
      <Icono size={16} style={{ color }} />
      {texto}
    </div>
  );
}

/* ───────────── Plataforma: lo que ocurre en MinutoDesk ───────────── */

function Plataforma({ resumen, personal }) {
  const total = resumen.total;
  // La meta (objetivo 2) es sobre consultas de primer nivel; si aún no hay, sobre todas.
  const primerNivel = resumen.pct_primer_nivel != null;
  const pct = primerNivel ? resumen.pct_primer_nivel : resumen.pct_resolucion_autonoma;
  const cumple = pct >= META_AUTONOMIA;
  const pendientes = resumen.abiertos + resumen.en_proceso;

  return (
    <>
      {/* Indicadores principales en una sola franja */}
      <FranjaIndicadores
        items={[
          {
            icono: Ticket,
            titulo: "Tickets",
            valor: formatoNumero(total),
            // Los cancelados también cuentan en el total: sin ellos la suma no cuadra.
            detalle: `${resumen.resueltos} resueltos · ${resumen.cancelados} cancelados`,
          },
          {
            icono: Inbox,
            titulo: "Pendientes",
            valor: formatoNumero(pendientes),
            detalle: `${resumen.abiertos} nuevos · ${resumen.en_proceso} en proceso`,
          },
          {
            icono: Clock,
            titulo: "Tiempo medio de resolución",
            valor: formatearHoras(resumen.tiempo_medio_resolucion_horas),
            detalle: "Días corridos",
          },
          {
            // Conversaciones del chat de Minutito ya terminadas (no las respuestas de la
            // evaluación a los tickets cargados, que van en Datos históricos).
            icono: MessagesSquare,
            titulo: "Conversaciones con Minutito",
            valor: formatoNumero(resumen.conversaciones_minutito),
            detalle: resumen.conversaciones_minutito
              ? `${resumen.conversaciones_resueltas} resueltas sin ticket · ${
                  resumen.conversaciones_minutito - resumen.conversaciones_resueltas
                } pasaron a ticket`
              : "Ninguna terminada aún",
          },
        ]}
      />

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Medidor de autonomía de Minutito */}
        <Panel className="lg:col-span-5">
          <h3 className="flex items-center gap-2 text-sm font-bold text-noche">
            <span aria-hidden="true" className="h-3 w-[3px] shrink-0 rounded-[1px] bg-acento" />
            Resolución autónoma de Minutito{primerNivel ? " · primer nivel" : ""}
          </h3>
          <div className="mt-3 flex flex-col items-center">
            <Medidor
              valor={pct}
              meta={personal ? META_AUTONOMIA : undefined}
              etiqueta="Resolución autónoma de Minutito"
              tamano={300}
            />
            <div className="-mt-1 text-5xl font-bold tabular-nums tracking-tight text-noche [font-variation-settings:'wdth'_112]">
              {pct}%
            </div>
            {total === 0 && !resumen.conversaciones_minutito ? (
              <Estado icono={Target} color={GRIS_SIN_DATO} texto="Aún no hay tickets en la plataforma" />
            ) : personal ? (
              cumple ? (
                <Estado icono={CheckCircle2} color={ESTADO_OK} texto={`Meta de ${META_AUTONOMIA}% alcanzada`} />
              ) : (
                <Estado icono={AlertTriangle} color={ESTADO_AVISO} texto={`Por debajo de la meta de ${META_AUTONOMIA}%`} />
              )
            ) : null}
          </div>
          <div className="mt-4 rounded-md border border-dashed border-linea bg-gray-50 p-3 text-sm text-gray-600">
            {resumen.conversaciones_minutito > 0 ? (
              <>
                <strong className="font-semibold text-noche">{resumen.conversaciones_resueltas}</strong> de{" "}
                <strong className="font-semibold text-noche">
                  {primerNivel ? resumen.conversaciones_primer_nivel : resumen.conversaciones_minutito}
                </strong>{" "}
                {primerNivel ? "consultas de primer nivel, sin ticket" : "consultas, sin ticket"}
                {primerNivel && (
                  <span className="mt-1 block text-xs text-gray-500">
                    Todas las consultas: {resumen.pct_resolucion_autonoma}% ({resumen.conversaciones_resueltas} de{" "}
                    {resumen.conversaciones_minutito})
                  </span>
                )}
              </>
            ) : (
              <>
                <strong className="font-semibold text-noche">{resumen.resueltos_por_minutito}</strong> de{" "}
                <strong className="font-semibold text-noche">{total - resumen.cancelados}</strong> tickets resueltos por
                Minutito
              </>
            )}
          </div>
        </Panel>

        <div className="flex min-w-0 flex-col gap-4 lg:col-span-7">
          {/* Estado de las solicitudes como cronograma por etapas */}
          <ChartCard
            titulo="Tickets por estado"
            tabla={{
              columnas: ["Estado", "Tickets"],
              filas: [
                ["Nuevos", resumen.abiertos],
                ["En proceso", resumen.en_proceso],
                ["Resueltos", resumen.resueltos],
                ["Cancelados", resumen.cancelados],
              ],
            }}
          >
            <FlujoEtapas
              etapas={[
                { etiqueta: "Nuevos", valor: resumen.abiertos, color: SERIES[0], icono: CircleDot },
                { etiqueta: "En proceso", valor: resumen.en_proceso, color: SERIES[1], icono: Clock },
                { etiqueta: "Resueltos", valor: resumen.resueltos, color: SERIES[2], icono: CheckCircle2 },
                { etiqueta: "Cancelados", valor: resumen.cancelados, color: GRIS_SIN_DATO, icono: Ban },
              ]}
            />
          </ChartCard>

          {/* Quién resolvió */}
          <Panel className="flex-1">
            <h3 className="flex items-center gap-2 text-sm font-bold text-noche">
              <span aria-hidden="true" className="h-3 w-[3px] shrink-0 rounded-[1px] bg-acento" />
              Quién resolvió los casos
            </h3>
            <div className="mb-4" />
            {resumen.resueltos_por_minutito + resumen.resueltos_por_tecnico === 0 ? (
              <div className="text-sm text-gray-400">Todavía no hay casos resueltos.</div>
            ) : (
              <StackedBar
                segmentos={[
                  { etiqueta: "Minutito (sin ticket)", valor: resumen.resueltos_por_minutito, color: SERIES[0] },
                  { etiqueta: "Equipo de soporte (tickets)", valor: resumen.resueltos_por_tecnico, color: SERIES[1] },
                ]}
              />
            )}
          </Panel>
        </div>
      </div>

      {resumen.sla && <CumplimientoSla sla={resumen.sla} />}

      <ChartCard
        className="mt-4"
        titulo="Tickets por categoría"
        tabla={{
          columnas: ["Categoría", "Tickets"],
          filas: resumen.por_categoria.map((c) => [c.categoria, c.total]),
        }}
      >
        {resumen.por_categoria.length === 0 ? (
          <SinDatos texto="Todavía no hay tickets." />
        ) : (
          <HBars datos={resumen.por_categoria.map((c) => ({ etiqueta: c.categoria, valor: c.total }))} />
        )}
      </ChartCard>
    </>
  );
}

/* ───────────── Plazo de atención (SLA) ───────────── */

function BarraCumplimiento({ etiqueta, grupo }) {
  const pct = grupo.pct;
  const color = pct == null ? GRIS_SIN_DATO : pct >= 80 ? ESTADO_OK : pct >= 50 ? ESTADO_AVISO : "#d64545";
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 py-1.5">
      <span className="truncate text-sm text-gray-700">{etiqueta}</span>
      <span className="font-mono text-xs tabular-nums text-gray-600">
        {pct == null ? "sin datos" : `${pct}% · ${grupo.cumplidos}/${grupo.total}`}
      </span>
      <div className="col-span-2 h-1.5 overflow-hidden rounded-[2px] bg-gray-100">
        <div className="h-full rounded-[2px]" style={{ width: `${pct ?? 0}%`, background: color }} />
      </div>
    </div>
  );
}

function CumplimientoSla({ sla }) {
  const pct = sla.pct_cumplimiento;
  return (
    <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-12">
      <Panel className="lg:col-span-5">
        <h3 className="flex items-center gap-2 text-sm font-bold text-noche">
          <span aria-hidden="true" className="h-3 w-[3px] shrink-0 rounded-[1px] bg-acento" />
          Cumplimiento del plazo de atención
        </h3>
        <p className="mt-0.5 text-xs text-gray-500">Resueltos a tiempo</p>
        <div className="mt-4 flex items-end gap-3">
          <div className="text-5xl font-bold tabular-nums tracking-tight text-noche [font-variation-settings:'wdth'_112]">
            {pct == null ? "—" : `${pct}%`}
          </div>
          <div className="pb-1.5 text-sm text-gray-600">
            {sla.resueltos_con_plazo === 0
              ? "Aún no hay tickets resueltos con plazo"
              : `${sla.cumplidos} de ${sla.resueltos_con_plazo} a tiempo`}
          </div>
        </div>
        {pct != null &&
          (pct >= 80 ? (
            <Estado icono={CheckCircle2} color={ESTADO_OK} texto="Buen cumplimiento" />
          ) : (
            <Estado icono={AlertTriangle} color={ESTADO_AVISO} texto="Hay plazos que se están pasando" />
          ))}
        <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
          {[
            ["En tiempo", sla.abiertos_en_tiempo, ESTADO_OK],
            ["Por vencer", sla.abiertos_por_vencer, ESTADO_AVISO],
            ["Vencidos", sla.abiertos_vencidos, "#d64545"],
            ["En pausa", sla.abiertos_pausados, GRIS_SIN_DATO],
          ].map(([etiqueta, valor, color]) => (
            <div key={etiqueta} className="rounded-md border border-dashed border-linea bg-gray-50 px-3 py-2">
              <dt className="flex items-center gap-1.5 text-xs text-gray-500">
                <span className="h-1.5 w-1.5 rounded-[1px]" style={{ background: color }} />
                {etiqueta}
              </dt>
              <dd className="font-mono text-lg font-semibold tabular-nums text-noche">{valor}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-2 text-xs text-gray-500">Abiertos ahora</p>
      </Panel>
      <Panel className="lg:col-span-7">
        <h3 className="flex items-center gap-2 text-sm font-bold text-noche">
          <TimerReset size={15} aria-hidden="true" className="text-acento" />
          Cumplimiento por tipo y por prioridad
        </h3>
        <div className="mt-3 grid grid-cols-1 gap-x-8 md:grid-cols-2">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-gray-500">Por tipo</p>
            {sla.por_tipo.map((g) => (
              <BarraCumplimiento key={g.etiqueta} etiqueta={g.etiqueta} grupo={g} />
            ))}
          </div>
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-gray-500">Por prioridad</p>
            {sla.por_prioridad.map((g) => (
              <BarraCumplimiento key={g.etiqueta} etiqueta={g.etiqueta} grupo={g} />
            ))}
          </div>
        </div>
      </Panel>
    </div>
  );
}

/* ───────────── Satisfacción del usuario (encuesta al resolver) ───────────── */

function Satisfaccion() {
  const [s, setS] = useState(null);

  useEffect(() => {
    obtenerSatisfaccion()
      .then(setS)
      .catch(() => setS(null));
  }, []);

  if (!s) return null;
  const sinRespuestas = s.respuestas === 0;

  return (
    <>
      <Seccion
        numero={2}
        titulo="Satisfacción del usuario"
        subtitulo="Encuesta de 1 a 5 estrellas"
      />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Panel className="lg:col-span-5">
          <h3 className="flex items-center gap-2 text-sm font-bold text-noche">
            <span aria-hidden="true" className="h-3 w-[3px] shrink-0 rounded-[1px] bg-acento" />
            Calificación promedio
          </h3>
          <div className="mt-4 flex items-end gap-3">
            <div className="text-5xl font-bold tabular-nums tracking-tight text-noche [font-variation-settings:'wdth'_112]">
              {s.promedio == null ? "—" : s.promedio.toFixed(1)}
            </div>
            <div className="pb-1.5">
              <Estrellas valor={Math.round(s.promedio ?? 0)} tamano={18} />
              <div className="text-sm text-gray-600">
                {sinRespuestas ? "Aún no hay calificaciones" : `de 5 · ${s.respuestas} ${s.respuestas === 1 ? "respuesta" : "respuestas"}`}
              </div>
            </div>
          </div>
          {s.satisfechos_pct != null &&
            (s.satisfechos_pct >= 80 ? (
              <Estado icono={CheckCircle2} color={ESTADO_OK} texto={`${s.satisfechos_pct}% satisfechos (4 o 5 estrellas)`} />
            ) : (
              <Estado icono={AlertTriangle} color={ESTADO_AVISO} texto={`${s.satisfechos_pct}% satisfechos (4 o 5 estrellas)`} />
            ))}
          <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md border border-dashed border-linea bg-gray-50 px-3 py-2">
              <dt className="text-xs text-gray-500">Tasa de respuesta</dt>
              <dd className="font-mono text-lg font-semibold tabular-nums text-noche">
                {s.tasa_respuesta_pct == null ? "—" : `${s.tasa_respuesta_pct}%`}
              </dd>
            </div>
            <div className="rounded-md border border-dashed border-linea bg-gray-50 px-3 py-2">
              <dt className="text-xs text-gray-500">Resueltos que se pueden calificar</dt>
              <dd className="font-mono text-lg font-semibold tabular-nums text-noche">{formatoNumero(s.resueltos_calificables)}</dd>
            </div>
          </dl>
        </Panel>

        <ChartCard
          className="lg:col-span-7"
          titulo="Reparto de calificaciones"
          tabla={{ columnas: ["Estrellas", "Respuestas"], filas: s.reparto.map((r) => [`${r.estrellas} ★`, r.total]) }}
        >
          {sinRespuestas ? (
            <SinDatos texto="Todavía no hay calificaciones." />
          ) : (
            <HBars
              nombreValor="Respuestas"
              datos={s.reparto.map((r) => ({
                etiqueta: `${r.estrellas} ${r.estrellas === 1 ? "estrella" : "estrellas"}`,
                valor: r.total,
              }))}
            />
          )}
        </ChartCard>
      </div>

      {!sinRespuestas && (
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-12">
          <Panel className="lg:col-span-5">
            <h3 className="flex items-center gap-2 text-sm font-bold text-noche">
              <span aria-hidden="true" className="h-3 w-[3px] shrink-0 rounded-[1px] bg-acento" />
              Promedio por técnico
            </h3>
            <ul className="mt-3 divide-y divide-dashed divide-linea">
              {s.por_tecnico.map((t) => (
                <li key={t.tecnico} className="flex items-center justify-between gap-3 py-2">
                  <span className="min-w-0 truncate text-sm text-gray-700">{t.tecnico}</span>
                  <span className="flex shrink-0 items-center gap-2">
                    <Estrellas valor={Math.round(t.promedio)} tamano={13} />
                    <span className="font-mono text-xs tabular-nums text-gray-600">
                      {t.promedio.toFixed(1)} · {t.respuestas}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </Panel>
          <Panel className="lg:col-span-7">
            <h3 className="flex items-center gap-2 text-sm font-bold text-noche">
              <span aria-hidden="true" className="h-3 w-[3px] shrink-0 rounded-[1px] bg-acento" />
              Comentarios recientes
            </h3>
            {s.comentarios.length === 0 ? (
              <p className="mt-3 text-sm text-gray-500">Nadie dejó comentarios todavía, solo estrellas.</p>
            ) : (
              <ul className="mt-3 space-y-3">
                {s.comentarios.map((c) => (
                  <li key={c.ticket_id} className="border-l-2 border-casco pl-3">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                      <Estrellas valor={c.estrellas} tamano={12} />
                      <span className="font-mono text-[11px] text-gray-500">
                        #{c.ticket_id} · {c.autor} · {new Date(c.fecha).toLocaleDateString("es-EC")}
                      </span>
                    </div>
                    <p className="mt-1 text-sm leading-relaxed text-gray-700">{c.comentario}</p>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      )}
    </>
  );
}

/* ───────────── Calidad del clasificador (solo administrador) ───────────── */

function fechaYHora(iso) {
  return iso ? new Date(iso).toLocaleDateString("es-EC") : "—";
}

function Clasificador() {
  const [m, setM] = useState(null);

  useEffect(() => {
    obtenerClasificador()
      .then(setM)
      .catch(() => setM({ disponible: false }));
  }, []);

  if (!m || !m.disponible) return null;
  const cat = m.categoria;
  const meta = Math.round(m.objetivo_precision * 100);
  const pct = (v) => (v != null ? `${(v * 100).toFixed(1)}%` : "—");
  const global = cat.accuracy * 100;
  const enUmbral = cat.precision_en_umbral != null ? cat.precision_en_umbral * 100 : null;

  return (
    <>
      <Seccion
        numero={3}
        titulo="Calidad del clasificador"
        subtitulo={`${formatoNumero(cat.tickets)} tickets · ${m.metodo} · ${fechaYHora(m.entrenado_en)}`}
      />
      {/* Las tres precisiones en una sola lámina, cada una con su medidor */}
      <Panel relleno="p-0" className="overflow-hidden">
        <div className="grid grid-cols-1 md:grid-cols-3">
          {[
            {
              titulo:
                cat.umbral != null
                  ? `Categoría · con confianza ≥ ${Math.round(cat.umbral * 100)}%`
                  : "Categoría · con confianza alta",
              valor: enUmbral ?? 0,
              texto: pct(cat.precision_en_umbral),
              estado:
                enUmbral != null ? (
                  <Estado
                    icono={enUmbral >= meta ? CheckCircle2 : AlertTriangle}
                    color={enUmbral >= meta ? ESTADO_OK : ESTADO_AVISO}
                    texto={`Cubre el ${Math.round(cat.cobertura_en_umbral * 100)}% de los tickets`}
                  />
                ) : (
                  <Estado icono={AlertTriangle} color={ESTADO_AVISO} texto="Ningún umbral alcanza la meta" />
                ),
            },
            {
              // La meta del objetivo 1 se mide con el umbral; sin umbral es solo referencia.
              titulo: "Categoría · sin umbral",
              valor: global,
              texto: pct(cat.accuracy),
              estado: <Estado icono={Target} color={GRIS_SIN_DATO} texto="Todas las predicciones" />,
            },
            {
              titulo: "Tipo · precisión global",
              valor: m.tipo.accuracy * 100,
              texto: pct(m.tipo.accuracy),
              estado: (
                <Estado
                  icono={m.tipo.accuracy * 100 >= meta ? CheckCircle2 : AlertTriangle}
                  color={m.tipo.accuracy * 100 >= meta ? ESTADO_OK : ESTADO_AVISO}
                  texto="Incidencia vs. solicitud"
                />
              ),
            },
          ].map((c, k) => (
            <div
              key={c.titulo}
              className={`flex flex-col items-center p-5 text-center ${
                k > 0 ? "border-t border-dashed border-linea md:border-l md:border-t-0" : ""
              }`}
            >
              <div className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-gray-500">{c.titulo}</div>
              <div className="mt-3">
                <Medidor valor={c.valor} meta={meta} etiqueta={c.titulo} tamano={240} color={SERIES[0]} />
              </div>
              <div className="-mt-1 text-4xl font-bold tabular-nums tracking-tight text-noche [font-variation-settings:'wdth'_112]">
                {c.texto}
              </div>
              {c.estado}
            </div>
          ))}
        </div>
      </Panel>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-12">
      {m.en_uso && (
        <Panel className="lg:col-span-5">
          <h3 className="flex items-center gap-2 text-sm font-bold text-noche">
            <span aria-hidden="true" className="h-3 w-[3px] shrink-0 rounded-[1px] bg-acento" />
            Acierto en uso real
          </h3>
          <p className="mt-0.5 text-xs text-gray-400">Sugerencia del SVM frente a la categoría confirmada</p>
          {m.en_uso.tickets_categoria === 0 ? (
            <p className="mt-3 text-sm text-gray-500">Sin tickets confirmados todavía.</p>
          ) : (
            <div className="mt-4 grid grid-cols-1 gap-6">
              {[
                ...(m.en_uso.acierto_categoria_umbral != null
                  ? [[
                      `Categoría · confianza ≥ ${Math.round(m.en_uso.umbral * 100)}%`,
                      m.en_uso.acierto_categoria_umbral,
                      m.en_uso.tickets_categoria_umbral,
                    ]]
                  : []),
                ["Categoría · todas", m.en_uso.acierto_categoria, m.en_uso.tickets_categoria],
                ["Tipo", m.en_uso.acierto_tipo, m.en_uso.tickets_tipo],
              ].map(([nombre, acierto, n]) => (
                <div key={nombre}>
                  <div className="flex flex-wrap items-baseline justify-between gap-x-2">
                    <span className="text-sm text-gray-600">{nombre}</span>
                    <span className="text-xs text-gray-400">{formatoNumero(n)} tickets confirmados</span>
                  </div>
                  <div className="text-3xl font-semibold tracking-tight text-noche">{pct(acierto)}</div>
                  <Meter valor={(acierto ?? 0) * 100} meta={meta} />
                </div>
              ))}
            </div>
          )}
        </Panel>
      )}

      <ChartCard
        className={m.en_uso ? "lg:col-span-7" : "lg:col-span-12"}
        titulo="Precisión y cobertura según la confianza del modelo"
        subtitulo="Más confianza: más precisión, menos cobertura"
        tabla={{
          columnas: ["Confianza ≥", "Precisión", "Cobertura", "Tickets"],
          filas: cat.por_umbral.map((p) => [`${Math.round(p.umbral * 100)}%`, pct(p.precision), pct(p.cobertura), p.tickets]),
        }}
      >
        <LineChart
          etiquetas={cat.por_umbral.map((p) => p.umbral)}
          etiquetaX={(u) => `${Math.round(u * 100)}%`}
          formatoValor={(v) => `${Math.round(v)}%`}
          yMax={100}
          referencia={{ valor: meta, etiqueta: `Meta ${meta}%` }}
          series={[
            { nombre: "Precisión", color: SERIES[0], valores: cat.por_umbral.map((p) => p.precision * 100) },
            { nombre: "Cobertura", color: SERIES[1], valores: cat.por_umbral.map((p) => p.cobertura * 100) },
          ]}
        />
      </ChartCard>
      </div>
    </>
  );
}

/* ───────────── Exportar (Excel con la hoja de tickets, o PDF) ───────────── */

function BotonesExportar({ onError }) {
  const [exportando, setExportando] = useState(null);

  async function exportar(formato) {
    setExportando(formato);
    onError(null);
    try {
      await exportarReportes(formato);
    } catch (e) {
      onError(e.message);
    } finally {
      setExportando(null);
    }
  }

  const opciones = [
    { formato: "xlsx", texto: "Excel", Icono: FileSpreadsheet, titulo: "Indicadores y una hoja con todos los tickets" },
    { formato: "pdf", texto: "PDF", Icono: FileText, titulo: "Indicadores listos para imprimir o anexar" },
  ];
  return (
    <div className="flex items-center gap-2">
      <span className="hidden font-mono text-[10.5px] uppercase tracking-[0.14em] text-gray-500 sm:inline">Exportar</span>
      {opciones.map(({ formato, texto, Icono, titulo }) => (
        <Button
          key={formato}
          size="sm"
          variant="outlineSecondary"
          title={titulo}
          disabled={exportando !== null}
          onClick={() => exportar(formato)}
        >
          <Icono size={15} aria-hidden="true" className={formato === "xlsx" ? "text-green-700" : "text-acento"} />
          {exportando === formato ? "Preparando…" : texto}
        </Button>
      ))}
    </div>
  );
}

/* ───────────── Página ───────────── */

export default function ReportesPage() {
  const rol = obtenerUsuario().rol;
  const personal = rol !== "usuario";
  const admin = rol === "administrador"; // las métricas del clasificador son solo suyas
  const [resumen, setResumen] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerResumen()
      .then(setResumen)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <PageHeader icon={BarChart3} title="Reportes">
        {personal && <BotonesExportar onError={setError} />}
      </PageHeader>
      {error && <Alert variant="danger">{error}</Alert>}
      {!resumen && !error && <Spinner size="sm" />}

      {resumen && (
        <>
          <Seccion numero={1} titulo="Plataforma" subtitulo={personal ? "Incluye los tickets cargados" : undefined} />
          <Plataforma resumen={resumen} personal={personal} />
        </>
      )}

      {personal && <Satisfaccion />}

      {admin && <Clasificador />}

      <div className="h-6" />
    </>
  );
}
