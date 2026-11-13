import { Bell, ClipboardCheck, MessageSquare } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { misAvisos } from "../api";

const CADA_MS = 60_000; // se revisa cada minuto y al cambiar de pantalla

/** Campanita de la barra superior: mensajes nuevos en tus tickets y aprobaciones pendientes. */
export default function Avisos() {
  const { pathname } = useLocation();
  const seccion = pathname.split("/")[1]; // usuario | tecnico | admin
  const [avisos, setAvisos] = useState([]);
  const [abierto, setAbierto] = useState(false);
  const contenedor = useRef(null);

  useEffect(() => {
    let vigente = true;
    const cargar = () =>
      misAvisos()
        .then((lista) => vigente && setAvisos(lista))
        .catch(() => {}); // un fallo de red no debe molestar: se reintenta en el siguiente ciclo
    cargar();
    const intervalo = setInterval(cargar, CADA_MS);
    return () => {
      vigente = false;
      clearInterval(intervalo);
    };
  }, [pathname]);

  useEffect(() => {
    if (!abierto) return undefined;
    const alClic = (e) => !contenedor.current?.contains(e.target) && setAbierto(false);
    const alTeclear = (e) => e.key === "Escape" && setAbierto(false);
    document.addEventListener("mousedown", alClic);
    document.addEventListener("keydown", alTeclear);
    return () => {
      document.removeEventListener("mousedown", alClic);
      document.removeEventListener("keydown", alTeclear);
    };
  }, [abierto]);

  const total = avisos.length;

  return (
    <div ref={contenedor} className="relative">
      <button
        type="button"
        onClick={() => setAbierto((a) => !a)}
        aria-haspopup="true"
        aria-expanded={abierto}
        aria-label={total ? `Avisos: ${total} ${total === 1 ? "pendiente" : "pendientes"}` : "Avisos: nada pendiente"}
        className="btn-obra relative rounded-md p-2 text-gray-600 hover:bg-marfil"
      >
        <Bell size={20} aria-hidden="true" className={total > 0 ? "anim-gancho" : ""} key={total} />
        {total > 0 && (
          <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-[3px] bg-acento px-1 font-mono text-[10px] font-semibold leading-none text-white">
            {total > 9 ? "9+" : total}
          </span>
        )}
      </button>

      {abierto && (
        <div className="anim-desplegar absolute right-0 z-40 mt-2 w-[min(20rem,calc(100vw-1.5rem))] overflow-hidden rounded-md border border-linea bg-white shadow-[0_16px_32px_-12px_rgb(27_30_34/0.3)]">
          <div className="franja-obra h-[3px]" aria-hidden="true" />
          <div className="border-b border-linea px-4 py-2.5 text-sm font-semibold text-noche">Avisos</div>
          {total === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-gray-500">No tienes nada pendiente.</p>
          ) : (
            <ul className="max-h-80 divide-y divide-gray-100 overflow-y-auto">
              {avisos.map((a) => {
                const esAprobacion = a.tipo === "aprobacion";
                const Icono = esAprobacion ? ClipboardCheck : MessageSquare;
                return (
                  <li key={`${a.tipo}-${a.ticket_id}-${a.fecha}`}>
                    <Link
                      to={esAprobacion ? `/${seccion}/aprobaciones` : `/${seccion}/tickets/${a.ticket_id}`}
                      onClick={() => setAbierto(false)}
                      className="flex gap-3 px-4 py-3 hover:bg-marfil"
                    >
                      <Icono size={16} aria-hidden="true" className="mt-0.5 shrink-0 text-acento" />
                      <span className="min-w-0">
                        <span className="block text-xs font-medium text-gray-700">
                          {esAprobacion ? "Te piden una aprobación" : "Nuevo mensaje"} · ticket #{a.ticket_id}
                        </span>
                        <span className="line-clamp-2 text-sm text-gray-600">{a.texto}</span>
                        <span className="text-[11px] text-gray-400">{new Date(a.fecha).toLocaleString()}</span>
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
