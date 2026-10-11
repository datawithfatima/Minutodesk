import { FileUp } from "lucide-react";
import { useState } from "react";
import { importarHistorico } from "../../api";
import Alert from "../../components/ui/Alert";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";

function Dato({ titulo, valor, detalle }) {
  return (
    <div className="rounded-lg border border-gray-200 p-3">
      <div className="text-xs text-gray-500">{titulo}</div>
      <div className="text-xl font-bold text-gray-900">{valor}</div>
      {detalle && <div className="text-xs text-gray-400">{detalle}</div>}
    </div>
  );
}

export default function ImportarPage() {
  const [archivo, setArchivo] = useState(null);
  const [reporte, setReporte] = useState(null);
  const [error, setError] = useState(null);
  const [trabajando, setTrabajando] = useState(false);

  async function ejecutar(aplicar) {
    setTrabajando(true);
    setError(null);
    try {
      setReporte(await importarHistorico(archivo, aplicar));
    } catch (e) {
      setError(e.message);
    } finally {
      setTrabajando(false);
    }
  }

  function elegir(e) {
    const nuevo = e.target.files?.[0] ?? null;
    setArchivo(nuevo);
    setReporte(null);
    setError(null);
  }

  return (
    <>
      <PageHeader
        icon={FileUp}
        title="Importar histórico"
        subtitle="Sube el CSV mensual de tickets. Se limpia y se revisa antes de guardarse."
      />

      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}

      <Card className="mb-4">
        <Card.Body>
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[240px] flex-1">
              <label className="mb-1 block text-sm font-medium text-gray-700">Archivo CSV</label>
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={elegir}
                className="block w-full text-sm text-gray-700 file:mr-3 file:rounded-md file:border-0 file:bg-gray-100 file:px-3 file:py-2 file:text-sm file:font-medium hover:file:bg-gray-200"
              />
            </div>
            <Button
              variant="dark"
              disabled={!archivo || trabajando}
              onClick={() => ejecutar(false)}
            >
              {trabajando && !reporte ? <Spinner size="sm" /> : "Revisar archivo"}
            </Button>
          </div>
          <ul className="mt-4 list-disc space-y-1 pl-5 text-xs text-gray-500">
            <li>Los tickets se identifican por su ID: los existentes se actualizan y los nuevos se agregan.</li>
            <li>Se descartan filas sin ID, sin estado o con fecha de creación ilegible.</li>
            <li>Se unifican mayúsculas, tildes y espacios en estado, prioridad y categoría.</li>
            <li>La fecha de solución se ignora si es ilegible o anterior a la creación.</li>
            <li>No se guardan nombres de personas ni la descripción de los tickets.</li>
          </ul>
        </Card.Body>
      </Card>

      {reporte && (
        <Card>
          <Card.Body>
            <h2 className="mb-3 text-sm font-semibold text-gray-700">
              {reporte.aplicado ? "Importación realizada" : "Vista previa (todavía no se guardó nada)"}
            </h2>

            {reporte.aplicado && (
              <Alert variant="success" className="mb-3">
                Listo: ahora hay {reporte.total_en_base} tickets históricos. Ya puedes verlos en
                Reportes.
              </Alert>
            )}

            <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              <Dato titulo="Filas leídas" valor={reporte.filas} detalle={`${reporte.validas} válidas`} />
              <Dato titulo="Nuevos" valor={reporte.nuevos} />
              <Dato
                titulo="Actualizados"
                valor={reporte.actualizados}
                detalle={`${reporte.sin_cambios} sin cambios`}
              />
              <Dato titulo="Descartados" valor={reporte.omitidos} />
            </div>

            <div className="space-y-1 text-sm text-gray-600">
              {reporte.duplicados_en_archivo > 0 && (
                <p>• {reporte.duplicados_en_archivo} ID repetidos en el archivo: se usó la última fila.</p>
              )}
              {reporte.fechas_solucion_descartadas > 0 && (
                <p>
                  • {reporte.fechas_solucion_descartadas} fechas de solución ignoradas por ser
                  ilegibles o anteriores a la creación.
                </p>
              )}
              {reporte.completados_sin_fecha > 0 && (
                <p>
                  • {reporte.completados_sin_fecha} tickets completados quedan sin fecha de
                  solución (no cuentan para el tiempo medio).
                </p>
              )}
            </div>

            {reporte.incidencias.length > 0 && (
              <details className="mt-3">
                <summary className="cursor-pointer text-sm font-medium text-gray-700">
                  Ver detalle (primeras {reporte.incidencias.length})
                </summary>
                <ul className="mt-2 space-y-1 pl-5 text-xs text-gray-500">
                  {reporte.incidencias.map((i) => (
                    <li key={i} className="list-disc">
                      {i}
                    </li>
                  ))}
                </ul>
              </details>
            )}

            {!reporte.aplicado && (
              <div className="mt-4 flex gap-2">
                <Button
                  variant="dark"
                  disabled={trabajando || reporte.validas === 0}
                  onClick={() => ejecutar(true)}
                >
                  {trabajando ? <Spinner size="sm" /> : "Confirmar e importar"}
                </Button>
                <Button variant="outlineSecondary" onClick={() => setReporte(null)}>
                  Cancelar
                </Button>
              </div>
            )}
          </Card.Body>
        </Card>
      )}
    </>
  );
}
