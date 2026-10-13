import { ChevronDown, KeyRound, LogOut } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ETIQUETA_ROL } from "../texto";

/** Menú de la cuenta en la barra superior: quién eres, cambiar contraseña y cerrar sesión. */
export default function MenuUsuario({ usuario, onLogout }) {
  const [abierto, setAbierto] = useState(false);
  const contenedor = useRef(null);
  const boton = useRef(null);
  const primerItem = useRef(null);
  const conTeclado = useRef(false); // solo si se abrió con teclado se enfoca la primera opción

  const iniciales = (usuario?.nombre || "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();

  // Se cierra al hacer clic fuera o con Escape (y el foco vuelve al botón).
  useEffect(() => {
    if (!abierto) return undefined;
    if (conTeclado.current) primerItem.current?.focus();
    const alClic = (e) => !contenedor.current?.contains(e.target) && setAbierto(false);
    const alTeclear = (e) => {
      if (e.key === "Escape") {
        setAbierto(false);
        boton.current?.focus();
      }
    };
    document.addEventListener("mousedown", alClic);
    document.addEventListener("keydown", alTeclear);
    return () => {
      document.removeEventListener("mousedown", alClic);
      document.removeEventListener("keydown", alTeclear);
    };
  }, [abierto]);

  const item =
    "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors duration-150 focus-visible:outline-none";

  return (
    <div ref={contenedor} className="relative">
      <button
        ref={boton}
        type="button"
        onClick={(e) => {
          conTeclado.current = e.detail === 0;
          setAbierto((a) => !a);
        }}
        aria-haspopup="menu"
        aria-expanded={abierto}
        aria-label={`Cuenta de ${usuario?.nombre ?? "usuario"}`}
        className="flex min-w-0 items-center gap-2.5 rounded-xl p-1 pr-1.5 transition-colors duration-150 hover:bg-marfil sm:pr-2"
      >
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-noche text-xs font-semibold text-white">
          {iniciales}
        </span>
        <span className="hidden min-w-0 text-left sm:block">
          <span className="block max-w-[160px] truncate text-sm font-medium leading-tight text-noche">
            {usuario?.nombre}
          </span>
          <span className="block text-xs text-gray-500">{ETIQUETA_ROL[usuario?.rol] || ""}</span>
        </span>
        <ChevronDown
          size={16}
          aria-hidden="true"
          className={`hidden text-gray-400 transition-transform duration-150 sm:block ${abierto ? "rotate-180" : ""}`}
        />
      </button>

      {abierto && (
        <div
          role="menu"
          aria-label="Opciones de la cuenta"
          className="absolute right-0 top-[calc(100%+8px)] z-50 w-64 rounded-xl border border-linea bg-white p-1.5 shadow-[0_12px_32px_-12px_rgba(16,27,48,0.25)]"
        >
          <div className="border-b border-linea px-3 pb-2.5 pt-2">
            <div className="truncate text-sm font-semibold text-noche">{usuario?.nombre}</div>
            {usuario?.email && <div className="truncate text-xs text-gray-500">{usuario.email}</div>}
            <div className="mt-1.5 inline-flex rounded-full bg-acento-50 px-2 py-0.5 text-[11px] font-medium text-acento-600">
              {ETIQUETA_ROL[usuario?.rol] || usuario?.rol}
            </div>
          </div>
          <div className="pt-1.5">
            <Link
              ref={primerItem}
              to="/cambiar-password"
              role="menuitem"
              onClick={() => setAbierto(false)}
              className={`${item} text-noche hover:bg-marfil focus-visible:bg-marfil`}
            >
              <KeyRound size={16} className="text-gray-500" aria-hidden="true" />
              Cambiar contraseña
            </Link>
            <button
              type="button"
              role="menuitem"
              onClick={onLogout}
              className={`${item} text-red-600 hover:bg-red-50 focus-visible:bg-red-50`}
            >
              <LogOut size={16} aria-hidden="true" />
              Cerrar sesión
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
