import { Megaphone, Unlink, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { incidenteSugerido, listarAfectados, separarAfectado, unirAfectados } from "../../api";
import EstadoBadge from "../EstadoBadge";
import Button from "../ui/Button";

/*
 * Varios usuarios con el mismo problema (solo personal): este ticket es el principal y los
 * demás quedan como afectados. Solo se trabaja el principal; al resolverlo, los afectados
 * se cierran con él y se avisa a cada persona. Si hay 3 o más personas con un problema
 * parecido en las últimas 48 h, se sugiere unirlos.
 */
export default function PanelIncidente({ ticket, onCambio }) {
  const [afectados, setAfectados] = useState([]);
  const [sugeridos, setSugeridos] = useState([]);
  const [elegidos, setElegidos] = useState(new Set());
  const [numero, setNumero] = useState("");
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState(null);
  const cerrado = ticket.estado === "resuelto" || ticket.estado === "cancelado";

  const cargar = useCallback(async () => {
    const [a, s] = await Promise.all([listarAfectados(ticket.id), cerrado ? [] : incidenteSugerido(ticket.id)]);
    setAfectados(a);
    setSugeridos(s);
    setElegidos(new Set(s.map((x) => x.id)));
  }, [ticket.id, cerrado]);

  useEffect(() => {
    cargar().catch(() => {});
  }, [cargar]);

  async function accion(funcion) {
    setTrabajando(true);
    setError(null);
    try {
      await funcion();
      await cargar();
      await onCambio?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setTrabajando(false);
    }
  }

  function unir(ids) {
    if (!ids.length) return;
    const lista = ids.map((i) => `#${i}`).join(", ");
    if (!window.confirm(`${lista} quedará${ids.length > 1 ? "n" : ""} como afectado${ids.length > 1 ? "s" : ""} de este ticket: su plazo se pausa y se cerrará${ids.length > 1 ? "n" : ""} cuando resuelvas este. ¿Continuar?`)) return;
    accion(async () => {
      await unirAfectados(ticket.id, ids);
      setNumero("");
    });
  }

  const alternar = (id) =>
    setElegidos((actual) => {
      const nuevo = new Set(actual);
      nuevo.has(id) ? nuevo.delete(id) : nuevo.add(id);
      return nuevo;
    });

  const abiertos = afectados.filter((a) => a.estado !== "resuelto" && a.estado !== "cancelado").length;

  return (
    <div className="space-y-3 text-sm">
      {sugeridos.length > 0 && (
        <div className="anim-desplegar relative overflow-hidden rounded-md border border-amber-200 bg-amber-50 pl-1.5 text-amber-900">
          <span aria-hidden="true" className="franja-obra absolute inset-y-0 left-0 w-1.5" />
          <div className="p-3">
            <p className="flex items-start gap-2 font-semibold">
              <Megaphone size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
              {sugeridos.length} {sugeridos.length === 1 ? "persona más reporta" : "personas más reportan"} algo parecido en las últimas 48 h
            </p>
            <p className="mt-0.5 text-xs text-amber-800">
              Únelos a este ticket para resolverlo una sola vez: se cierran con él y se avisa a cada persona.
            </p>
            <ul className="mt-2 space-y-1.5">
              {sugeridos.map((s) => (
                <li key={s.id} className="rounded-md border border-amber-200 bg-superficie p-2">
                  <label className="flex cursor-pointer items-start gap-2">
                    <input
                      type="checkbox"
                      checked={elegidos.has(s.id)}
                      onChange={() => alternar(s.id)}
                      className="mt-0.5 h-4 w-4 accent-[var(--color-acento)]"
                    />
                    <span className="min-w-0">
                      <span className="flex flex-wrap items-center gap-x-2 text-xs">
                        <Link to={`../${s.id}`} relative="path" className="font-mono font-semibold text-acento hover:underline">
                          #{s.id}
                        </Link>
                        <span className="text-gray-700">{s.solicitante}</span>
                        <span className="font-mono text-[10.5px] text-gray-500">{Math.round(s.similitud * 100)}% parecido</span>
                      </span>
                      <span className="mt-0.5 line-clamp-2 block text-xs text-gray-600">{s.texto}</span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
            <Button
              size="sm"
              variant="dark"
              className="mt-2"
              disabled={trabajando || elegidos.size === 0}
              onClick={() => unir([...elegidos])}
            >
              <Users size={14} aria-hidden="true" /> Unir {elegidos.size} como afectados
            </Button>
          </div>
        </div>
      )}

      {afectados.length > 0 && (
        <div>
          <p className="text-xs text-gray-500">
            Ticket principal · {afectados.length} {afectados.length === 1 ? "ticket unido" : "tickets unidos"}
            {abiertos > 0 && ` (${abiertos} se ${abiertos === 1 ? "cerrará" : "cerrarán"} al resolver este)`}
          </p>
          <ul className="mt-1.5 divide-y divide-dashed divide-linea rounded-md border border-linea">
            {afectados.map((a) => {
              const abierto = a.estado !== "resuelto" && a.estado !== "cancelado";
              return (
                <li key={a.id} className="flex items-center justify-between gap-2 px-2.5 py-1.5">
                  <span className="flex min-w-0 items-center gap-2">
                    <Link to={`../${a.id}`} relative="path" className="font-mono text-xs font-semibold text-acento hover:underline">
                      #{a.id}
                    </Link>
                    <span className="truncate text-xs text-gray-700">{a.solicitante}</span>
                  </span>
                  <span className="flex shrink-0 items-center gap-1.5">
                    <EstadoBadge estado={a.estado} />
                    {abierto && (
                      <button
                        type="button"
                        title={`Separar #${a.id}: vuelve a atenderse por su cuenta`}
                        aria-label={`Separar el ticket #${a.id}`}
                        disabled={trabajando}
                        onClick={() => accion(() => separarAfectado(a.id))}
                        className="btn-obra rounded p-1 text-gray-500 hover:bg-marfil hover:text-noche disabled:opacity-40"
                      >
                        <Unlink size={14} aria-hidden="true" />
                      </button>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {!cerrado && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (Number(numero) > 0) unir([Number(numero)]);
          }}
          className="flex flex-wrap items-center gap-1.5"
        >
          <label className="text-xs text-gray-500" htmlFor={`afectado-${ticket.id}`}>
            Unir como afectado el #
          </label>
          <input
            id={`afectado-${ticket.id}`}
            inputMode="numeric"
            value={numero}
            onChange={(e) => setNumero(e.target.value.replace(/\D/g, ""))}
            placeholder="123"
            className="campo-obra h-8 w-20 rounded-md border border-linea bg-superficie px-2 font-mono text-sm text-noche"
          />
          <Button type="submit" size="sm" variant="outlinePrimary" disabled={!numero || trabajando}>
            <Users size={14} aria-hidden="true" /> Unir
          </Button>
        </form>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
