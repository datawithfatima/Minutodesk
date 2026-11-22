import { BookmarkPlus, MessageSquareText, Search, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { crearPredefinida, eliminarPredefinida, listarPredefinidas, usarPredefinida } from "../../api";

/*
 * Respuestas predefinidas del personal: un panel desplegable junto al chat del ticket.
 * Elegir una pone el texto (ya con el nombre del usuario y el número de ticket) en la
 * caja del mensaje para revisarlo antes de enviar; nunca se envía sola.
 */
export default function RespuestasPredefinidas({ ticketId, textoActual, onInsertar }) {
  const [abierto, setAbierto] = useState(false);
  const [lista, setLista] = useState(null);
  const [filtro, setFiltro] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [titulo, setTitulo] = useState("");
  const [error, setError] = useState(null);
  const caja = useRef(null);

  useEffect(() => {
    if (!abierto) return;
    listarPredefinidas()
      .then(setLista)
      .catch((e) => setError(e.message));
    const cerrarFuera = (e) => caja.current && !caja.current.contains(e.target) && setAbierto(false);
    const cerrarEsc = (e) => e.key === "Escape" && setAbierto(false);
    document.addEventListener("mousedown", cerrarFuera);
    document.addEventListener("keydown", cerrarEsc);
    return () => {
      document.removeEventListener("mousedown", cerrarFuera);
      document.removeEventListener("keydown", cerrarEsc);
    };
  }, [abierto]);

  async function elegir(p) {
    setError(null);
    try {
      const { texto } = await usarPredefinida(ticketId, p.id);
      onInsertar(texto);
      setAbierto(false);
    } catch (e) {
      setError(e.message);
    }
  }

  async function guardarActual(e) {
    e.preventDefault();
    setError(null);
    try {
      const nueva = await crearPredefinida({ titulo, texto: textoActual });
      setLista((l) => [...(l || []), nueva]);
      setGuardando(false);
      setTitulo("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function borrar(p) {
    if (!window.confirm(`¿Eliminar la respuesta «${p.titulo}»?`)) return;
    try {
      await eliminarPredefinida(p.id);
      setLista((l) => l.filter((x) => x.id !== p.id));
    } catch (e) {
      setError(e.message);
    }
  }

  const q = filtro.trim().toLowerCase();
  const visibles = (lista || []).filter((p) => !q || p.titulo.toLowerCase().includes(q) || p.texto.toLowerCase().includes(q));

  return (
    <div className="relative" ref={caja}>
      <button
        type="button"
        onClick={() => setAbierto((a) => !a)}
        aria-expanded={abierto}
        className="btn-obra inline-flex h-8 items-center gap-1.5 rounded-md border border-linea bg-superficie px-2.5 text-xs font-semibold text-noche hover:border-noche/40"
      >
        <MessageSquareText size={14} aria-hidden="true" className="text-acento" />
        Respuestas predefinidas
      </button>

      {abierto && (
        <div className="anim-desplegar absolute bottom-full left-0 z-30 mb-2 w-[min(26rem,calc(100vw-2.5rem))] overflow-hidden rounded-lg border border-linea bg-superficie shadow-[0_10px_30px_rgb(0_0_0/0.18)]">
          <div className="flex items-center justify-between bg-grafito px-3 py-2 text-white">
            <span className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-casco">Respuestas predefinidas</span>
            <button type="button" onClick={() => setAbierto(false)} aria-label="Cerrar" className="rounded p-1 text-white/60 hover:text-white">
              <X size={15} />
            </button>
          </div>
          <div className="border-b border-linea p-2">
            <label className="relative block">
              <span className="sr-only">Buscar respuesta</span>
              <Search size={14} aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                autoFocus
                value={filtro}
                onChange={(e) => setFiltro(e.target.value)}
                placeholder="Buscar…"
                className="campo-obra h-8 w-full rounded-md border border-linea bg-superficie pl-8 pr-2 text-sm text-noche placeholder:text-gray-400"
              />
            </label>
          </div>
          <ul className="max-h-64 divide-y divide-dashed divide-linea overflow-y-auto">
            {lista === null && <li className="px-3 py-3 text-sm text-gray-500">Cargando…</li>}
            {lista && visibles.length === 0 && <li className="px-3 py-3 text-sm text-gray-500">No hay respuestas que coincidan.</li>}
            {visibles.map((p) => (
              <li key={p.id} className="group flex items-start gap-1 hover:bg-marfil">
                <button type="button" onClick={() => elegir(p)} className="min-w-0 flex-1 px-3 py-2 text-left">
                  <span className="flex items-center gap-2">
                    <span className="truncate text-sm font-semibold text-noche">{p.titulo}</span>
                    {p.usos > 0 && <span className="shrink-0 font-mono text-[10px] text-gray-500">{p.usos} usos</span>}
                  </span>
                  <span className="mt-0.5 line-clamp-2 block text-xs text-gray-600">{p.texto}</span>
                </button>
                {p.editable && (
                  <button
                    type="button"
                    onClick={() => borrar(p)}
                    aria-label={`Eliminar ${p.titulo}`}
                    className="m-1.5 rounded p-1.5 text-gray-400 opacity-0 hover:bg-red-50 hover:text-red-600 focus:opacity-100 group-hover:opacity-100"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </li>
            ))}
          </ul>
          <div className="border-t border-linea bg-gray-50 p-2">
            {guardando ? (
              <form onSubmit={guardarActual} className="flex gap-1.5">
                <input
                  autoFocus
                  value={titulo}
                  onChange={(e) => setTitulo(e.target.value)}
                  maxLength={80}
                  placeholder="Título, p. ej. «Pedir número de serie»"
                  className="campo-obra h-8 min-w-0 flex-1 rounded-md border border-linea bg-superficie px-2 text-sm text-noche placeholder:text-gray-400"
                />
                <button type="submit" disabled={titulo.trim().length < 3} className="btn-obra h-8 rounded-md bg-acento px-3 text-xs font-semibold text-white disabled:opacity-50">
                  Guardar
                </button>
              </form>
            ) : (
              <button
                type="button"
                disabled={textoActual.trim().length < 5}
                onClick={() => setGuardando(true)}
                title={textoActual.trim().length < 5 ? "Escribe primero el mensaje en el chat" : undefined}
                className="flex w-full items-center gap-2 rounded px-1.5 py-1 text-xs font-semibold text-acento hover:underline disabled:cursor-not-allowed disabled:text-gray-400 disabled:no-underline"
              >
                <BookmarkPlus size={14} aria-hidden="true" />
                Guardar el mensaje que estás escribiendo como respuesta
              </button>
            )}
            <p className="mt-1 px-1.5 text-[11px] text-gray-500">
              Variables: {"{nombre}"}, {"{ticket}"}, {"{tecnico}"}
            </p>
            {error && <p className="mt-1 px-1.5 text-xs text-red-600">{error}</p>}
          </div>
        </div>
      )}
    </div>
  );
}
