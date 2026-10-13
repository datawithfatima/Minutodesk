import { useCallback, useRef, useState } from "react";

/**
 * Tooltip compartido: un solo recuadro con todos los valores del punto señalado.
 * Los textos se insertan como texto de React (nunca como HTML), y también se muestra
 * al enfocar con el teclado. Uso:
 *   const tt = useTooltip();
 *   <div ref={tt.ref} className="relative"> ... {tt.capa} </div>
 *   tt.mostrar(evento, { titulo, filas: [{ color, etiqueta, valor }] })
 */
export function useTooltip() {
  const ref = useRef(null);
  const [tip, setTip] = useState(null);

  const mostrar = useCallback((evento, contenido) => {
    const caja = ref.current?.getBoundingClientRect();
    if (!caja) return;
    let x = evento.clientX;
    let y = evento.clientY;
    if (evento.type === "focus") {
      const r = evento.currentTarget.getBoundingClientRect();
      x = r.left + r.width / 2;
      y = r.top + Math.min(r.height / 2, 40);
    }
    const margen = 90; // ancho medio del recuadro, para que no se salga por los lados
    setTip({
      x: Math.min(Math.max(x - caja.left, margen), Math.max(caja.width - margen, margen)),
      y: y - caja.top,
      contenido,
    });
  }, []);

  const ocultar = useCallback(() => setTip(null), []);

  const capa = tip ? (
    <div
      role="tooltip"
      className="pointer-events-none absolute z-20 min-w-[130px] rounded-lg border border-linea bg-white px-3 py-2 text-xs shadow-lg"
      style={{ left: tip.x, top: tip.y, transform: "translate(-50%, calc(-100% - 12px))" }}
    >
      {tip.contenido.titulo && <div className="mb-1 text-gray-500">{tip.contenido.titulo}</div>}
      {tip.contenido.filas.map((f) => (
        <div key={f.etiqueta} className="flex items-center gap-2 py-0.5">
          <span className="inline-block h-0.5 w-3 shrink-0 rounded" style={{ background: f.color }} />
          <span className="text-sm font-semibold text-noche">{f.valor}</span>
          <span className="text-gray-500">{f.etiqueta}</span>
        </div>
      ))}
    </div>
  ) : null;

  return { ref, mostrar, ocultar, capa };
}
