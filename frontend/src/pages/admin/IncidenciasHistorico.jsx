import { Bot, User } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  generarEvaluacionHistorico,
  marcarEvaluacionHistorico,
  obtenerEvaluacionHistorico,
  pausarEvaluacionHistorico,
} from "../../api";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import ControlPausa from "./ControlPausa";

const OPCIONES = [
  { valor: "resuelve", texto: "Lo resolvería", variante: "outlineSuccess" },
  { valor: "no_resuelve", texto: "No lo resolvería", variante: "outlineDanger" },
  { valor: "no_aplica", texto: "No es de primer nivel", variante: "outlineSecondary" },
];

function porcentaje(valor) {
  return valor == null ? "—" : `${Math.round(valor * 1000) / 10}%`;
}

function dias(valor) {
  return valor == null ? "—" : `${valor.toLocaleString("es-EC")} días`;
}

function Item({ item, onMarcar }) {
  const [guardando, setGuardando] = useState(false);

  async function marcar(valor) {
    setGuardando(true);
    // Volver a pulsar la opción elegida la desmarca.
    await onMarcar(item.id, item.veredicto === valor ? null : valor);
    setGuardando(false);
  }

  const burbuja = (Icono, esMinutito, texto) => (
    <div className="flex items-start gap-2">
      <span
        className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ring-1 ${
          esMinutito ? "bg-acento-50 text-acento ring-acento-100" : "bg-gray-100 text-gray-500 ring-gray-200"
        }`}
        aria-label={esMinutito ? "Minutito" : "Persona"}
      >
        <Icono size={14} aria-hidden="true" />
      </span>
      <div
        className={`min-w-0 flex-1 whitespace-pre-line break-words rounded-2xl rounded-tl-md px-3.5 py-2.5 text-sm ${
          esMinutito ? "border border-linea bg-superficie text-gray-700" : "bg-marfil text-gray-800"
        }`}
      >
        {texto}
      </div>
    </div>
  );

  return (
    <Card>
      <Card.Body className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-gray-500">
          <span>
            H-{item.id_externo} · {item.categoria}
          </span>
          <Badge color="gray">Tardó {dias(item.dias_reales)}</Badge>
        </div>
        {burbuja(User, false, item.texto)}
        {burbuja(Bot, true, item.respuesta)}
        <div className="flex flex-wrap gap-2" role="group" aria-label="¿La respuesta la habría resuelto?">
          {OPCIONES.map((o) => (
            <Button
              key={o.valor}
              size="sm"
              variant={item.veredicto === o.valor ? "dark" : o.variante}
              aria-pressed={item.veredicto === o.valor}
              disabled={guardando}
              onClick={() => marcar(o.valor)}
            >
              {o.texto}
            </Button>
          ))}
        </div>
      </Card.Body>
    </Card>
  );
}

/** Objetivo 3 medido en las incidencias del histórico: tú marcas si Minutito las habría resuelto. */
export default function IncidenciasHistorico() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [soloPendientes, setSoloPendientes] = useState(true);

  const cargar = useCallback(() => obtenerEvaluacionHistorico().then(setDatos), []);
  useEffect(() => {
    cargar().catch((e) => setError(e.message));
  }, [cargar]);

  const enCurso = datos?.progreso?.en_curso;
  useEffect(() => {
    if (!enCurso) return undefined;
    const intervalo = setInterval(() => cargar().catch(() => {}), 10000);
    return () => clearInterval(intervalo);
  }, [enCurso, cargar]);

  const items = useMemo(
    () => (datos?.items ?? []).filter((i) => !soloPendientes || i.veredicto == null),
    [datos, soloPendientes]
  );

  async function marcar(id, veredicto) {
    try {
      await marcarEvaluacionHistorico(id, veredicto);
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function generar() {
    setError(null);
    try {
      setAviso((await generarEvaluacionHistorico()).mensaje);
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function pausar() {
    try {
      setAviso((await pausarEvaluacionHistorico()).mensaje);
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function reanudar() {
    setError(null);
    try {
      setAviso((await generarEvaluacionHistorico()).mensaje);
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  if (!datos) return error ? <Alert variant="danger">{error}</Alert> : <Spinner size="sm" />;

  const conTexto = datos.incidencias - datos.sin_texto;
  const faltan = conTexto - datos.generadas;
  const cumple = datos.reduccion != null && datos.reduccion >= datos.meta;
  const marcadas = datos.generadas - datos.sin_evaluar;

  return (
    <div className="space-y-4">
      <Alert variant="info">
        Son las {datos.incidencias} incidencias resueltas del histórico, con su tiempo real de resolución. Minutito
        respondió el texto de cada una como si la persona se lo escribiera; tú marcas si esa respuesta la habría
        resuelto, con el mismo criterio que en la evaluación de Minutito. Las que Minutito resolvería cuentan con{" "}
        {datos.minutos_minutito} minutos; las demás, y las {datos.sin_texto} sin texto, con su tiempo real.
      </Alert>
      {error && <Alert variant="danger">{error}</Alert>}
      {aviso && <Alert variant="success">{aviso}</Alert>}

      <div className="grid gap-3 md:grid-cols-3">
        <Card>
          <Card.Body>
            <div className="text-sm font-medium text-gray-500">Reducción del tiempo promedio</div>
            <div className="mt-1 flex items-baseline gap-2">
              {/* Sin ninguna marcada, la simulada es igual a la real: un 0 % que no mide nada. */}
              <span className="text-3xl font-semibold tracking-tight text-noche">
                {marcadas > 0 ? porcentaje(datos.reduccion) : "—"}
              </span>
              {marcadas > 0 && (
                <Badge color={cumple ? "green" : "amber"}>
                  {cumple ? "Cumple" : "Por debajo de"} la meta de {porcentaje(datos.meta)}
                </Badge>
              )}
            </div>
            <p className="mt-1 text-sm text-gray-500">
              {marcadas > 0 ? (
                <>
                  De {dias(datos.media_real_dias)} a {dias(datos.media_simulada_dias)} en promedio.
                  {datos.sin_evaluar > 0 && " Las que faltan marcar cuentan como no resueltas."}
                </>
              ) : (
                `Aún no se marca ninguna. Tiempo real promedio: ${dias(datos.media_real_dias)}.`
              )}
            </p>
          </Card.Body>
        </Card>
        <Card>
          <Card.Body>
            <div className="text-sm font-medium text-gray-500">Marcadas</div>
            <div className="mt-1 text-3xl font-semibold tracking-tight text-noche">
              {marcadas} <span className="text-base text-gray-400">de {datos.generadas}</span>
            </div>
            <p className="mt-1 text-sm text-gray-500">
              Lo resolvería: {datos.resuelve} · No: {datos.no_resuelve} · No es de primer nivel: {datos.no_aplica}
            </p>
          </Card.Body>
        </Card>
        <Card>
          <Card.Body className="space-y-2">
            <div className="text-sm font-medium text-gray-500">Respuestas de Minutito</div>
            <ControlPausa
              enCurso={enCurso}
              pausada={datos.pausada}
              pausando={datos.progreso?.pausar}
              onPausar={pausar}
              onReanudar={reanudar}
            />
            {enCurso ? (
              <p className="flex items-center gap-2 text-sm font-medium text-acento">
                <Spinner size="sm" />
                Generando: {datos.progreso.hechas} de {datos.progreso.total || "…"}. Se actualiza solo.
              </p>
            ) : datos.pausada ? null : faltan > 0 ? (
              <>
                <p className="text-sm text-gray-600">
                  Faltan {faltan} de {conTexto} (necesita Ollama encendido; menos de un minuto cada una).
                </p>
                <Button size="sm" variant="dark" onClick={generar}>
                  Generar las que faltan
                </Button>
              </>
            ) : (
              <p className="text-sm text-gray-600">Listas las {conTexto}.</p>
            )}
          </Card.Body>
        </Card>
      </div>

      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-noche">Incidencias ({items.length})</h2>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" checked={soloPendientes} onChange={(e) => setSoloPendientes(e.target.checked)} />
          Solo las que faltan marcar
        </label>
      </div>
      {items.length === 0 ? (
        <Alert variant="secondary">
          {datos.generadas === 0 ? "Todavía no hay respuestas: pulsa «Generar las que faltan»." : "No queda nada por marcar."}
        </Alert>
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {items.map((i) => (
            <Item key={i.id} item={i} onMarcar={marcar} />
          ))}
        </div>
      )}
    </div>
  );
}
