import { Archive, Bot, FlaskConical, Timer, BarChart3, Ban, CheckCircle2, Database, Gauge, Ticket } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { obtenerHistorico } from "../../api";
import Alert from "../../components/ui/Alert";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";
import {
  ChartCard,
  ColumnChart,
  Donut,
  HBars,
  LineChart,
  SinDatos,
  StackedBar,
  StatTile,
} from "../../components/charts/Charts";
import {
  COLOR_ESTADO_HISTORICO,
  COLOR_PRIORIDAD,
  SERIES,
  etiquetaMes,
  formatoNumero,
} from "../../components/charts/tokens";
import TicketsImportados from "./TicketsImportados";
import EvaluacionMinutito from "./EvaluacionMinutito";
import PruebaControlada from "./PruebaControlada";
import SimulacionTiempos from "./SimulacionTiempos";

function fechaCorta(iso) {
  return iso ? new Date(iso).toLocaleDateString("es-EC") : "—";
}

/* ───────────── Histórico importado desde el CSV mensual ───────────── */

const ORDEN_ESTADO = ["Completado", "En Curso", "Cancelado", "Nuevo"];
const ORDEN_PRIORIDAD = ["Baja", "Normal", "Alta", "Crítica", "Sin prioridad"];

function esMesIncompleto(h) {
  if (!h.hasta || !h.por_mes.length) return false;
  const fin = new Date(h.hasta);
  const clave = `${fin.getFullYear()}-${String(fin.getMonth() + 1).padStart(2, "0")}`;
  const diasDelMes = new Date(fin.getFullYear(), fin.getMonth() + 1, 0).getDate();
  return h.por_mes[h.por_mes.length - 1].etiqueta === clave && fin.getDate() < diasDelMes;
}

function Historico() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerHistorico()
      .then(setDatos)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <Alert variant="danger">{error}</Alert>;
  if (!datos) return <Spinner size="sm" />;
  if (datos.total === 0) {
    return <SinDatos texto="Todavía no se importó ningún histórico de tickets." />;
  }

  const estados = ORDEN_ESTADO.map((e) => ({
    etiqueta: e,
    valor: datos.por_estado.find((x) => x.etiqueta === e)?.total ?? 0,
    color: COLOR_ESTADO_HISTORICO[e],
  }));
  const prioridades = ORDEN_PRIORIDAD.map((p) => ({
    etiqueta: p,
    valor: datos.por_prioridad.find((x) => x.etiqueta === p)?.total ?? 0,
    color: COLOR_PRIORIDAD[p],
  }));
  const pctCompletados = Math.round((100 * datos.completados) / datos.total);
  const pctCancelados = Math.round((100 * datos.cancelados) / datos.total);
  const diasPorMes = datos.resolucion_por_mes.map((p) => p.valor);

  return (
    <>
      <p className="-mt-2 mb-3 text-sm text-gray-500">
        Tickets del export mensual, del {fechaCorta(datos.desde)} al {fechaCorta(datos.hasta)}. Última actualización:{" "}
        {fechaCorta(datos.ultima_importacion)}.
      </p>

      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <StatTile
          icono={Ticket}
          tono={0}
          titulo="Tickets históricos"
          valor={formatoNumero(datos.total)}
          detalle="Importados del CSV"
          tendencia={datos.por_mes.map((m) => m.total)}
        />
        <StatTile
          icono={CheckCircle2}
          tono={2}
          titulo="Completados"
          valor={`${pctCompletados}%`}
          detalle={`${formatoNumero(datos.completados)} de ${formatoNumero(datos.total)}`}
        />
        <StatTile
          icono={Gauge}
          tono={6}
          titulo="Tiempo medio de resolución"
          valor={datos.dias_medio_resolucion != null ? `${datos.dias_medio_resolucion} d` : "—"}
          detalle="Días entre creación y solución"
          tendencia={diasPorMes.some((v) => v != null) ? diasPorMes.map((v) => v ?? 0) : undefined}
        />
        <StatTile
          icono={Ban}
          tono={1}
          titulo="Cancelados"
          valor={formatoNumero(datos.cancelados)}
          detalle={`${pctCancelados}% del total`}
        />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ChartCard
          className="lg:col-span-2"
          titulo="Tickets por mes"
          subtitulo="Cuántas solicitudes se crearon cada mes"
          tabla={{ columnas: ["Mes", "Tickets"], filas: datos.por_mes.map((m) => [etiquetaMes(m.etiqueta), m.total]) }}
        >
          <ColumnChart
            datos={datos.por_mes.map((m) => ({ etiqueta: m.etiqueta, valor: m.total }))}
            etiquetaX={etiquetaMes}
            parcialUltimo={esMesIncompleto(datos)}
          />
          {esMesIncompleto(datos) && (
            <p className="mt-1 text-xs text-gray-400">El último mes está incompleto (los datos llegan hasta el {fechaCorta(datos.hasta)}).</p>
          )}
        </ChartCard>

        <ChartCard
          titulo="Tickets por estado"
          subtitulo="Situación de todo el histórico"
          tabla={{ columnas: ["Estado", "Tickets"], filas: estados.map((e) => [e.etiqueta, e.valor]) }}
        >
          <Donut datos={estados} centroValor={formatoNumero(datos.total)} centroTitulo="tickets" />
        </ChartCard>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartCard
          titulo="Tickets por categoría"
          subtitulo="Las 8 categorías con más solicitudes"
          tabla={{ columnas: ["Categoría", "Tickets"], filas: datos.por_categoria.map((c) => [c.etiqueta, c.total]) }}
        >
          <HBars datos={datos.por_categoria.map((c) => ({ etiqueta: c.etiqueta, valor: c.total }))} />
        </ChartCard>

        <ChartCard
          titulo="Tiempo medio de resolución"
          subtitulo="Días en resolver los tickets creados cada mes"
          tabla={{
            columnas: ["Mes", "Días"],
            filas: datos.resolucion_por_mes.map((p) => [etiquetaMes(p.etiqueta), p.valor ?? "—"]),
          }}
        >
          <LineChart
            etiquetas={datos.resolucion_por_mes.map((p) => p.etiqueta)}
            etiquetaX={etiquetaMes}
            formatoValor={(v) => `${formatoNumero(v)} d`}
            series={[{ nombre: "Días de resolución", color: SERIES[2], valores: diasPorMes }]}
          />
        </ChartCard>
      </div>

      <ChartCard
        className="mt-4"
        titulo="Tickets por prioridad"
        subtitulo="De menor a mayor urgencia"
        tabla={{ columnas: ["Prioridad", "Tickets"], filas: prioridades.map((p) => [p.etiqueta, p.valor]) }}
      >
        <StackedBar segmentos={prioridades} />
      </ChartCard>
    </>
  );
}

/* ───────────── Página: análisis del histórico (solo administrador) ───────────── */

const VISTAS = [
  { clave: "analisis", etiqueta: "Análisis", icono: BarChart3 },
  { clave: "tickets", etiqueta: "Tickets importados", icono: Archive },
  { clave: "minutito", etiqueta: "Evaluación de Minutito", icono: Bot },
  { clave: "prueba", etiqueta: "Prueba controlada", icono: FlaskConical },
  { clave: "tiempos", etiqueta: "Simulación de tiempos", icono: Timer },
];

export default function DatosHistoricosPage() {
  const [params, setParams] = useSearchParams();
  const pedida = params.get("vista");
  const vista = VISTAS.some((v) => v.clave === pedida) ? pedida : "analisis";

  return (
    <>
      <PageHeader
        icon={Database}
        title="Datos históricos"
      />

      <div role="tablist" className="mb-5 flex gap-1 overflow-x-auto border-b border-linea">
        {VISTAS.map(({ clave, etiqueta, icono: Icono }) => {
          const activa = vista === clave;
          return (
            <button
              key={clave}
              role="tab"
              aria-selected={activa}
              onClick={() => setParams(clave === "analisis" ? {} : { vista: clave })}
              className={`-mb-px inline-flex shrink-0 items-center gap-2 whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition-colors sm:px-4 ${
                activa
                  ? "border-noche text-noche"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              <Icono size={16} />
              {etiqueta}
            </button>
          );
        })}
      </div>

      {vista === "analisis" && <Historico />}
      {vista === "tickets" && <TicketsImportados />}
      {vista === "minutito" && <EvaluacionMinutito />}
      {vista === "prueba" && <PruebaControlada />}
      {vista === "tiempos" && <SimulacionTiempos />}
    </>
  );
}
