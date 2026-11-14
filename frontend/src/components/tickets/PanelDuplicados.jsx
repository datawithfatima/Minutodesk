import { Link2, Link2Off, Search } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { posiblesDuplicados, quitarVinculo, vincularDuplicado } from "../../api";
import Button from "../ui/Button";

/*
 * Duplicados (solo personal): muestra si el ticket está unido a otro, busca tickets
 * abiertos parecidos y lo marca como duplicado de uno de ellos. Al marcarlo se cancela
 * con el motivo «Duplicado del ticket #X» y la atención sigue en el principal.
 */
export default function PanelDuplicados({ ticket, onCambio }) {
  const [sugeridos, setSugeridos] = useState(null);
  const [numero, setNumero] = useState("");
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState(null);
  const cerrado = ticket.estado === "resuelto" || ticket.estado === "cancelado";

  async function accion(funcion) {
    setTrabajando(true);
    setError(null);
    try {
      await funcion();
      await onCambio();
    } catch (e) {
      setError(e.message);
    } finally {
      setTrabajando(false);
    }
  }

  function marcar(principalId) {
    if (!window.confirm(`El ticket #${ticket.id} quedará cancelado como duplicado del #${principalId}. ¿Continuar?`)) return;
    accion(() => vincularDuplicado(ticket.id, principalId, true));
  }

  async function buscar() {
    setError(null);
    try {
      setSugeridos(await posiblesDuplicados(ticket.id));
    } catch (e) {
      setError(e.message);
    }
  }

  if (ticket.duplicado_de_id) {
    return (
      <div className="space-y-3 text-sm">
        <p className="text-gray-700">
          Es duplicado del{" "}
          <Link to={`../${ticket.duplicado_de_id}`} relative="path" className="font-semibold text-acento hover:underline">
            ticket #{ticket.duplicado_de_id}
          </Link>
          : la atención sigue allí.
        </p>
        <Button size="sm" variant="outlineSecondary" disabled={trabajando} onClick={() => accion(() => quitarVinculo(ticket.id))}>
          <Link2Off size={14} aria-hidden="true" /> Quitar vínculo
        </Button>
        {ticket.estado === "cancelado" && (
          <p className="text-xs text-gray-500">Si fue un error, quita el vínculo y reabre el ticket desde «Gestión».</p>
        )}
        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>
    );
  }

  return (
    <div className="space-y-3 text-sm">
      {ticket.duplicados?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500">Tickets unidos a este como duplicados</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {ticket.duplicados.map((d) => (
              <Link
                key={d}
                to={`../${d}`}
                relative="path"
                className="rounded-[4px] border border-linea bg-gray-50 px-2 py-0.5 font-mono text-xs text-noche hover:border-acento hover:text-acento"
              >
                #{d}
              </Link>
            ))}
          </div>
        </div>
      )}

      {!cerrado && !ticket.duplicados?.length && (
        <>
          {sugeridos === null ? (
            <Button size="sm" variant="outlineSecondary" onClick={buscar}>
              <Search size={14} aria-hidden="true" /> Buscar tickets parecidos
            </Button>
          ) : sugeridos.length === 0 ? (
            <p className="text-gray-500">No hay tickets abiertos parecidos en los últimos 30 días.</p>
          ) : (
            <ul className="space-y-2">
              {sugeridos.map((s) => (
                <li key={s.id} className="rounded-md border border-dashed border-linea p-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <Link to={`../${s.id}`} relative="path" className="font-mono text-xs font-semibold text-acento hover:underline">
                      #{s.id}
                    </Link>
                    <span className="font-mono text-[10.5px] text-gray-500">
                      {Math.round(s.similitud * 100)}% parecido · {s.categoria || "Sin categoría"}
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs text-gray-700">{s.texto}</p>
                  <button
                    type="button"
                    disabled={trabajando}
                    onClick={() => marcar(s.id)}
                    className="mt-1.5 text-xs font-semibold text-acento hover:underline disabled:opacity-50"
                  >
                    Marcar este ticket como duplicado del #{s.id}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (Number(numero) > 0) marcar(Number(numero));
            }}
            className="flex items-center gap-1.5"
          >
            <label className="sr-only" htmlFor={`principal-${ticket.id}`}>
              Número del ticket principal
            </label>
            <span className="text-xs text-gray-500">Duplicado del #</span>
            <input
              id={`principal-${ticket.id}`}
              inputMode="numeric"
              value={numero}
              onChange={(e) => setNumero(e.target.value.replace(/\D/g, ""))}
              placeholder="123"
              className="campo-obra h-8 w-20 rounded-md border border-linea bg-superficie px-2 font-mono text-sm text-noche"
            />
            <Button type="submit" size="sm" variant="outlinePrimary" disabled={!numero || trabajando}>
              <Link2 size={14} aria-hidden="true" /> Unir
            </Button>
          </form>
        </>
      )}
      {cerrado && !ticket.duplicados?.length && <p className="text-gray-500">El ticket está cerrado.</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
