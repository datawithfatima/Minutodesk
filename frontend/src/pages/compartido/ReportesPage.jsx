import { BarChart3 } from "lucide-react";
import { useEffect, useState } from "react";
import { obtenerHistorico, obtenerResumen } from "../../api";
import { obtenerUsuario } from "../../auth";
import Alert from "../../components/ui/Alert";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";

function Kpi({ titulo, valor, detalle }) {
  return (
    <Card>
      <Card.Body>
        <div className="text-xs text-gray-500">{titulo}</div>
        <div className="my-1 text-2xl font-bold text-gray-900">{valor}</div>
        <div className="text-xs text-gray-400">{detalle}</div>
      </Card.Body>
    </Card>
  );
}

function Barra({ etiqueta, valor, maximo }) {
  const ancho = maximo > 0 ? Math.round((valor / maximo) * 100) : 0;
  return (
    <div className="mb-3 last:mb-0">
      <div className="mb-1 flex justify-between text-sm">
        <span className="truncate text-gray-700">{etiqueta}</span>
        <span className="ml-2 font-medium text-gray-900">{valor}</span>
      </div>
      <div className="h-2 rounded-full bg-gray-100">
        <div className="h-2 rounded-full bg-gray-900" style={{ width: `${ancho}%` }} />
      </div>
    </div>
  );
}

function formatearHoras(horas) {
  if (horas == null) return "—";
  if (horas < 1) return "< 1 h";
  if (horas >= 48) return `${(horas / 24).toFixed(1)} d`;
  return `${horas} h`;
}

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

function etiquetaMes(clave) {
  const [anio, mes] = clave.split("-");
  return `${MESES[Number(mes) - 1]} ${anio}`;
}

function fechaCorta(iso) {
  return iso ? new Date(iso).toLocaleDateString("es-EC") : "—";
}

function Grupo({ titulo, items, formato = (x) => x }) {
  return (
    <Card>
      <Card.Body>
        <h3 className="mb-3 text-sm font-semibold text-gray-700">{titulo}</h3>
        {items.map((i) => (
          <Barra
            key={i.etiqueta}
            etiqueta={formato(i.etiqueta)}
            valor={i.total}
            maximo={Math.max(...items.map((x) => x.total))}
          />
        ))}
      </Card.Body>
    </Card>
  );
}

function HistoricoSeccion() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerHistorico()
      .then(setDatos)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <Alert variant="danger">{error}</Alert>;
  if (!datos) return <Spinner size="sm" />;

  return (
    <section className="mt-8">
      <h2 className="mb-1 text-base font-semibold text-gray-900">Histórico importado</h2>
      {datos.total === 0 ? (
        <p className="text-sm text-gray-500">
          Todavía no se importó ningún histórico de tickets.
        </p>
      ) : (
        <>
          <p className="mb-3 text-sm text-gray-500">
            Tickets del export mensual, del {fechaCorta(datos.desde)} al {fechaCorta(datos.hasta)}.
            Última actualización: {fechaCorta(datos.ultima_importacion)}.
          </p>
          <div className="mb-4 grid grid-cols-2 gap-4 xl:grid-cols-4">
            <Kpi titulo="Tickets históricos" valor={datos.total} detalle="Importados del CSV" />
            <Kpi
              titulo="Completados"
              valor={datos.completados}
              detalle={`${Math.round((100 * datos.completados) / datos.total)}% del total`}
            />
            <Kpi titulo="Cancelados" valor={datos.cancelados} detalle="Tickets anulados" />
            <Kpi
              titulo="Tiempo medio de resolución"
              valor={datos.dias_medio_resolucion != null ? `${datos.dias_medio_resolucion} d` : "—"}
              detalle="Días entre creación y solución"
            />
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Grupo titulo="Por mes" items={datos.por_mes} formato={etiquetaMes} />
            <Grupo titulo="Por estado" items={datos.por_estado} />
            <Grupo titulo="Por categoría" items={datos.por_categoria} />
            <Grupo titulo="Por prioridad" items={datos.por_prioridad} />
          </div>
        </>
      )}
    </section>
  );
}

export default function ReportesPage() {
  const personal = obtenerUsuario().rol !== "usuario";
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
            ? "Indicadores de todos los tickets del sistema."
            : "Resumen de tus propios tickets."
        }
      />
      {error && <Alert variant="danger">{error}</Alert>}
      {!resumen && !error && <Spinner size="sm" />}

      {resumen && (
        <>
          <div className="mb-4 grid grid-cols-2 gap-4 xl:grid-cols-4">
            <Kpi
              titulo="Tickets"
              valor={resumen.total}
              detalle={`${resumen.resueltos} resueltos`}
            />
            <Kpi
              titulo="Resueltos por Minutito"
              valor={`${resumen.pct_resolucion_autonoma}%`}
              detalle={
                personal
                  ? `${resumen.resueltos_por_minutito} de ${resumen.total} · meta ≥ 30%`
                  : `${resumen.resueltos_por_minutito} de ${resumen.total}`
              }
            />
            <Kpi
              titulo="Tiempo medio de resolución"
              valor={formatearHoras(resumen.tiempo_medio_resolucion_horas)}
              detalle="Tickets resueltos"
            />
            <Kpi
              titulo="Confianza del clasificador"
              valor={resumen.confianza_media != null ? `${resumen.confianza_media}%` : "—"}
              detalle="Promedio de las predicciones"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <Card.Body>
                <h2 className="mb-3 text-sm font-semibold text-gray-700">Por estado</h2>
                <Barra etiqueta="Abiertos" valor={resumen.abiertos} maximo={resumen.total} />
                <Barra etiqueta="En proceso" valor={resumen.en_proceso} maximo={resumen.total} />
                <Barra etiqueta="Resueltos" valor={resumen.resueltos} maximo={resumen.total} />
                <div className="mt-4 border-t border-gray-100 pt-3 text-xs text-gray-500">
                  Resueltos por Minutito: {resumen.resueltos_por_minutito} · por el equipo:{" "}
                  {resumen.resueltos_por_tecnico}
                </div>
              </Card.Body>
            </Card>

            <Card>
              <Card.Body>
                <h2 className="mb-3 text-sm font-semibold text-gray-700">Por categoría</h2>
                {resumen.por_categoria.length === 0 && (
                  <p className="text-sm text-gray-500">Todavía no hay tickets.</p>
                )}
                {resumen.por_categoria.map((c) => (
                  <Barra
                    key={c.categoria}
                    etiqueta={c.categoria}
                    valor={c.total}
                    maximo={resumen.por_categoria[0].total}
                  />
                ))}
              </Card.Body>
            </Card>
          </div>
        </>
      )}

      {personal && <HistoricoSeccion />}
    </>
  );
}
