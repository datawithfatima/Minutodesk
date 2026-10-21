import { ClipboardCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { listarMisAprobaciones, responderAprobacion } from "../../api";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";
import { inputClass } from "../../components/ui/formStyles";

const ESTADO = {
  pendiente: { texto: "Pendiente", color: "amber" },
  aprobada: { texto: "Aprobada", color: "green" },
  rechazada: { texto: "Rechazada", color: "gray" },
};

function fecha(valor) {
  return new Date(valor).toLocaleString([], { dateStyle: "short", timeStyle: "short" });
}

function Solicitud({ a, onRespondida }) {
  const [comentario, setComentario] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const estado = ESTADO[a.estado] ?? ESTADO.pendiente;
  const cancelado = a.ticket_estado === "cancelado";

  async function responder(aprobada) {
    setEnviando(true);
    setError(null);
    try {
      await responderAprobacion(a.id, { aprobada, comentario: comentario.trim() || null });
      onRespondida();
    } catch (e) {
      setError(e.message);
      setEnviando(false);
    }
  }

  return (
    <Card>
      <Card.Body className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-noche">
              Ticket #{a.ticket_id} · de {a.ticket_solicitante}
            </h2>
            <p className="text-xs text-gray-500">
              Pedida por {a.solicitada_por} el {fecha(a.creado_en)}
            </p>
          </div>
          <Badge color={estado.color}>{estado.texto}</Badge>
        </div>

        <div className="rounded-lg bg-marfil px-3 py-2 text-sm">
          <div className="text-xs font-medium text-gray-500">Qué se debe aprobar</div>
          <p className="whitespace-pre-line break-words text-noche">{a.descripcion}</p>
        </div>
        {a.ticket_texto && (
          <details className="text-sm text-gray-600">
            <summary className="cursor-pointer text-xs font-medium text-gray-500">Ver el ticket</summary>
            <p className="mt-1 whitespace-pre-line break-words">{a.ticket_texto}</p>
          </details>
        )}

        {a.estado !== "pendiente" ? (
          a.comentario && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">Tu comentario:</span> {a.comentario}
            </p>
          )
        ) : cancelado ? (
          <Alert variant="secondary">El ticket fue cancelado: ya no hace falta responder.</Alert>
        ) : (
          <div className="space-y-2">
            {error && <Alert variant="danger">{error}</Alert>}
            <label htmlFor={`comentario-${a.id}`} className="sr-only">
              Comentario
            </label>
            <textarea
              id={`comentario-${a.id}`}
              rows={2}
              maxLength={500}
              value={comentario}
              onChange={(e) => setComentario(e.target.value)}
              placeholder="Comentario (obligatorio si rechazas)"
              className={`${inputClass} resize-y`}
            />
            <div className="flex flex-wrap gap-2">
              <Button variant="outlineSuccess" size="sm" disabled={enviando} onClick={() => responder(true)}>
                Aprobar
              </Button>
              <Button
                variant="outlineDanger"
                size="sm"
                disabled={enviando || !comentario.trim()}
                onClick={() => responder(false)}
                title={!comentario.trim() ? "Escribe el motivo para rechazar" : undefined}
              >
                Rechazar
              </Button>
            </div>
          </div>
        )}
      </Card.Body>
    </Card>
  );
}

export default function AprobacionesPage() {
  const [aprobaciones, setAprobaciones] = useState(null);
  const [error, setError] = useState(null);

  const cargar = useCallback(() => listarMisAprobaciones().then(setAprobaciones), []);

  useEffect(() => {
    cargar().catch((e) => setError(e.message));
  }, [cargar]);

  const pendientes = aprobaciones?.filter((a) => a.estado === "pendiente") ?? [];
  const respondidas = aprobaciones?.filter((a) => a.estado !== "pendiente") ?? [];

  return (
    <>
      <PageHeader
        icon={ClipboardCheck}
        title="Aprobaciones"
        subtitle="Lo que el equipo de soporte necesita que apruebes para continuar con un ticket."
      />
      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}
      {aprobaciones === null && !error && <Spinner size="sm" />}
      {aprobaciones && (
        <div className="space-y-6">
          <section>
            <h2 className="mb-2 text-sm font-semibold text-gray-500">Pendientes ({pendientes.length})</h2>
            {pendientes.length === 0 ? (
              <Alert variant="secondary">No tienes aprobaciones pendientes.</Alert>
            ) : (
              <div className="grid gap-3 lg:grid-cols-2">
                {pendientes.map((a) => (
                  <Solicitud key={a.id} a={a} onRespondida={() => cargar().catch((e) => setError(e.message))} />
                ))}
              </div>
            )}
          </section>
          {respondidas.length > 0 && (
            <section>
              <h2 className="mb-2 text-sm font-semibold text-gray-500">Respondidas</h2>
              <div className="grid gap-3 lg:grid-cols-2">
                {respondidas.map((a) => (
                  <Solicitud key={a.id} a={a} onRespondida={() => {}} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </>
  );
}
