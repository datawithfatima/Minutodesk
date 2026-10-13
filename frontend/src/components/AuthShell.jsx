import { ArrowLeft, Bot, Layers3, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { Marca } from "./Logo";

// Lo que el producto hace hoy (sin promesas): se repite en la portada.
const PUNTOS = [
  { Icono: Layers3, texto: "Cada ticket con su tipo, categoría, prioridad y estado." },
  { Icono: Sparkles, texto: "La categoría se sugiere mientras escribes la solicitud." },
  { Icono: Bot, texto: "Minutito resuelve lo más común y, si no puede, deja el caso al equipo." },
];

/**
 * Marco de las pantallas de acceso (ingresar, recuperar y cambiar contraseña).
 * Escritorio: panel de marca en azul noche + formulario. Móvil: solo el formulario.
 */
export default function AuthShell({ titulo, descripcion, children, pie }) {
  return (
    <div className="flex min-h-screen bg-marfil">
      <aside className="relative hidden w-[42%] max-w-[560px] shrink-0 flex-col justify-between overflow-hidden bg-noche p-10 text-white lg:flex xl:p-12">
        {/* Trama sutil de líneas: textura sin degradados ni efectos de cristal. */}
        <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.07]">
          <defs>
            <pattern id="trama-acceso" width="32" height="32" patternUnits="userSpaceOnUse">
              <path d="M32 0H0v32" fill="none" stroke="#fff" strokeWidth="1" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#trama-acceso)" />
        </svg>

        <Link to="/" className="relative w-fit rounded-lg" aria-label="MinutoDesk, ir a la portada">
          <Marca oscuro />
        </Link>

        <div className="relative">
          <p className="text-sm font-medium text-acento-100">Mesa de ayuda TI</p>
          <h2 className="mt-3 text-[34px] font-semibold leading-[1.1] tracking-[-0.03em] xl:text-[40px]">
            Cada solicitud,
            <br />
            en su lugar.
          </h2>
          <ul className="mt-8 space-y-4">
            {PUNTOS.map(({ Icono, texto }) => (
              <li key={texto} className="flex items-start gap-3 text-[15px] leading-snug text-white/80">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/[0.08] text-acento-100">
                  <Icono size={15} aria-hidden="true" />
                </span>
                {texto}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-noche-300">
          Las cuentas las crea el administrador de la plataforma.
        </p>
      </aside>

      <main className="flex flex-1 flex-col px-4 py-6 sm:px-8">
        <div className="flex items-center justify-between">
          <Link to="/" className="rounded-lg lg:hidden" aria-label="MinutoDesk, ir a la portada">
            <Marca size="h-8 w-8" />
          </Link>
          <Link
            to="/"
            className="ml-auto inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm text-gray-500 transition-colors duration-150 hover:bg-white hover:text-noche"
          >
            <ArrowLeft size={15} aria-hidden="true" />
            <span className="hidden sm:inline">Volver a la portada</span>
            <span className="sm:hidden">Portada</span>
          </Link>
        </div>

        <div className="flex flex-1 items-center justify-center py-8">
          <div className="w-full max-w-[400px]">
            <div className="rounded-2xl border border-linea bg-white p-6 shadow-[0_1px_2px_rgba(16,27,48,0.04),0_8px_24px_-12px_rgba(16,27,48,0.12)] sm:p-8">
              {titulo && (
                <div className="mb-6">
                  <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-noche">{titulo}</h1>
                  {descripcion && <p className="mt-1.5 text-sm leading-relaxed text-gray-500">{descripcion}</p>}
                </div>
              )}
              {children}
            </div>
            {pie && <div className="mt-5 text-center text-sm text-gray-500">{pie}</div>}
          </div>
        </div>
      </main>
    </div>
  );
}
