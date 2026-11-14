import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { obtenerCiudad } from "../../api";
import { Trophy } from "lucide-react";
import Alert from "../ui/Alert";
import Spinner from "../ui/Spinner";
import { ICONO_INSIGNIA } from "./insignias";

// Three.js pesa: se carga solo cuando se abre la ciudad.
const CiudadObras = lazy(() => import("./CiudadObras"));

/** Ciudad MinutoDesk: las obras del Top 5 (del mes o históricas) y, si no está ahí, la propia. */
export default function SeccionCiudad() {
  const [periodo, setPeriodo] = useState("mes");
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setDatos(null);
    obtenerCiudad(periodo)
      .then(setDatos)
      .catch((e) => setError(e.message));
  }, [periodo]);

  const lotes = useMemo(() => {
    if (!datos) return [];
    // Primero el Top 5 (con nombre), luego la obra propia y al final las demás, anónimas.
    const top = datos.top;
    const propia = datos.yo && !top.some((l) => l.es_yo) ? [datos.yo] : [];
    return [...top, ...propia, ...datos.vecinos];
  }, [datos]);

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold text-noche">Ciudad MinutoDesk</h2>
          <p className="text-sm text-gray-500">
            Cada persona tiene su obra en la ciudad. Con nombre aparece el Top 5{" "}
            {periodo === "mes" ? "de este mes" : "de siempre"}; las demás son de compañeros.
          </p>
        </div>
        <div className="flex gap-1 rounded-lg border border-linea bg-superficie p-1 text-sm" role="tablist">
          {[
            ["mes", "Este mes"],
            ["total", "Histórico"],
          ].map(([v, t]) => (
            <button
              key={v}
              role="tab"
              aria-selected={periodo === v}
              onClick={() => setPeriodo(v)}
              className={`rounded-md px-3 py-1 ${periodo === v ? "bg-grafito text-white" : "text-gray-600 hover:bg-marfil"}`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {error && <Alert variant="danger">{error}</Alert>}
      {!datos && !error && <Spinner size="sm" />}
      {datos && lotes.length === 0 && (
        <Alert variant="secondary">Todavía nadie suma puntos este mes. ¡La primera obra puede ser la tuya!</Alert>
      )}
      {datos && lotes.length > 0 && (
        <>
          <Suspense
            fallback={
              <div className="flex h-[440px] items-center justify-center rounded-xl bg-sky-50 text-sm text-gray-500">
                Levantando la ciudad…
              </div>
            }
          >
            <CiudadObras lotes={lotes} />
          </Suspense>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
            {lotes.filter((l) => !l.anonimo).map((l) => (
              <div
                key={`${l.posicion}-${l.nombre}`}
                className={`rounded-xl border bg-superficie p-2.5 text-sm ${l.es_yo ? "border-acento ring-2 ring-acento/30" : "border-linea"}`}
              >
                <div className="text-xs text-gray-500">#{l.posicion}</div>
                <div className="truncate font-semibold text-noche">
                  {l.posicion === 1 && <Trophy size={13} className="mr-1 inline-block -translate-y-px text-amber-600" aria-label="Primer lugar" />}
                  {l.es_yo ? "Tú" : l.nombre}
                </div>
                <div className="text-xs text-gray-600">{l.etapa}</div>
                <div className="text-xs text-gray-600">
                  {periodo === "mes" ? `${l.puntos_periodo} pts este mes` : `${l.puntos} pts`} · {l.pisos} pisos
                </div>
                <div className="mt-1 flex gap-1 text-gray-500">
                  {l.insignias.map((i) => {
                    const IconoInsignia = ICONO_INSIGNIA[i];
                    return IconoInsignia ? <IconoInsignia key={i} size={14} aria-hidden="true" /> : null;
                  })}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
