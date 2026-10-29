import { Building2 } from "lucide-react";
import { useEffect, useState } from "react";
import { obtenerGamificacion } from "../../api";
import { obtenerUsuario } from "../../auth";
import { ICONO_INSIGNIA } from "../../components/obra/insignias";
import SeccionCiudad from "../../components/obra/SeccionCiudad";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";

const ETAPAS = ["Cimientos", "Estructura", "Acabados", "Entrega de llaves"];
const ICONO_ETAPA = ["🏗️", "🧱", "🪟", "🔑"];
const INICIO_ETAPA = [0, 50, 150, 300];

/** «Mi obra»: la etapa de la obra propia, sus insignias y la ciudad con el Top 5. */
export default function GamificacionPage() {
  const usuario = obtenerUsuario();
  const [detalle, setDetalle] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerGamificacion(usuario.id)
      .then(setDetalle)
      .catch((e) => setError(e.message));
  }, [usuario.id]);

  const i = detalle ? detalle.numero_etapa - 1 : 0;
  const avance = detalle?.siguiente_etapa
    ? Math.round((100 * (detalle.puntos - INICIO_ETAPA[i])) / (INICIO_ETAPA[i + 1] - INICIO_ETAPA[i]))
    : 100;

  return (
    <>
      <PageHeader
        icon={Building2}
        title="Mi obra"
        subtitle="Cada consulta que resuelves con Minutito suma puntos y sube un piso de tu edificio."
      />
      {error && <Alert variant="danger">{error}</Alert>}
      {!detalle && !error && <Spinner size="sm" />}
      {detalle && (
        <div className="space-y-6">
          <div className="grid gap-3 lg:grid-cols-3">
            <Card>
              <Card.Body>
                <div className="text-sm text-gray-500">Tu obra está en</div>
                <div className="mt-1 text-2xl font-semibold text-noche">
                  {ICONO_ETAPA[i]} {detalle.nivel}
                </div>
                <div className="mt-1 text-sm text-gray-600">
                  {detalle.puntos} puntos · {detalle.pisos} pisos
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-gray-100">
                  <div className="h-full rounded-full bg-acento transition-all" style={{ width: `${avance}%` }} />
                </div>
                <p className="mt-1.5 text-xs text-gray-500">
                  {detalle.siguiente_etapa
                    ? `Te faltan ${detalle.puntos_para_siguiente} puntos para ${detalle.siguiente_etapa}.`
                    : "¡Obra entregada! Eres experta/o en autoservicio."}
                </p>
                <div className="mt-3 flex gap-1">
                  {ETAPAS.map((e, k) => (
                    <span
                      key={e}
                      title={e}
                      className={`flex-1 rounded-md py-1 text-center text-sm ${k <= i ? "bg-acento-50" : "bg-gray-50 opacity-40"}`}
                    >
                      {ICONO_ETAPA[k]}
                    </span>
                  ))}
                </div>
              </Card.Body>
            </Card>
            <Card className="lg:col-span-2">
              <Card.Body>
                <h2 className="mb-2 text-sm font-semibold text-noche">Insignias</h2>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {detalle.insignias.map((ins) => (
                    <div
                      key={ins.clave}
                      className={`rounded-xl border p-3 text-center ${ins.obtenida ? "border-acento/40 bg-acento-50/40" : "border-linea opacity-50 grayscale"}`}
                    >
                      <div className="text-2xl">{ICONO_INSIGNIA[ins.clave]}</div>
                      <div className="mt-1 text-sm font-semibold text-noche">{ins.nombre}</div>
                      <div className="text-xs text-gray-500">{ins.descripcion}</div>
                      {!ins.obtenida && <Badge className="mt-1">Por desbloquear</Badge>}
                    </div>
                  ))}
                </div>
              </Card.Body>
            </Card>
          </div>

          <SeccionCiudad />

          <Card>
            <Card.Body>
              <h2 className="mb-2 text-sm font-semibold text-noche">Cómo ganaste tus puntos</h2>
              {detalle.historial.length === 0 ? (
                <Alert variant="secondary">
                  Todavía no tienes puntos. Pregúntale a Minutito y, si te resuelve, confírmalo: ¡es tu primera piedra!
                </Alert>
              ) : (
                detalle.historial.map((e) => (
                  <div key={e.id} className="flex items-center justify-between gap-3 border-b border-gray-100 py-2 last:border-b-0">
                    <div className="min-w-0 text-sm">
                      <div>{e.motivo}</div>
                      <small className="text-gray-500">
                        {e.ticket_id ? `Ticket #${e.ticket_id} · ` : ""}
                        {new Date(e.creado_en).toLocaleString()}
                      </small>
                    </div>
                    <Badge color="green" className="shrink-0">
                      +{e.puntos_otorgados}
                    </Badge>
                  </div>
                ))
              )}
            </Card.Body>
          </Card>
        </div>
      )}
    </>
  );
}
