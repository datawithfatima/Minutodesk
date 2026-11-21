import { Check, ChevronDown } from "lucide-react";
import { Children, isValidElement, useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

/*
 * Lista desplegable con el estilo del portal (reemplaza a <select>, cuya lista abierta la
 * dibuja el sistema operativo y no se puede diseñar). Se usa igual que un <select>:
 * mismas <option> como hijas, mismo `value` y el mismo `onChange(e)` con `e.target.value`,
 * así que cambiar uno por otro no toca la lógica de cada pantalla.
 *
 * Teclado como en un <select>: flechas, Inicio/Fin, Enter o Espacio para elegir, Esc para
 * cerrar y escribir para saltar a una opción. La lista se dibuja en un portal con posición
 * fija, para que ningún panel con overflow la recorte.
 */

function textoDe(nodo) {
  if (nodo == null || typeof nodo === "boolean") return "";
  if (typeof nodo === "string" || typeof nodo === "number") return String(nodo);
  if (Array.isArray(nodo)) return nodo.map(textoDe).join("");
  if (isValidElement(nodo)) return textoDe(nodo.props.children);
  return "";
}

function opcionesDe(children) {
  const lista = [];
  Children.forEach(children, (hijo) => {
    if (!isValidElement(hijo)) return;
    if (hijo.type === "option") {
      const etiqueta = textoDe(hijo.props.children);
      lista.push({
        valor: String(hijo.props.value ?? etiqueta),
        etiqueta,
        deshabilitada: Boolean(hijo.props.disabled),
      });
    } else if (hijo.props?.children) {
      lista.push(...opcionesDe(hijo.props.children)); // fragmentos
    }
  });
  return lista;
}

const MARGEN = 6;
const ALTO_MAXIMO = 288;

export default function Selector({
  value,
  onChange,
  children,
  className = "",
  disabled = false,
  required = false,
  id,
  name,
  "aria-label": ariaLabel,
  "aria-describedby": ariaDescribedby,
}) {
  const opciones = useMemo(() => opcionesDe(children), [children]);
  const valor = value == null ? "" : String(value);
  const elegida = opciones.find((o) => o.valor === valor) ?? opciones[0];
  const [abierta, setAbierta] = useState(false);
  const [activa, setActiva] = useState(-1);
  const [posicion, setPosicion] = useState(null);
  const boton = useRef(null);
  const lista = useRef(null);
  const busqueda = useRef({ texto: "", hasta: 0 });
  const idLista = useId();

  const habilitadas = opciones.map((o, i) => (o.deshabilitada ? -1 : i)).filter((i) => i >= 0);

  function ubicar() {
    const r = boton.current?.getBoundingClientRect();
    if (!r) return;
    const abajo = window.innerHeight - r.bottom - MARGEN;
    const arriba = r.top - MARGEN;
    const haciaArriba = abajo < Math.min(ALTO_MAXIMO, 200) && arriba > abajo;
    setPosicion({
      izquierda: Math.max(8, Math.min(r.left, window.innerWidth - Math.max(r.width, 200) - 8)),
      ancho: Math.max(r.width, 200),
      alto: Math.min(ALTO_MAXIMO, (haciaArriba ? arriba : abajo) - 4),
      ...(haciaArriba ? { abajo: window.innerHeight - r.top + 4 } : { arriba: r.bottom + 4 }),
    });
  }

  function abrir() {
    if (disabled) return;
    ubicar();
    setActiva(Math.max(0, opciones.indexOf(elegida)));
    setAbierta(true);
  }

  function cerrar(devolverFoco = true) {
    setAbierta(false);
    if (devolverFoco) boton.current?.focus();
  }

  function elegir(i) {
    const o = opciones[i];
    if (!o || o.deshabilitada) return;
    cerrar();
    if (o.valor !== valor) onChange?.({ target: { value: o.valor, name, id }, currentTarget: { value: o.valor } });
  }

  function mover(desde, paso) {
    if (!habilitadas.length) return desde;
    const pos = habilitadas.indexOf(desde);
    if (pos === -1) return paso > 0 ? habilitadas[0] : habilitadas[habilitadas.length - 1];
    return habilitadas[Math.min(habilitadas.length - 1, Math.max(0, pos + paso))];
  }

  function buscar(tecla) {
    const ahora = Date.now();
    const b = busqueda.current;
    b.texto = (ahora < b.hasta ? b.texto : "") + tecla.toLowerCase();
    b.hasta = ahora + 700;
    const normal = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    const encontrada = opciones.findIndex((o) => !o.deshabilitada && normal(o.etiqueta).startsWith(normal(b.texto)));
    return encontrada;
  }

  function alTeclear(e) {
    if (disabled) return;
    const { key } = e;
    if (!abierta) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(key)) {
        e.preventDefault();
        abrir();
      } else if (key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const i = buscar(key);
        if (i >= 0) elegir(i);
      }
      return;
    }
    if (key === "Escape") {
      e.preventDefault();
      cerrar();
    } else if (key === "Tab") {
      cerrar(false);
    } else if (key === "ArrowDown" || key === "ArrowUp") {
      e.preventDefault();
      setActiva((a) => mover(a, key === "ArrowDown" ? 1 : -1));
    } else if (key === "Home" || key === "End" || key === "PageUp" || key === "PageDown") {
      e.preventDefault();
      setActiva(key === "Home" || key === "PageUp" ? habilitadas[0] : habilitadas[habilitadas.length - 1]);
    } else if (key === "Enter" || key === " ") {
      e.preventDefault();
      elegir(activa);
    } else if (key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const i = buscar(key);
      if (i >= 0) setActiva(i);
    }
  }

  // Cerrar al hacer clic fuera; reubicar si la página se desplaza o cambia de tamaño.
  useEffect(() => {
    if (!abierta) return undefined;
    const fuera = (e) => {
      if (!boton.current?.contains(e.target) && !lista.current?.contains(e.target)) cerrar(false);
    };
    const alMover = (e) => {
      if (lista.current?.contains(e.target)) return;
      ubicar();
    };
    document.addEventListener("mousedown", fuera);
    window.addEventListener("scroll", alMover, true);
    window.addEventListener("resize", ubicar);
    return () => {
      document.removeEventListener("mousedown", fuera);
      window.removeEventListener("scroll", alMover, true);
      window.removeEventListener("resize", ubicar);
    };
  }, [abierta]); // eslint-disable-line react-hooks/exhaustive-deps

  // Mantener visible la opción activa al moverse con el teclado.
  useLayoutEffect(() => {
    if (abierta && activa >= 0) lista.current?.querySelector(`[data-indice="${activa}"]`)?.scrollIntoView({ block: "nearest" });
  }, [abierta, activa]);

  const vacia = !elegida || elegida.valor === "";

  return (
    <>
      <button
        ref={boton}
        id={id}
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={abierta}
        aria-controls={abierta ? idLista : undefined}
        aria-activedescendant={abierta && activa >= 0 ? `${idLista}-${activa}` : undefined}
        aria-label={ariaLabel}
        aria-describedby={ariaDescribedby}
        onClick={() => (abierta ? cerrar() : abrir())}
        onKeyDown={alTeclear}
        className={`${className} flex items-center justify-between gap-2 text-left disabled:cursor-not-allowed ${
          abierta ? "border-acento ring-3 ring-acento/15" : ""
        }`}
      >
        <span className={`min-w-0 truncate ${vacia ? "text-gray-500" : ""}`}>{elegida?.etiqueta ?? ""}</span>
        <ChevronDown
          size={16}
          aria-hidden="true"
          className={`shrink-0 text-gray-500 transition-transform duration-200 ${abierta ? "rotate-180 text-acento" : ""}`}
        />
      </button>
      {required && (
        // Para que el formulario siga exigiendo un valor, como con <select required>.
        <input
          tabIndex={-1}
          aria-hidden="true"
          required
          value={valor}
          onChange={() => {}}
          onFocus={() => boton.current?.focus()}
          className="sr-only"
        />
      )}
      {abierta &&
        posicion &&
        createPortal(
          <div
            className="anim-desplegar fixed z-[60] overflow-hidden rounded-md border border-linea bg-superficie shadow-[0_16px_32px_-12px_rgb(27_30_34/0.35)]"
            style={{
              left: posicion.izquierda,
              width: posicion.ancho,
              top: posicion.arriba,
              bottom: posicion.abajo,
            }}
          >
            <div className="franja-obra h-[3px]" aria-hidden="true" />
            <ul
              ref={lista}
              id={idLista}
              role="listbox"
              aria-labelledby={id}
              className="overflow-y-auto overscroll-contain py-1"
              style={{ maxHeight: posicion.alto }}
            >
              {opciones.map((o, i) => {
                const seleccionada = o === elegida;
                const marcada = i === activa;
                return (
                  <li
                    key={`${o.valor}-${i}`}
                    id={`${idLista}-${i}`}
                    data-indice={i}
                    role="option"
                    aria-selected={seleccionada}
                    aria-disabled={o.deshabilitada || undefined}
                    onMouseEnter={() => !o.deshabilitada && setActiva(i)}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => elegir(i)}
                    className={`relative flex cursor-pointer items-center gap-2 py-2 pl-4 pr-3 text-sm transition-colors ${
                      o.deshabilitada ? "cursor-not-allowed text-gray-400" : seleccionada ? "font-semibold text-noche" : "text-gray-700"
                    } ${marcada && !o.deshabilitada ? "bg-marfil" : ""}`}
                  >
                    {seleccionada && <span aria-hidden="true" className="absolute inset-y-1.5 left-0 w-[3px] rounded-r bg-acento" />}
                    <span className="min-w-0 flex-1 truncate" title={o.etiqueta}>
                      {o.etiqueta}
                    </span>
                    {seleccionada && <Check size={15} aria-hidden="true" className="shrink-0 text-acento" />}
                  </li>
                );
              })}
            </ul>
          </div>,
          document.body,
        )}
    </>
  );
}
