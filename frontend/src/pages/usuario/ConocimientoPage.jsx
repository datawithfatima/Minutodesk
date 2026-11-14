import {
  BookOpen,
  Bot,
  Check,
  Cloud,
  Gauge,
  KeyRound,
  Keyboard,
  LockKeyhole,
  Mail,
  Monitor,
  Plus,
  Power,
  Printer,
  Search,
  ShieldCheck,
  Sheet,
  Video,
  Wifi,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { obtenerConocimiento } from "../../api";
import Alert from "../../components/ui/Alert";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";

/*
 * Base de conocimiento: las fichas de pasos verificados que usa Minutito, a la vista para
 * que la persona resuelva sola. Se presentan como «procedimientos de obra»: cada ficha
 * es una lámina con sus pasos numerados que se pueden ir marcando.
 */

const ICONOS = {
  onedrive: Cloud,
  "contrasena-olvidada": KeyRound,
  vpn: ShieldCheck,
  impresora: Printer,
  "videollamadas-teams-zoom": Video,
  "office-excel-word-powerpoint": Sheet,
  "correo-outlook": Mail,
  "internet-o-wi-fi": Wifi,
  "equipo-que-no-enciende": Power,
  "equipo-lento": Gauge,
  "pantalla-o-monitor": Monitor,
  "mouse-o-teclado": Keyboard,
  "contrasena-o-acceso-a-una-cuenta": LockKeyhole,
};

const sinTildes = (t) =>
  (t || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");

function Procedimiento({ ficha, codigo, onCerrar }) {
  const [hechos, setHechos] = useState([]);
  const Icono = ICONOS[ficha.clave] || BookOpen;
  const todos = hechos.length === ficha.pasos.length;

  return (
    <section className="anim-levantar-ventana overflow-hidden rounded-lg border border-linea bg-superficie shadow-[0_1px_0_rgb(27_30_34/0.04),0_1px_3px_rgb(27_30_34/0.05)]">
      <header className="relative bg-grafito px-5 pb-4 pt-4 text-white">
        <span aria-hidden="true" className="franja-obra absolute inset-x-0 bottom-0 h-1" />
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-casco text-grafito">
              <Icono size={20} aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <p className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-casco">
                Procedimiento {codigo} · {ficha.pasos.length} pasos
              </p>
              <h2 className="text-lg font-bold text-white">{ficha.tema}</h2>
            </div>
          </div>
          <button
            type="button"
            onClick={onCerrar}
            aria-label="Cerrar procedimiento"
            className="rounded-md p-1.5 text-white/60 hover:bg-white/10 hover:text-white"
          >
            <X size={18} />
          </button>
        </div>
      </header>

      <ol className="divide-y divide-dashed divide-linea">
        {ficha.pasos.map((paso, i) => {
          const hecho = hechos.includes(i);
          return (
            <li key={i}>
              <label className="flex cursor-pointer items-start gap-3 px-5 py-3.5 hover:bg-marfil">
                <input
                  type="checkbox"
                  className="peer sr-only"
                  checked={hecho}
                  onChange={() => setHechos((h) => (hecho ? h.filter((x) => x !== i) : [...h, i]))}
                />
                <span
                  aria-hidden="true"
                  className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-[4px] border font-mono text-xs font-semibold transition-colors peer-focus-visible:ring-2 peer-focus-visible:ring-acento ${
                    hecho ? "border-green-600 bg-green-600 text-white" : "border-linea bg-gray-50 text-gray-600"
                  }`}
                >
                  {hecho ? <Check size={14} /> : i + 1}
                </span>
                <span className={`text-[15px] leading-relaxed ${hecho ? "text-gray-500 line-through" : "text-noche"}`}>
                  {paso}
                </span>
              </label>
            </li>
          );
        })}
      </ol>

      <footer className="border-t border-linea bg-gray-50 px-5 py-4">
        <p className="text-sm text-gray-600">
          {todos
            ? "Hiciste todos los pasos. Si el problema sigue, el equipo de sistemas te ayuda:"
            : "Marca cada paso a medida que lo pruebes. Si no se resuelve:"}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link
            to="/usuario#minutito"
            className="btn-obra inline-flex h-9 items-center gap-2 rounded-md bg-acento px-3.5 text-sm font-semibold text-white hover:bg-acento-600"
          >
            <Bot size={15} /> Pregúntale a Minutito
          </Link>
          <Link
            to="/usuario/nuevo-ticket"
            className="btn-obra inline-flex h-9 items-center gap-2 rounded-md border border-linea bg-superficie px-3.5 text-sm font-semibold text-noche hover:border-noche/40"
          >
            <Plus size={15} /> Crear ticket
          </Link>
        </div>
      </footer>
    </section>
  );
}

export default function ConocimientoPage() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [busqueda, setBusqueda] = useState("");
  const [sugerida, setSugerida] = useState(null);
  const [abierta, setAbierta] = useState(null);

  useEffect(() => {
    obtenerConocimiento()
      .then(setDatos)
      .catch((e) => setError(e.message));
  }, []);

  // Con lo que escribe la persona, el servidor dice qué ficha usaría Minutito para ese problema.
  useEffect(() => {
    const q = busqueda.trim();
    if (q.length < 3) {
      setSugerida(null);
      return;
    }
    const espera = setTimeout(() => {
      obtenerConocimiento(q)
        .then((r) => setSugerida(r.sugerida))
        .catch(() => setSugerida(null));
    }, 300);
    return () => clearTimeout(espera);
  }, [busqueda]);

  const visibles = useMemo(() => {
    if (!datos) return [];
    const q = sinTildes(busqueda.trim());
    const lista = datos.fichas.map((f, i) => ({ ...f, codigo: `P-${String(i + 1).padStart(2, "0")}` }));
    if (!q) return lista;
    const coincide = (f) =>
      f.clave === sugerida ||
      sinTildes(f.tema).includes(q) ||
      f.palabras.some((p) => q.includes(p) || p.includes(q)) ||
      f.pasos.some((p) => sinTildes(p).includes(q));
    return lista.filter(coincide).sort((a, b) => (b.clave === sugerida) - (a.clave === sugerida));
  }, [datos, busqueda, sugerida]);

  // En pantallas angostas el procedimiento queda debajo de la lista: se lleva la vista a él.
  useEffect(() => {
    if (abierta && window.matchMedia("(max-width: 1023px)").matches) {
      document.getElementById("procedimiento")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [abierta]);

  const fichaAbierta = visibles.find((f) => f.clave === abierta) || datos?.fichas.find((f) => f.clave === abierta);
  const codigoAbierta = datos ? `P-${String(datos.fichas.findIndex((f) => f.clave === abierta) + 1).padStart(2, "0")}` : "";

  return (
    <>
      <PageHeader icon={BookOpen} title="Base de conocimiento" />
      <p className="-mt-2 mb-5 max-w-2xl text-sm text-gray-600">
        Los procedimientos que el equipo de sistemas verificó para los problemas más comunes. Son los mismos pasos que te
        da Minutito: puedes seguirlos por tu cuenta, sin chat y sin ticket.
      </p>

      {error && <Alert variant="danger">{error}</Alert>}
      {!datos && !error && <Spinner size="sm" />}

      {datos && (
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
          <div className="min-w-0">
            <label className="relative mb-4 block">
              <span className="sr-only">Describe tu problema</span>
              <Search size={17} aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="search"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                placeholder="Describe tu problema: «no puedo imprimir», «Outlook no abre»…"
                className="campo-obra h-11 w-full rounded-md border border-linea bg-superficie pl-10 pr-3 text-sm text-noche placeholder:text-gray-400"
              />
            </label>

            {visibles.length === 0 ? (
              <div className="rounded-md border border-dashed border-linea bg-gray-50 p-5 text-sm text-gray-600">
                No encontramos un procedimiento para eso.{" "}
                <Link to="/usuario#minutito" className="font-semibold text-acento hover:underline">
                  Cuéntaselo a Minutito
                </Link>{" "}
                o{" "}
                <Link to="/usuario/nuevo-ticket" className="font-semibold text-acento hover:underline">
                  crea un ticket
                </Link>
                .
              </div>
            ) : (
              <ul className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
                {visibles.map((f) => {
                  const Icono = ICONOS[f.clave] || BookOpen;
                  const activa = f.clave === abierta;
                  const recomendada = f.clave === sugerida && busqueda.trim().length >= 3;
                  return (
                    <li key={f.clave}>
                      <button
                        type="button"
                        onClick={() => setAbierta(f.clave)}
                        aria-pressed={activa}
                        className={`lamina group flex w-full items-center gap-3 rounded-md border px-3 py-3 text-left transition-colors ${
                          activa
                            ? "border-acento bg-acento-50"
                            : recomendada
                              ? "border-casco bg-casco-100"
                              : "border-linea bg-superficie hover:border-noche/30"
                        }`}
                      >
                        <span
                          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md ${
                            activa ? "bg-acento text-white" : "bg-grafito text-casco"
                          }`}
                        >
                          <Icono size={17} aria-hidden="true" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block font-mono text-[10px] uppercase tracking-[0.14em] text-gray-500">
                            {f.codigo} · {f.pasos.length} pasos{recomendada ? " · recomendado" : ""}
                          </span>
                          <span className="block text-sm font-semibold leading-snug text-noche">{f.tema}</span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <div id="procedimiento" className="min-w-0 scroll-mt-20 lg:sticky lg:top-22">
            {fichaAbierta ? (
              <Procedimiento
                key={fichaAbierta.clave}
                ficha={fichaAbierta}
                codigo={codigoAbierta}
                onCerrar={() => setAbierta(null)}
              />
            ) : (
              <div className="lamina hidden rounded-lg border border-dashed border-linea bg-gray-50 p-8 text-center lg:block">
                <BookOpen size={28} aria-hidden="true" className="mx-auto text-gray-400" />
                <p className="mt-3 text-sm font-semibold text-noche">Elige un procedimiento</p>
                <p className="mt-1 text-sm text-gray-500">Verás sus pasos aquí, para ir marcándolos mientras los pruebas.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
