import { useCallback, useEffect, useState } from "react";
import { obtenerSimulacionTiempos } from "../../api";
import Alert from "../../components/ui/Alert";
import Badge from "../../components/ui/Badge";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import { inputClass } from "../../components/ui/formStyles";

function dias(valor) {
  return valor == null ? "—" : `${valor.toLocaleString(undefined, { maximumFractionDigits: 2 })} días`;
}

function Cifra({ titulo, valor, detalle, children }) {
  return (
    <Card>
      <Card.Body>
        <div className="text-sm font-medium text-gray-500">{titulo}</div>
        <div className="mt-1 flex flex-wrap items-baseline gap-2">
          <span className="text-3xl font-semibold tracking-tight text-noche">{valor}</span>
          {children}
        </div>
        {detalle && <p className="mt-1 text-sm text-gray-500">{detalle}</p>}
      </Card.Body>
    </Card>
  );
}

/** Objetivo 3: cuánto bajaría el tiempo de resolución si Minutito resolviera lo evaluado. */
export default function SimulacionTiempos() {
  const [minutos, setMinutos] = useState(15);
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);

  const cargar = useCallback(() => obtenerSimulacionTiempos(minutos).then(setDatos), [minutos]);
  useEffect(() => {
    cargar().catch((e) => setError(e.message));
  }, [cargar]);

  if (error) return <Alert variant="danger">{error}</Alert>;
  if (!datos) return <Spinner size="sm" />;

  const inc = datos.incidencias;
  const total = datos.muestra;
  const cumple = inc.muestra.reduccion != null && inc.muestra.reduccion >= datos.meta;
  const pct = (v) => (v == null ? "—" : `${Math.round(v * 1000) / 10}%`);
  const detalleMuestra = (m) =>
    `${m.tickets} tickets resueltos; Minutito habría resuelto ${m.resueltos_por_minutito}. ${
      m.sin_evaluar ? `Faltan ${m.sin_evaluar} por evaluar.` : "Todos evaluados."
    }`;

  return (
    <div className="space-y-4">
      <Alert variant="info">
        El objetivo 3 se mide en las <strong className="font-semibold">incidencias</strong> (algo dejó de funcionar),
        que es lo que Minutito atiende. Se toman las incidencias nuevas cargadas que ya se resolvieron: a las que, según
        la <strong className="font-semibold">Evaluación de Minutito</strong>, Minutito habría resuelto se les asigna el
        tiempo de una conversación; el resto conserva su tiempo real.
      </Alert>

      <h2 className="text-sm font-semibold text-noche">Incidencias (objetivo 3)</h2>
      <div className="grid gap-3 md:grid-cols-3">
        <Cifra
          titulo="Línea base: incidencias del histórico"
          valor={dias(inc.linea_base_historico.media_dias)}
          detalle={`Promedio de ${inc.linea_base_historico.tickets} incidencias completadas. En días hábiles: ${dias(
            inc.linea_base_historico.media_dias_habiles
          )}; mediana ${dias(inc.linea_base_historico.mediana_dias)}.`}
        />
        <Cifra
          titulo="Muestra: tiempo real → simulado"
          valor={`${dias(inc.muestra.media_real_dias)} → ${dias(inc.muestra.media_simulada_dias)}`}
          detalle={detalleMuestra(inc.muestra)}
        />
        <Cifra titulo="Reducción del tiempo promedio" valor={pct(inc.muestra.reduccion)}>
          {inc.muestra.reduccion != null && (
            <Badge color={cumple ? "green" : "amber"}>
              {cumple ? "Cumple" : "Por debajo de"} la meta de {Math.round(datos.meta * 100)}%
            </Badge>
          )}
        </Cifra>
      </div>

      <h2 className="pt-2 text-sm font-semibold text-noche">Todos los tickets (referencia)</h2>
      <div className="grid gap-3 md:grid-cols-3">
        <Cifra
          titulo="Línea base: histórico completo"
          valor={dias(datos.linea_base_historico.media_dias)}
          detalle={`Promedio de ${datos.linea_base_historico.tickets} tickets completados. En días hábiles: ${dias(
            datos.linea_base_historico.media_dias_habiles
          )}; mediana ${dias(datos.linea_base_historico.mediana_dias)}.`}
        />
        <Cifra
          titulo="Muestra: tiempo real → simulado"
          valor={`${dias(total.media_real_dias)} → ${dias(total.media_simulada_dias)}`}
          detalle={detalleMuestra(total)}
        />
        <Cifra
          titulo="Reducción del tiempo promedio"
          valor={pct(total.reduccion)}
          detalle={`Las incidencias son solo el ${pct(
            inc.parte_del_tiempo_total
          )} del tiempo total del histórico; las solicitudes y los accesos los atiende siempre el equipo, así que este es el techo de lo que Minutito puede reducir aquí.`}
        />
      </div>

      <Card>
        <Card.Body className="flex flex-wrap items-center gap-3 text-sm text-gray-600">
          <label htmlFor="minutos-minutito">Tiempo de una conversación con Minutito que resuelve:</label>
          <input
            id="minutos-minutito"
            type="number"
            min={1}
            max={1440}
            value={minutos}
            onChange={(e) => setMinutos(Math.max(1, Math.min(1440, Number(e.target.value) || 1)))}
            className={`${inputClass} w-24`}
          />
          <span>minutos (supuesto de la simulación).</span>
        </Card.Body>
      </Card>
    </div>
  );
}
