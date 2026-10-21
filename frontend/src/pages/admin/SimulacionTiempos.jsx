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

  const { linea_base_historico: base, muestra } = datos;
  const cumple = muestra.reduccion != null && muestra.reduccion >= datos.meta;

  return (
    <div className="space-y-4">
      <Alert variant="info">
        Se toman los tickets nuevos cargados que ya se resolvieron. A los que, según la{" "}
        <strong className="font-semibold">Evaluación de Minutito</strong>, Minutito habría resuelto se les asigna el
        tiempo de una conversación; el resto conserva su tiempo real. Los que aún no evaluaste cuentan como no
        resueltos por Minutito.
      </Alert>

      <div className="grid gap-3 md:grid-cols-3">
        <Cifra
          titulo="Línea base: histórico"
          valor={dias(base.media_dias)}
          detalle={`Promedio de ${base.tickets} tickets completados (creación → fecha de solución). En días hábiles: ${dias(base.media_dias_habiles)}; mediana ${dias(base.mediana_dias)}.`}
        />
        <Cifra
          titulo="Muestra: tiempo real → simulado"
          valor={`${dias(muestra.media_real_dias)} → ${dias(muestra.media_simulada_dias)}`}
          detalle={`${muestra.tickets} tickets resueltos; Minutito habría resuelto ${muestra.resueltos_por_minutito}. ${
            muestra.sin_evaluar ? `Faltan ${muestra.sin_evaluar} por evaluar.` : "Todos evaluados."
          }`}
        />
        <Cifra
          titulo="Reducción del tiempo promedio"
          valor={muestra.reduccion == null ? "—" : `${Math.round(muestra.reduccion * 1000) / 10}%`}
        >
          {muestra.reduccion != null && (
            <Badge color={cumple ? "green" : "amber"}>
              {cumple ? "Cumple" : "Por debajo de"} la meta de {Math.round(datos.meta * 100)}%
            </Badge>
          )}
        </Cifra>
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
