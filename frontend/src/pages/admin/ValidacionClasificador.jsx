import { CheckCircle2, FileUp, XCircle } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { cargarValidacion, obtenerValidacion } from "../../api";
import { tituloTipo } from "../../components/tickets/formato";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";

function porcentaje(valor) {
  return valor == null ? "—" : `${Math.round(valor * 1000) / 10}%`;
}

function Indicador({ titulo, valor, objetivo, detalle }) {
  const cumple = valor != null && objetivo != null && valor >= objetivo;
  return (
    <Card>
      <Card.Body>
        <div className="text-sm font-medium text-gray-500">{titulo}</div>
        <div className="mt-1 flex items-baseline gap-2">
          <span className="text-3xl font-semibold tracking-tight text-noche">{porcentaje(valor)}</span>
          {objetivo != null && valor != null && (
            <Badge color={cumple ? "green" : "amber"}>
              {cumple ? "Cumple" : "Por debajo de"} la meta de {porcentaje(objetivo)}
            </Badge>
          )}
        </div>
        {detalle && <p className="mt-1 text-sm text-gray-500">{detalle}</p>}
      </Card.Body>
    </Card>
  );
}

const MOTIVOS = [
  ["de_entrenamiento", "ya son parte del histórico de entrenamiento"],
  ["ya_cargados", "ya se habían cargado antes"],
  ["sin_clasificacion_real", "no traen tipo, categoría o descripción"],
  ["sin_id_o_repetidos", "no tienen ID o están repetidos en el archivo"],
];

function CargarCsv({ onCargado }) {
  const [archivo, setArchivo] = useState(null);
  const [previa, setPrevia] = useState(null);
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState(null);

  async function revisar(e) {
    const elegido = e.target.files?.[0] ?? null;
    setArchivo(elegido);
    setPrevia(null);
    setError(null);
    if (!elegido) return;
    setTrabajando(true);
    try {
      setPrevia(await cargarValidacion(elegido, false));
    } catch (err) {
      setError(err.message);
    } finally {
      setTrabajando(false);
    }
  }

  async function confirmar() {
    setTrabajando(true);
    setError(null);
    try {
      const r = await cargarValidacion(archivo, true);
      setPrevia(null);
      setArchivo(null);
      onCargado(r.creados);
    } catch (err) {
      setError(err.message);
    } finally {
      setTrabajando(false);
    }
  }

  return (
    <Card>
      <Card.Body className="space-y-3">
        <div>
          <h2 className="text-sm font-semibold text-noche">Cargar tickets nuevos para validar</h2>
          <p className="text-sm text-gray-500">
            Usa el export de siempre: los tickets que ya están en el histórico se ignoran solos, y repetir la
            carga no duplica nada. Estos tickets no se usan para entrenar ni entran en los indicadores de soporte.
          </p>
        </div>
        {error && <Alert variant="danger">{error}</Alert>}
        <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-linea bg-white px-3 py-2 text-sm font-medium text-noche hover:bg-marfil">
          <FileUp size={16} aria-hidden="true" />
          {archivo ? archivo.name : "Elegir archivo CSV"}
          <input type="file" accept=".csv,text/csv" className="sr-only" onChange={revisar} />
        </label>
        {trabajando && <Spinner size="sm" />}
        {previa && (
          <div className="space-y-2 rounded-lg bg-marfil p-3 text-sm">
            <p className="text-noche">
              De {previa.filas} filas, <strong>{previa.validables}</strong> se crearán como tickets de validación.
            </p>
            <ul className="list-disc pl-5 text-gray-600">
              {MOTIVOS.filter(([clave]) => previa[clave] > 0).map(([clave, texto]) => (
                <li key={clave}>
                  {previa[clave]} {texto}
                </li>
              ))}
            </ul>
            <Button size="sm" variant="dark" disabled={trabajando || previa.validables === 0} onClick={confirmar}>
              Confirmar y clasificar {previa.validables} tickets
            </Button>
          </div>
        )}
      </Card.Body>
    </Card>
  );
}

export default function ValidacionClasificador() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [soloErrores, setSoloErrores] = useState(false);

  const cargar = useCallback(() => obtenerValidacion().then(setDatos), []);
  useEffect(() => {
    cargar().catch((e) => setError(e.message));
  }, [cargar]);

  const filas = useMemo(
    () => (datos?.tickets ?? []).filter((t) => !soloErrores || !t.acierto_tipo || t.acierto_categoria === false),
    [datos, soloErrores]
  );

  if (error) return <Alert variant="danger">{error}</Alert>;
  if (!datos) return <Spinner size="sm" />;

  return (
    <div className="space-y-4">
      {aviso && <Alert variant="success">{aviso}</Alert>}
      <CargarCsv
        onCargado={(n) => {
          setAviso(`Se crearon y clasificaron ${n} tickets de validación.`);
          cargar().catch((e) => setError(e.message));
        }}
      />

      {datos.total === 0 ? (
        <Alert variant="secondary">Todavía no hay tickets de validación.</Alert>
      ) : (
        <>
          <p className="text-sm text-gray-500">
            {datos.total} tickets creados entre el {new Date(datos.desde).toLocaleDateString()} y el{" "}
            {new Date(datos.hasta).toLocaleDateString()}, posteriores a los datos de entrenamiento.
          </p>
          <div className="grid gap-3 md:grid-cols-3">
            <Indicador
              titulo="Acierto en el tipo"
              valor={datos.acierto_tipo}
              objetivo={datos.objetivo}
              detalle={`Sobre ${datos.total} tickets.`}
            />
            <Indicador
              titulo="Acierto en la categoría"
              valor={datos.acierto_categoria}
              objetivo={datos.objetivo}
              detalle={`Sobre ${datos.categoria_evaluables} tickets con una categoría que el modelo conoce.`}
            />
            <Indicador
              titulo={`Categoría con confianza ≥ ${datos.umbral != null ? porcentaje(datos.umbral) : "umbral"}`}
              valor={datos.categoria_en_umbral}
              objetivo={datos.objetivo}
              detalle={`Cubre el ${porcentaje(datos.cobertura_en_umbral)} de los tickets; el resto se pide confirmar.`}
            />
          </div>
          {datos.tickets_no_vistos > 0 && (
            <Alert variant="info">
              {datos.tickets_no_vistos} ticket(s) son de una categoría que no existía en el entrenamiento (
              {datos.categorias_no_vistas.join(", ")}): el modelo no puede acertarlos, así que se muestran aparte y no
              cuentan en el acierto de categoría.
            </Alert>
          )}

          <div className="grid gap-3 lg:grid-cols-2">
            <Card>
              <Card.Body>
                <h2 className="mb-2 text-sm font-semibold text-noche">Acierto por categoría</h2>
                <table className="w-full text-sm">
                  <thead className="text-left text-xs text-gray-500">
                    <tr>
                      <th className="py-1 font-medium">Categoría real</th>
                      <th className="py-1 text-right font-medium">Tickets</th>
                      <th className="py-1 text-right font-medium">Acierto</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-linea">
                    {datos.por_categoria.map((c) => (
                      <tr key={c.categoria}>
                        <td className="py-1.5">{c.categoria}</td>
                        <td className="py-1.5 text-right">{c.total}</td>
                        <td className="py-1.5 text-right">{porcentaje(c.aciertos / c.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card.Body>
            </Card>
            <Card>
              <Card.Body>
                <h2 className="mb-2 text-sm font-semibold text-noche">Confusiones más frecuentes</h2>
                {datos.errores_frecuentes.length === 0 ? (
                  <p className="text-sm text-gray-500">Sin errores de categoría.</p>
                ) : (
                  <ul className="space-y-1.5 text-sm">
                    {datos.errores_frecuentes.map((e) => (
                      <li key={`${e.real}-${e.predicha}`} className="flex justify-between gap-3">
                        <span>
                          Era <strong className="font-medium">{e.real}</strong> y predijo{" "}
                          <strong className="font-medium">{e.predicha}</strong>
                        </span>
                        <span className="shrink-0 text-gray-500">{e.veces}×</span>
                      </li>
                    ))}
                  </ul>
                )}
              </Card.Body>
            </Card>
          </div>

          <Card>
            <Card.Body>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-sm font-semibold text-noche">Tickets de validación ({filas.length})</h2>
                <label className="flex items-center gap-2 text-sm text-gray-600">
                  <input type="checkbox" checked={soloErrores} onChange={(e) => setSoloErrores(e.target.checked)} />
                  Solo los que falló
                </label>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-sm">
                  <thead className="text-left text-xs text-gray-500">
                    <tr>
                      <th className="py-1 font-medium">ID</th>
                      <th className="py-1 font-medium">Descripción</th>
                      <th className="py-1 font-medium">Tipo (real → predicho)</th>
                      <th className="py-1 font-medium">Categoría (real → predicha)</th>
                      <th className="py-1 text-right font-medium">Confianza</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-linea align-top">
                    {filas.map((t) => (
                      <tr key={t.id}>
                        <td className="py-2 pr-2 text-gray-500">{t.id_externo}</td>
                        <td className="max-w-[320px] py-2 pr-2">
                          <span className="line-clamp-2" title={t.texto}>
                            {t.texto}
                          </span>
                        </td>
                        <td className="py-2 pr-2">
                          <Resultado ok={t.acierto_tipo} />
                          {tituloTipo(t.tipo_real)}
                          {!t.acierto_tipo && <span className="text-gray-500"> → {tituloTipo(t.tipo_predicho)}</span>}
                        </td>
                        <td className="py-2 pr-2">
                          <Resultado ok={t.acierto_categoria} />
                          {t.categoria_real}
                          {t.categoria_esperada && t.categoria_esperada !== t.categoria_real && (
                            <span className="text-gray-400"> ({t.categoria_esperada})</span>
                          )}
                          {t.acierto_categoria !== true && (
                            <span className="text-gray-500"> → {t.categoria_predicha}</span>
                          )}
                        </td>
                        <td className="py-2 text-right">{porcentaje(t.confianza)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card.Body>
          </Card>
        </>
      )}
    </div>
  );
}

function Resultado({ ok }) {
  if (ok == null) return <span className="mr-1 text-xs text-gray-400">(no evaluable) </span>;
  return ok ? (
    <CheckCircle2 size={14} className="mr-1 inline text-green-600" aria-label="Acierto" />
  ) : (
    <XCircle size={14} className="mr-1 inline text-red-500" aria-label="Error" />
  );
}
