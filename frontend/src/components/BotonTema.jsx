import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { alternarTema, temaActual } from "../tema";

/** Interruptor de modo claro / oscuro: el sol se pone y sale la luna. */
export default function BotonTema({ className = "" }) {
  const [tema, setTema] = useState(temaActual);

  useEffect(() => {
    const alCambiar = (e) => setTema(e.detail);
    window.addEventListener("cambio-tema", alCambiar);
    return () => window.removeEventListener("cambio-tema", alCambiar);
  }, []);

  const oscuro = tema === "oscuro";
  return (
    <button
      type="button"
      onClick={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        alternarTema(r.left + r.width / 2, r.top + r.height / 2);
      }}
      aria-label={oscuro ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      aria-pressed={oscuro}
      title={oscuro ? "Modo claro" : "Modo oscuro"}
      className={`btn-obra relative h-9 w-9 overflow-hidden rounded-md text-gray-600 hover:bg-marfil hover:text-noche ${className}`}
    >
      <Sun
        size={19}
        aria-hidden="true"
        className={`icono-tema absolute left-1/2 top-1/2 -ml-[9.5px] -mt-[9.5px] ${
          oscuro ? "translate-y-6 rotate-90 opacity-0" : "text-acento"
        }`}
      />
      <Moon
        size={18}
        aria-hidden="true"
        className={`icono-tema absolute left-1/2 top-1/2 -ml-[9px] -mt-[9px] ${
          oscuro ? "text-casco" : "-translate-y-6 -rotate-90 opacity-0"
        }`}
      />
    </button>
  );
}
