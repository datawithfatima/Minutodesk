import { Bot, Layers3, Sparkles } from "lucide-react";
import { Marca } from "./Logo";
import BotonTema from "./BotonTema";
import ObraIlustracion from "./ObraIlustracion";

// Lo que el producto hace hoy (sin promesas).
const PUNTOS = [
  { Icono: Layers3, texto: "Cada ticket con su tipo, categoría, prioridad y estado." },
  { Icono: Sparkles, texto: "La categoría se sugiere mientras escribes la solicitud." },
  { Icono: Bot, texto: "Minutito resuelve lo más común y, si no puede, deja el caso al equipo." },
];

/**
 * Marco de las pantallas de acceso (ingresar, recuperar y cambiar contraseña).
 * Escritorio: lámina de plano en grafito con la obra animada + formulario. Móvil: solo el formulario.
 */
export default function AuthShell({ titulo, descripcion, children, pie }) {
  return (
    <div className="papel-plano flex min-h-screen">
      <aside className="relative hidden w-[46%] max-w-[640px] shrink-0 flex-col justify-between overflow-hidden bg-grafito p-10 text-white lg:flex xl:p-12">
        {/* Cuadrícula de plano sobre el grafito */}
        <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full">
          <defs>
            <pattern id="trama-fina" width="24" height="24" patternUnits="userSpaceOnUse">
              <path d="M24 0H0v24" fill="none" stroke="#fff" strokeOpacity=".035" strokeWidth="1" />
            </pattern>
            <pattern id="trama-gruesa" width="120" height="120" patternUnits="userSpaceOnUse">
              <rect width="120" height="120" fill="url(#trama-fina)" />
              <path d="M120 0H0v120" fill="none" stroke="#fff" strokeOpacity=".07" strokeWidth="1" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#trama-gruesa)" />
        </svg>

        <div className="relative flex items-center justify-between">
          <Marca oscuro subtitulo />
          <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-noche-300">Lámina 01 · Acceso</span>
        </div>

        <div className="relative">
          <ObraIlustracion className="-ml-2 mb-8 w-full max-w-[460px]" />
          <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-casco">Mesa de ayuda de TI</p>
          <h2 className="mt-3 text-[34px] font-bold leading-[1.05] xl:text-[42px]">
            Cada solicitud,
            <br />
            en su lugar.
          </h2>
          <ul className="mt-7 space-y-3.5">
            {PUNTOS.map(({ Icono, texto }) => (
              <li key={texto} className="flex items-start gap-3 text-[15px] leading-snug text-white/80">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-[5px] border border-white/10 bg-white/[0.05] text-casco">
                  <Icono size={15} aria-hidden="true" />
                </span>
                {texto}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative flex items-end justify-between gap-6 border-t border-white/10 pt-4">
          <p className="text-xs text-noche-300">Las cuentas las crea el administrador de la plataforma.</p>
          <span aria-hidden="true" className="franja-obra h-2 w-20 shrink-0 rounded-[1px] opacity-90" />
        </div>
      </aside>

      <main className="flex flex-1 flex-col px-4 py-6 sm:px-8">
        <div className="flex items-center justify-between gap-3">
          <span className="lg:invisible">
            <Marca size="h-8 w-8" />
          </span>
          <BotonTema />
        </div>

        <div className="flex flex-1 items-center justify-center py-8">
          <div className="anim-levantar w-full max-w-[420px]">
            <div className="lamina relative rounded-md border border-linea bg-superficie p-6 shadow-[0_1px_0_rgb(27_30_34/0.04),0_18px_40px_-20px_rgb(27_30_34/0.25)] sm:p-8">
              <span aria-hidden="true" className="franja-obra absolute inset-x-0 top-0 h-1 rounded-t-md" />
              {titulo && (
                <div className="mb-6">
                  <h1 className="text-[24px] font-bold text-noche">{titulo}</h1>
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
