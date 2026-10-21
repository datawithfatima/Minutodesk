import { Bot } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { generarEvaluacionMinutito, marcarEvaluacionMinutito, obtenerEvaluacionMinutito } from "../../api";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";

const OPCIONES = [
  { valor: "resuelve", texto: "Lo resolvería", variante: "outlineSuccess" },
  { valor: "no_resuelve", texto: "No lo resolvería", variante: "outlineDanger" },
  { valor: "no_aplica", texto: "No es de primer nivel", variante: "outlineSecondary" },
];

function porcentaje(valor) {
  return valor == null ? "—" : `${Math.round(valor * 1000) / 10}%`;
}

function Item({ item, onMarcar }) {
  const [guardando, setGuardando] = useState(false);

  async function marcar(valor) {
    setGuardando(true);
    // Volver a pulsar la opción elegida la desmarca.
    await onMarcar(item.id, item.veredicto === valor ? null : valor);
    setGuardando(false);
  }

  return (
    <Card>
      <Card.Body className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-gray-500">
          <span>
            Ticket #{item.ticket_id} · {item.categoria}
          </span>
          {item.escalado && <Badge color="amber">Minutito lo derivó a soporte</Badge>}
        </div>
        <p className="whitespace-pre-line break-words text-sm text-noche">{item.texto}</p>
        <div className="flex items-start gap-2">
          <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-acento-50 text-acento ring-1 ring-acento-100">
            <Bot size={14} aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1 whitespace-pre-line break-words rounded-2xl rounded-tl-md border border-linea bg-white px-3.5 py-2.5 text-sm text-gray-700">
            {item.respuesta}
          </div>
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="¿La respuesta lo resolvería?">
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

/** Evaluación simulada: qué habría respondido Minutito a los tickets cargados y si lo resolvía. */
export default function EvaluacionMinutito() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [soloPendientes, setSoloPendientes] = useState(true);

  const cargar = useCallback(() => obtenerEvaluacionMinutito().then(setDatos), []);
  useEffect(() => {
    cargar().catch((e) => setError(e.message));
  }, [cargar]);

  const items = useMemo(
    () => (datos?.items ?? []).filter((i) => !soloPendientes || i.veredicto == null),
    [datos, soloPendientes]
  );

  async function marcar(id, veredicto) {
    try {
      await marcarEvaluacionMinutito(id, veredicto);
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function generar() {
    setError(null);
    try {
      setAviso((await generarEvaluacionMinutito()).mensaje);
    } catch (e) {
      setError(e.message);
    }
  }

  if (!datos) return error ? <Alert variant="danger">{error}</Alert> : <Spinner size="sm" />;

  const faltan = datos.tickets_cargados - datos.con_respuesta;
  const cumple = datos.pct_resolveria != null && datos.pct_resolveria >= datos.meta;

  return (
    <div className="space-y-4">
      <Alert variant="info">
        Estos tickets se atendieron en la herramienta anterior, así que nadie habló con Minutito. Aquí se le pasa
        a Minutito el texto de cada ticket y tú marcas si su respuesta lo habría resuelto. Es una{" "}
        <strong className="font-semibold">estimación por evaluación experta</strong>: no crea conversaciones ni
        cambia los tickets, y no se mezcla con la resolución autónoma real.
      </Alert>
      {error && <Alert variant="danger">{error}</Alert>}
      {aviso && <Alert variant="success">{aviso}</Alert>}

      <div className="grid gap-3 md:grid-cols-3">
        <Card>
          <Card.Body>
            <div className="text-sm font-medium text-gray-500">Minutito lo habría resuelto</div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-3xl font-semibold tracking-tight text-noche">{porcentaje(datos.pct_resolveria)}</span>
              {datos.pct_resolveria != null && (
                <Badge color={cumple ? "green" : "amber"}>
                  {cumple ? "Cumple" : "Por debajo de"} la meta de {porcentaje(datos.meta)}
                </Badge>
              )}
            </div>
            <p className="mt-1 text-sm text-gray-500">
              {datos.resuelve} de {datos.resuelve + datos.no_resuelve} consultas de primer nivel.
            </p>
          </Card.Body>
        </Card>
        <Card>
          <Card.Body>
            <div className="text-sm font-medium text-gray-500">Evaluados</div>
            <div className="mt-1 text-3xl font-semibold tracking-tight text-noche">
              {datos.con_respuesta - datos.sin_evaluar} <span className="text-base text-gray-400">de {datos.con_respuesta}</span>
            </div>
            <p className="mt-1 text-sm text-gray-500">{datos.no_aplica} marcados como «no es de primer nivel».</p>
          </Card.Body>
        </Card>
        <Card>
          <Card.Body className="space-y-2">
            <div className="text-sm font-medium text-gray-500">Respuestas de Minutito</div>
            <p className="text-sm text-gray-600">
              {faltan > 0
                ? `Faltan ${faltan} de ${datos.tickets_cargados} tickets por generar (necesita Ollama encendido).`
                : `Generadas para los ${datos.tickets_cargados} tickets cargados.`}
            </p>
            {faltan > 0 && (
              <Button size="sm" variant="dark" onClick={generar}>
                Generar respuestas pendientes
              </Button>
            )}
          </Card.Body>
        </Card>
      </div>

      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-noche">Tickets ({items.length})</h2>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" checked={soloPendientes} onChange={(e) => setSoloPendientes(e.target.checked)} />
          Solo los que faltan evaluar
        </label>
      </div>
      {items.length === 0 ? (
        <Alert variant="secondary">{soloPendientes ? "No queda nada por evaluar." : "Todavía no hay respuestas."}</Alert>
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
