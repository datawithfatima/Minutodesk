import { Bot, User } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { generarPruebaControlada, marcarPruebaControlada, obtenerPruebaControlada } from "../../api";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";

const OPCIONES = [
  { valor: "resuelve", texto: "Minutito lo resolvió", variante: "outlineSuccess" },
  { valor: "no_resuelve", texto: "No lo resolvió", variante: "outlineDanger" },
];

const TERMINO = {
  resuelto: { texto: "El colaborador dijo que funcionó", color: "green" },
  ticket: { texto: "Terminó en ticket", color: "amber" },
  sin_cierre: { texto: "Sin cierre", color: "gray" },
};

function porcentaje(valor) {
  return valor == null ? "—" : `${Math.round(valor * 1000) / 10}%`;
}

function Item({ item, onMarcar }) {
  const [guardando, setGuardando] = useState(false);
  const termino = TERMINO[item.termino] ?? TERMINO.sin_cierre;

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
          <span>{item.tema}</span>
          <Badge color={termino.color}>{termino.texto}</Badge>
        </div>
        <p className="text-sm font-medium text-noche">{item.situacion}</p>
        <div className="rounded-lg border border-green-200 bg-green-50 px-3.5 py-2 text-sm text-gray-700">
          <span className="font-medium text-green-800">Lo que lo arregla: </span>
          {item.arreglo}
        </div>

        <div className="space-y-2">
          {item.conversacion.map((m, i) => {
            const esMinutito = m.rol === "minutito";
            const Icono = esMinutito ? Bot : User;
            return (
              <div key={i} className="flex items-start gap-2">
                <span
                  className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ring-1 ${
                    esMinutito ? "bg-acento-50 text-acento ring-acento-100" : "bg-gray-100 text-gray-500 ring-gray-200"
                  }`}
                  aria-label={esMinutito ? "Minutito" : "Colaborador simulado"}
                >
                  <Icono size={14} aria-hidden="true" />
                </span>
                <div
                  className={`min-w-0 flex-1 whitespace-pre-line break-words rounded-2xl rounded-tl-md px-3.5 py-2.5 text-sm ${
                    esMinutito ? "border border-linea bg-white text-gray-700" : "bg-marfil text-gray-800"
                  }`}
                >
                  {m.texto}
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex flex-wrap gap-2" role="group" aria-label="¿Minutito lo resolvió?">
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

/** Prueba controlada: un colaborador simulado conversa con Minutito y tú decides si lo resolvió. */
export default function PruebaControlada() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [soloPendientes, setSoloPendientes] = useState(true);

  const cargar = useCallback(() => obtenerPruebaControlada().then(setDatos), []);
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
      await marcarPruebaControlada(id, veredicto);
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  async function generar(todas = false) {
    if (
      todas &&
      !window.confirm("Se volverán a correr todas las conversaciones y se borrarán tus marcas. ¿Continuar?")
    )
      return;
    setError(null);
    try {
      setAviso((await generarPruebaControlada(todas)).mensaje);
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  if (!datos) return error ? <Alert variant="danger">{error}</Alert> : <Spinner size="sm" />;

  const faltan = datos.escenarios - datos.generadas;
  const cumple = datos.pct_resolveria != null && datos.pct_resolveria >= datos.meta;
  const evaluados = datos.resuelve + datos.no_resuelve;

  return (
    <div className="space-y-4">
      <Alert variant="info">
        Un agente hace de colaborador con {datos.escenarios} problemas típicos de primer nivel ya definidos (Wi-Fi,
        impresoras, Outlook, contraseñas, VPN, Teams…) y conversa con Minutito hasta 3 respuestas. Tú lees cada
        conversación y marcas si <strong className="font-semibold">las respuestas de Minutito llevaban a lo que lo
        arregla</strong>. Decide por eso y no por lo que dijo el colaborador simulado, que a veces se equivoca.
      </Alert>
      {error && <Alert variant="danger">{error}</Alert>}
      {aviso && <Alert variant="success">{aviso}</Alert>}

      <div className="grid gap-3 md:grid-cols-3">
        <Card>
          <Card.Body>
            <div className="text-sm font-medium text-gray-500">Minutito lo resolvió</div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-3xl font-semibold tracking-tight text-noche">{porcentaje(datos.pct_resolveria)}</span>
              {datos.pct_resolveria != null && (
                <Badge color={cumple ? "green" : "amber"}>
                  {cumple ? "Cumple" : "Por debajo de"} la meta de {porcentaje(datos.meta)}
                </Badge>
              )}
            </div>
            <p className="mt-1 text-sm text-gray-500">
              {datos.resuelve} de {evaluados} conversaciones evaluadas.
            </p>
          </Card.Body>
        </Card>
        <Card>
          <Card.Body>
            <div className="text-sm font-medium text-gray-500">Evaluadas</div>
            <div className="mt-1 text-3xl font-semibold tracking-tight text-noche">
              {datos.generadas - datos.sin_evaluar}{" "}
              <span className="text-base text-gray-400">de {datos.generadas}</span>
            </div>
          </Card.Body>
        </Card>
        <Card>
          <Card.Body className="space-y-2">
            <div className="text-sm font-medium text-gray-500">Conversaciones</div>
            {enCurso ? (
              <p className="flex items-center gap-2 text-sm font-medium text-acento">
                <Spinner size="sm" />
                Corriendo: {datos.progreso.hechas} de {datos.progreso.total || "…"}. Se actualiza solo.
              </p>
            ) : (
              <>
                <p className="text-sm text-gray-600">
                  {faltan > 0
                    ? `Faltan ${faltan} de ${datos.escenarios} (necesita Ollama encendido; 1 o 2 minutos cada una).`
                    : `Corridas las ${datos.escenarios}.`}
                </p>
                {faltan > 0 && (
                  <Button size="sm" variant="dark" onClick={() => generar()}>
                    Correr las que faltan
                  </Button>
                )}
                {datos.generadas > 0 && (
                  <Button size="sm" variant="outlinePrimary" onClick={() => generar(true)}>
                    Volver a correr todas
                  </Button>
                )}
              </>
            )}
          </Card.Body>
        </Card>
      </div>

      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-noche">Conversaciones ({items.length})</h2>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" checked={soloPendientes} onChange={(e) => setSoloPendientes(e.target.checked)} />
          Solo las que faltan evaluar
        </label>
      </div>
      {items.length === 0 ? (
        <Alert variant="secondary">
          {datos.generadas === 0
            ? "Todavía no hay conversaciones: pulsa «Correr las que faltan»."
            : "No queda nada por evaluar."}
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
