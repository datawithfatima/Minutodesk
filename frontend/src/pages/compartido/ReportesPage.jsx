import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock,
  Inbox,
  MessagesSquare,
  Target,
  Ticket,
} from "lucide-react";
import { useEffect, useState } from "react";
import { obtenerClasificador, obtenerResumen } from "../../api";
import { obtenerUsuario } from "../../auth";
import Alert from "../../components/ui/Alert";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";
import {
  ChartCard,
  Donut,
  HBars,
  LineChart,
  Meter,
  Panel,
  SinDatos,
  StackedBar,
  StatTile,
} from "../../components/charts/Charts";
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

function Seccion({ titulo, subtitulo }) {
  return (
    <div className="mb-3 mt-9 first:mt-0">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500">{titulo}</h2>
      {subtitulo && <p className="mt-0.5 text-sm text-gray-500">{subtitulo}</p>}
    </div>
  );
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
  const pct = resumen.pct_resolucion_autonoma;
  const cumple = pct >= META_AUTONOMIA;
  const pendientes = resumen.abiertos + resumen.en_proceso;

  return (
    <>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel className="lg:col-span-2">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-sm font-medium text-gray-500">Resolución autónoma de Minutito</div>
              <div className="mt-1 text-5xl font-semibold tracking-tight text-noche sm:text-6xl">{pct}%</div>
              {total === 0 ? (
                <Estado icono={Target} color={GRIS_SIN_DATO} texto="Aún no hay tickets en la plataforma" />
              ) : personal ? (
                cumple ? (
                  <Estado icono={CheckCircle2} color={ESTADO_OK} texto={`Meta de ${META_AUTONOMIA}% alcanzada`} />
                ) : (
                  <Estado icono={AlertTriangle} color={ESTADO_AVISO} texto={`Por debajo de la meta de ${META_AUTONOMIA}%`} />
                )
              ) : null}
            </div>
            <div className="text-sm text-gray-500 sm:max-w-[220px]">
              <strong className="font-semibold text-noche">{resumen.resueltos_por_minutito}</strong> de{" "}
              <strong className="font-semibold text-noche">{total - resumen.cancelados}</strong> tickets los resolvió
              Minutito y el usuario lo confirmó{resumen.cancelados > 0 ? " (sin contar los cancelados)" : ""}.
            </div>
          </div>

          <div className="mt-4">
            <Meter valor={pct} meta={personal ? META_AUTONOMIA : undefined} color={SERIES[0]} />
          </div>

          <div className="mt-5 border-t border-gray-100 pt-4">
            <div className="mb-2 text-xs font-medium text-gray-500">Quién resolvió los tickets cerrados</div>
            {resumen.resueltos === 0 ? (
              <div className="text-sm text-gray-400">Todavía no hay tickets resueltos.</div>
            ) : (
              <StackedBar
                segmentos={[
                  { etiqueta: "Minutito", valor: resumen.resueltos_por_minutito, color: SERIES[0] },
                  { etiqueta: "Equipo de soporte", valor: resumen.resueltos_por_tecnico, color: SERIES[1] },
                ]}
              />
            )}
          </div>
        </Panel>

        <ChartCard
          titulo="Tickets por estado"
          subtitulo="Cómo van las solicitudes ahora"
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
          <Donut
            centroValor={formatoNumero(total)}
            centroTitulo="tickets"
            datos={[
              { etiqueta: "Nuevos", valor: resumen.abiertos, color: SERIES[0] },
              { etiqueta: "En proceso", valor: resumen.en_proceso, color: SERIES[1] },
              { etiqueta: "Resueltos", valor: resumen.resueltos, color: SERIES[2] },
              { etiqueta: "Cancelados", valor: resumen.cancelados, color: GRIS_SIN_DATO },
            ]}
          />
        </ChartCard>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <StatTile
          icono={Ticket}
          tono={0}
          titulo="Tickets"
          valor={formatoNumero(total)}
          detalle={`${resumen.resueltos} resueltos`}
          tendencia={resumen.ultimos_dias.map((d) => d.total)}
        />
        <StatTile
          icono={Inbox}
          tono={1}
          titulo="Pendientes"
          valor={formatoNumero(pendientes)}
          detalle={`${resumen.en_proceso} en proceso`}
        />
        <StatTile
          icono={Clock}
          tono={2}
          titulo="Tiempo medio de resolución"
          valor={formatearHoras(resumen.tiempo_medio_resolucion_horas)}
          detalle="Tickets resueltos"
        />
        <StatTile
          icono={MessagesSquare}
          tono={6}
          titulo="Conversaciones con Minutito"
          valor={formatoNumero(resumen.con_minutito)}
          detalle={total ? `${Math.round((100 * resumen.con_minutito) / total)}% de los tickets` : "Sin tickets"}
        />
      </div>

      <ChartCard
        className="mt-4"
        titulo="Tickets por categoría"
        subtitulo="Categoría que predijo el clasificador"
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
        titulo="Calidad del clasificador"
        subtitulo={`Medida con ${m.metodo} sobre ${formatoNumero(cat.tickets)} tickets: cada ticket se predice sin haberlo visto al entrenar. Entrenado el ${fechaYHora(m.entrenado_en)}.`}
      />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel>
          <div className="text-sm font-medium text-gray-500">Categoría · precisión global</div>
          <div className="mt-1 text-4xl font-semibold tracking-tight text-noche">{pct(cat.accuracy)}</div>
          <Estado
            icono={global >= meta ? CheckCircle2 : AlertTriangle}
            color={global >= meta ? ESTADO_OK : ESTADO_AVISO}
            texto={global >= meta ? `Meta de ${meta}% alcanzada` : `Por debajo de la meta de ${meta}%`}
          />
          <div className="mt-3">
            <Meter valor={global} meta={meta} />
          </div>
        </Panel>

        <Panel>
          <div className="text-sm font-medium text-gray-500">
            {cat.umbral != null ? `Categoría · con confianza ≥ ${Math.round(cat.umbral * 100)}%` : "Categoría · con confianza alta"}
          </div>
          <div className="mt-1 text-4xl font-semibold tracking-tight text-noche">{pct(cat.precision_en_umbral)}</div>
          {enUmbral != null ? (
            <Estado
              icono={enUmbral >= meta ? CheckCircle2 : AlertTriangle}
              color={enUmbral >= meta ? ESTADO_OK : ESTADO_AVISO}
              texto={`Cubre el ${Math.round(cat.cobertura_en_umbral * 100)}% de los tickets`}
            />
          ) : (
            <Estado icono={AlertTriangle} color={ESTADO_AVISO} texto="Ningún umbral alcanza la meta" />
          )}
          <div className="mt-3">
            <Meter valor={enUmbral ?? 0} meta={meta} />
          </div>
        </Panel>

        <Panel>
          <div className="text-sm font-medium text-gray-500">Tipo · precisión global</div>
          <div className="mt-1 text-4xl font-semibold tracking-tight text-noche">{pct(m.tipo.accuracy)}</div>
          <Estado
            icono={m.tipo.accuracy * 100 >= meta ? CheckCircle2 : AlertTriangle}
            color={m.tipo.accuracy * 100 >= meta ? ESTADO_OK : ESTADO_AVISO}
            texto="Incidencia vs. solicitud"
          />
          <div className="mt-3">
            <Meter valor={m.tipo.accuracy * 100} meta={meta} />
          </div>
        </Panel>
      </div>

      {m.en_uso && (
        <Panel className="mt-4">
          <div className="text-sm font-medium text-gray-500">Acierto en uso real</div>
          <p className="mt-0.5 text-xs text-gray-400">
            Compara lo que sugirió el SVM con lo que eligió la persona al crear el ticket o corrigió el técnico.
          </p>
          {m.en_uso.tickets_categoria === 0 ? (
            <p className="mt-3 text-sm text-gray-500">
              Todavía no hay tickets creados con la categoría confirmada. Aparecerán aquí cuando los usuarios usen
              «Crear ticket».
            </p>
          ) : (
            <div className="mt-3 grid grid-cols-1 gap-6 sm:grid-cols-2">
              {[
                ["Categoría", m.en_uso.acierto_categoria, m.en_uso.tickets_categoria],
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
        className="mt-4"
        titulo="Precisión y cobertura según la confianza del modelo"
        subtitulo="Al exigir más confianza el modelo acierta más, pero responde menos tickets."
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
    </>
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
      <PageHeader
        icon={BarChart3}
        title="Reportes"
        subtitle={
          personal
            ? "Indicadores de los tickets del sistema."
            : "Resumen de tus propios tickets."
        }
      />
      {error && <Alert variant="danger">{error}</Alert>}
      {!resumen && !error && <Spinner size="sm" />}

      {resumen && (
        <>
          <Seccion titulo="Plataforma" subtitulo={personal ? "Tickets creados en MinutoDesk" : undefined} />
          <Plataforma resumen={resumen} personal={personal} />
        </>
      )}

      {admin && <Clasificador />}

      <div className="h-6" />
    </>
  );
}
