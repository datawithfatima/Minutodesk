import { Bot, ClipboardList, Pencil } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  generarEvaluacionMinutito,
  pausarEvaluacionMinutito,
  guardarSolucionEsperada,
  marcarEvaluacionMinutito,
  obtenerEvaluacionMinutito,
} from "../../api";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import ControlPausa from "./ControlPausa";
import { inputClass } from "../../components/ui/formStyles";

const OPCIONES = [
  { valor: "resuelve", texto: "Lo resolvería", variante: "outlineSuccess" },
  { valor: "no_resuelve", texto: "No lo resolvería", variante: "outlineDanger" },
  { valor: "no_aplica", texto: "No es de primer nivel", variante: "outlineSecondary" },
];

function porcentaje(valor) {
  return valor == null ? "—" : `${Math.round(valor * 1000) / 10}%`;
}

// Lo que el equipo considera la solución correcta: es la referencia para el veredicto,
// no reemplaza la respuesta de Minutito (que es lo que se evalúa).
function SolucionEsperada({ item, onGuardar }) {
  const [editando, setEditando] = useState(false);
  const [texto, setTexto] = useState("");
  const [guardando, setGuardando] = useState(false);

  function abrir() {
    setTexto(item.solucion_esperada ?? "");
    setEditando(true);
  }

  async function guardar() {
    setGuardando(true);
    if (await onGuardar(item.id, texto)) setEditando(false);
    setGuardando(false);
  }

  if (editando) {
    return (
      <div className="space-y-2">
        <label htmlFor={`solucion-${item.id}`} className="text-xs font-medium text-gray-600">
          Qué se debía hacer
        </label>
        <textarea
          id={`solucion-${item.id}`}
          rows={3}
          maxLength={2000}
          className={inputClass}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="La solución correcta o los pasos que había que seguir…"
          autoFocus
        />
        <div className="flex gap-2">
          <Button size="sm" variant="primary" onClick={guardar} disabled={guardando}>
            Guardar
          </Button>
          <Button size="sm" variant="outlineSecondary" onClick={() => setEditando(false)} disabled={guardando}>
            Cancelar
          </Button>
        </div>
      </div>
    );
  }

  if (!item.solucion_esperada) {
    return (
      <button
        type="button"
        onClick={abrir}
        className="flex items-center gap-1.5 text-sm font-medium text-acento hover:underline"
      >
        <ClipboardList size={14} aria-hidden="true" />
        Escribir qué se debía hacer
      </button>
    );
  }

  return (
    <div className="rounded-lg border border-green-200 bg-green-50 px-3.5 py-2.5">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-green-800">Qué se debía hacer</span>
        <button
          type="button"
          onClick={abrir}
          aria-label="Editar qué se debía hacer"
          className="flex items-center gap-1 text-xs text-green-800 hover:underline"
        >
          <Pencil size={12} aria-hidden="true" />
          Editar
        </button>
      </div>
      <p className="whitespace-pre-line break-words text-sm text-gray-700">{item.solucion_esperada}</p>
    </div>
  );
}

function Item({ item, onMarcar, onGuardarSolucion }) {
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
          <div className="min-w-0 flex-1 whitespace-pre-line break-words rounded-2xl rounded-tl-md border border-linea bg-superficie px-3.5 py-2.5 text-sm text-gray-700">
            {item.respuesta}
          </div>
        </div>
        <SolucionEsperada item={item} onGuardar={onGuardarSolucion} />
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

  // Mientras corre en segundo plano, la pantalla se actualiza sola.
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
      await marcarEvaluacionMinutito(id, veredicto);
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function guardarSolucion(id, solucion) {
    try {
      await guardarSolucionEsperada(id, solucion);
      await cargar();
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    }
  }

  async function generar(todas = false) {
    if (
      todas &&
      !window.confirm(
        "Se volverán a generar las respuestas de todos los tickets usando las soluciones anotadas. " +
          "Las marcas de «Lo resolvería / No lo resolvería» se borran, porque cambian las respuestas. ¿Continuar?"
      )
    )
      return;
    setError(null);
    try {
      setAviso((await generarEvaluacionMinutito(todas)).mensaje);
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function pausar() {
    try {
      setAviso((await pausarEvaluacionMinutito()).mensaje);
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function reanudar() {
    setError(null);
    try {
      setAviso((await generarEvaluacionMinutito(false, true)).mensaje);
      await cargar();
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
        <strong className="font-semibold">Evaluación experta</strong> · tickets cargados · no modifica los tickets
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
                Generando respuestas: {datos.progreso.hechas} de {datos.progreso.total || "…"}. Se actualiza solo.
              </p>
            ) : datos.pausada ? null : (
              <>
                <p className="text-sm text-gray-600">
                  {faltan > 0
                    ? `Faltan ${faltan} de ${datos.tickets_cargados} · requiere Ollama`
                    : `Generadas para los ${datos.tickets_cargados} tickets cargados.`}
                </p>
                {faltan > 0 && (
                  <Button size="sm" variant="dark" onClick={() => generar()}>
                    Generar respuestas pendientes
                  </Button>
                )}
                {datos.con_solucion > 0 && (
                  <>
                    <p className="text-sm text-gray-600">
                      {datos.con_solucion} {datos.con_solucion === 1 ? "solución anotada" : "soluciones anotadas"} ·
                      dejando uno fuera
                    </p>
                    <Button size="sm" variant="outlinePrimary" onClick={() => generar(true)}>
                      Volver a generar con lo aprendido
                    </Button>
                  </>
                )}
              </>
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
            <Item key={i.id} item={i} onMarcar={marcar} onGuardarSolucion={guardarSolucion} />
          ))}
        </div>
      )}
    </div>
  );
}
