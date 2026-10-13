import { AlertTriangle, Bot, CheckCircle2, Lightbulb, Plus, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  crearAltaColaborador,
  crearTicket,
  obtenerCatalogos,
  subirAdjunto,
  sugerirClasificacion,
} from "../../api";
import { COLOR_PRIORIDAD } from "../../components/charts/tokens";
import SelectorArchivos from "../../components/tickets/SelectorArchivos";
import Alert from "../../components/ui/Alert";
import Button from "../../components/ui/Button";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";
import Spinner from "../../components/ui/Spinner";
import { inputClass } from "../../components/ui/formStyles";
import FormAltaColaborador, { ALTA_VACIA, problemaDelAlta } from "./FormAltaColaborador";

const MIN = 5;
const MAX = 5000;
const MIN_PARA_SUGERIR = 15;

const AYUDA_PRIORIDAD = {
  Crítica: "Me impide trabajar y no tengo alternativa.",
  Alta: "Afecta mi trabajo de forma importante.",
  Normal: "Puede atenderse en el orden habitual.",
  Baja: "No corre prisa.",
};

const ETIQUETA_DESCRIPCION = {
  0: "Describe detalladamente tu problema",
  1: "Indícanos tu idea o solicitud de servicio",
};

const CONSEJOS = [
  "Cuenta qué pasó y desde cuándo.",
  "Si aparece un mensaje de error, escríbelo tal cual.",
  "Indica qué equipo o sistema usas (por ejemplo, SAP, Salesforce o tu laptop).",
  "Un ticket por problema: así se atiende más rápido.",
];

function Paso({ numero, titulo, ayuda, children }) {
  return (
    <section className="border-t border-gray-100 pt-5 first:border-0 first:pt-0">
      <div className="mb-3 flex items-baseline gap-2">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-noche text-xs font-semibold text-white">
          {numero}
        </span>
        <div>
          <h2 className="text-sm font-semibold text-noche">{titulo}</h2>
          {ayuda && <p className="text-xs text-gray-500">{ayuda}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

export default function NuevoTicketPage() {
  const navegar = useNavigate();
  const [catalogos, setCatalogos] = useState(null);
  const [tipo, setTipo] = useState(null);
  const [texto, setTexto] = useState("");
  const [categoria, setCategoria] = useState("");
  const [categoriaTocada, setCategoriaTocada] = useState(false); // la persona ya eligió a mano
  const [prioridad, setPrioridad] = useState("Normal");
  const [archivos, setArchivos] = useState([]);
  const [sugerencia, setSugerencia] = useState(null);
  const [sugiriendo, setSugiriendo] = useState(false);
  const [alta, setAlta] = useState(ALTA_VACIA);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerCatalogos()
      .then(setCatalogos)
      .catch((e) => setError(e.message));
  }, []);

  const tipoAccesos = catalogos?.tipos[2]?.nombre; // el tercero es «Gestión de usuarios y accesos»
  const esAlta = tipo !== null && tipo === tipoAccesos;
  const largo = texto.trim().length;

  // Mientras la persona escribe, el SVM propone tipo y categoría (un instante después de teclear).
  useEffect(() => {
    if (esAlta || largo < MIN_PARA_SUGERIR) {
      setSugerencia(null);
      return undefined;
    }
    let vigente = true;
    const espera = setTimeout(() => {
      setSugiriendo(true);
      sugerirClasificacion(texto.trim())
        .then((s) => {
          if (!vigente) return;
          setSugerencia(s);
          if (!categoriaTocada) setCategoria(s.confiable ? s.categoria : "");
        })
        .catch(() => vigente && setSugerencia(null))
        .finally(() => vigente && setSugiriendo(false));
    }, 700);
    return () => {
      vigente = false;
      clearTimeout(espera);
    };
    // La categoría tocada no debe reiniciar la sugerencia.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [texto, esAlta]);

  function elegirCategoria(valor) {
    setCategoria(valor);
    setCategoriaTocada(true);
  }

  async function subirArchivos(ticketId) {
    const avisos = [];
    for (const f of archivos) {
      try {
        await subirAdjunto(ticketId, f);
      } catch (e) {
        avisos.push(`«${f.name}»: ${e.message}`);
      }
    }
    return avisos;
  }

  async function manejarEnvio(e) {
    e.preventDefault();
    setError(null);
    if (!tipo) return setError("Elige el tipo de ticket.");
    if (esAlta) {
      const problema = problemaDelAlta(alta);
      if (problema) return setError(problema);
    } else {
      if (largo < MIN) return setError(`Describe tu solicitud (mínimo ${MIN} caracteres).`);
      if (!categoria) return setError("Elige la categoría del ticket.");
    }

    setEnviando(true);
    try {
      const ticket = esAlta
        ? await crearAltaColaborador({
            ...alta,
            nombres: alta.nombres.trim(),
            cedula: alta.cedula.trim(),
            grupo: alta.grupo.trim() || null,
            permisos_sap: alta.permisos_sap.trim() || null,
            prioridad,
          })
        : await crearTicket({ texto, tipo, categoria, prioridad });
      const avisos = await subirArchivos(ticket.id);
      navegar(`/usuario/tickets/${ticket.id}`, { state: { creado: true, avisos } });
    } catch (e) {
      setError(e.message);
      setEnviando(false);
    }
  }

  if (!catalogos) {
    return (
      <>
        <PageHeader icon={Plus} title="Crear ticket" subtitle="Cuéntanos tu problema o solicitud y un técnico lo atenderá." />
        {error ? <Alert variant="danger">{error}</Alert> : <Spinner size="sm" />}
      </>
    );
  }

  const puedeEnviar = tipo && (esAlta || (largo >= MIN && categoria));
  const nombreSugerido = sugerencia && catalogos.tipos.find((t) => t.nombre === sugerencia.tipo)?.titulo;

  return (
    <>
      <PageHeader icon={Plus} title="Crear ticket" subtitle="Cuéntanos tu problema o solicitud y un técnico lo atenderá." />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <Card.Body>
            {error && (
              <Alert variant="danger" className="mb-4">
                {error}
              </Alert>
            )}
            <form onSubmit={manejarEnvio} className="space-y-5">
              <Paso numero={1} titulo="¿Qué tipo de ticket es?" ayuda="Elige una opción. Si no estás seguro, escribe primero la descripción y te sugerimos una.">
                <div role="radiogroup" className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {catalogos.tipos.map((t) => {
                    const elegido = tipo === t.nombre;
                    const sugerido = !esAlta && sugerencia?.tipo === t.nombre && t.nombre !== tipoAccesos;
                    return (
                      <button
                        type="button"
                        role="radio"
                        aria-checked={elegido}
                        key={t.nombre}
                        onClick={() => setTipo(t.nombre)}
                        className={`relative rounded-lg border p-3 text-left transition-colors ${
                          elegido ? "border-noche bg-noche text-white" : "border-linea bg-white hover:border-gray-400"
                        }`}
                      >
                        {sugerido && (
                          <span
                            className={`absolute right-2 top-2 inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                              elegido ? "bg-white/20 text-white" : "bg-amber-50 text-amber-800"
                            }`}
                          >
                            <Sparkles size={10} /> Sugerido
                          </span>
                        )}
                        <div className="pr-14 text-sm font-semibold">{t.titulo}</div>
                        <div className={`mt-0.5 text-xs ${elegido ? "text-gray-300" : "text-gray-500"}`}>{t.ayuda}</div>
                      </button>
                    );
                  })}
                </div>
                {!tipo && nombreSugerido && !esAlta && (
                  <p className="mt-2 text-xs text-gray-600">
                    Por tu descripción parece una <strong>{nombreSugerido}</strong>.{" "}
                    <button type="button" className="font-medium text-noche underline" onClick={() => setTipo(sugerencia.tipo)}>
                      Usar esa
                    </button>
                  </p>
                )}
              </Paso>

              {esAlta ? (
                <Paso numero={2} titulo="Datos del nuevo colaborador" ayuda="Completa lo que pide el alta; los campos con * son obligatorios.">
                  <FormAltaColaborador datos={alta} onCambio={setAlta} catalogos={catalogos} />
                </Paso>
              ) : (
                <>
                  <Paso numero={2} titulo={ETIQUETA_DESCRIPCION[catalogos.tipos.findIndex((t) => t.nombre === tipo)] ?? "Describe tu problema o solicitud"}>
                    <label htmlFor="texto-ticket" className="sr-only">
                      Descripción
                    </label>
                    <textarea
                      id="texto-ticket"
                      rows={7}
                      className={`${inputClass} resize-y`}
                      value={texto}
                      onChange={(e) => setTexto(e.target.value)}
                      maxLength={MAX}
                      placeholder="Ej.: Desde ayer no puedo conectarme a la VPN, me dice que las credenciales son inválidas."
                    />
                    <div className="mt-1 flex items-center justify-between gap-3 text-xs text-gray-400">
                      <span>{largo < MIN ? `Escribe al menos ${MIN} caracteres.` : "Cuanto más detalle, más rápido se atiende."}</span>
                      <span className="shrink-0">
                        {largo} / {MAX}
                      </span>
                    </div>
                  </Paso>

                  <Paso numero={3} titulo="Categoría" ayuda="La proponemos según tu descripción; puedes cambiarla.">
                    {sugiriendo && (
                      <p className="mb-2 flex items-center gap-2 text-xs text-gray-500">
                        <Spinner size="sm" /> Analizando tu descripción…
                      </p>
                    )}
                    {sugerencia && !sugiriendo && (
                      <div
                        className={`mb-2 flex items-start gap-2 rounded-lg px-3 py-2 text-sm ${
                          sugerencia.confiable ? "bg-emerald-50 text-emerald-900" : "bg-amber-50 text-amber-900"
                        }`}
                      >
                        {sugerencia.confiable ? <CheckCircle2 size={16} className="mt-0.5 shrink-0" /> : <AlertTriangle size={16} className="mt-0.5 shrink-0" />}
                        <span>
                          {sugerencia.confiable ? (
                            <>
                              Sugerimos <strong>{sugerencia.categoria}</strong> ({Math.round(sugerencia.confianza * 100)}% de confianza).
                              Si no es correcta, elige otra.
                            </>
                          ) : (
                            <>No estamos seguros de la categoría. Revisa las más probables o elige la correcta.</>
                          )}
                        </span>
                      </div>
                    )}
                    <select
                      className={inputClass}
                      value={categoria}
                      onChange={(e) => elegirCategoria(e.target.value)}
                      aria-label="Categoría"
                    >
                      <option value="">Selecciona una categoría…</option>
                      {catalogos.categorias.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                    {sugerencia && sugerencia.alternativas.length > 0 && (
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                        Más probables:
                        {sugerencia.alternativas.map((a) => (
                          <button
                            type="button"
                            key={a.categoria}
                            onClick={() => elegirCategoria(a.categoria)}
                            className={`rounded-full border px-2.5 py-0.5 ${
                              categoria === a.categoria ? "border-noche bg-noche text-white" : "border-gray-300 text-gray-700 hover:bg-marfil"
                            }`}
                          >
                            {a.categoria} · {Math.round(a.confianza * 100)}%
                          </button>
                        ))}
                      </div>
                    )}
                  </Paso>
                </>
              )}

              <Paso numero={esAlta ? 3 : 4} titulo="Prioridad" ayuda="Si no estás seguro, déjala en Normal: el técnico puede ajustarla.">
                <div role="radiogroup" className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {catalogos.prioridades.map((p) => {
                    const elegida = prioridad === p;
                    return (
                      <button
                        type="button"
                        role="radio"
                        aria-checked={elegida}
                        key={p}
                        onClick={() => setPrioridad(p)}
                        className={`rounded-lg border p-2.5 text-left transition-colors ${
                          elegida ? "border-noche ring-1 ring-noche" : "border-linea hover:border-gray-400"
                        }`}
                      >
                        <div className="flex items-center gap-2 text-sm font-semibold text-noche">
                          <span className="h-2.5 w-2.5 rounded-full" style={{ background: COLOR_PRIORIDAD[p] }} />
                          {p}
                        </div>
                        <div className="mt-0.5 text-xs text-gray-500">{AYUDA_PRIORIDAD[p]}</div>
                      </button>
                    );
                  })}
                </div>
              </Paso>

              <Paso numero={esAlta ? 4 : 5} titulo="Archivos (opcional)" ayuda="Capturas de pantalla, documentos o cualquier evidencia que ayude.">
                <SelectorArchivos archivos={archivos} onCambio={setArchivos} limites={catalogos.adjuntos} />
              </Paso>

              <div className="flex flex-col items-stretch gap-3 border-t border-gray-100 pt-5 text-center sm:flex-row sm:flex-wrap sm:items-center sm:text-left">
                <Button type="submit" variant="dark" disabled={enviando || !puedeEnviar}>
                  {enviando ? <Spinner size="sm" /> : esAlta ? "Enviar solicitud de alta" : "Crear ticket"}
                </Button>
                <Link to="/usuario/mis-tickets" className="text-sm text-gray-500 hover:underline">
                  Cancelar
                </Link>
              </div>
            </form>
          </Card.Body>
        </Card>

        <div className="space-y-4">
          <Card>
            <Card.Body>
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-noche">
                <Lightbulb size={16} className="text-amber-500" /> Para que lo atiendan más rápido
              </div>
              <ul className="list-disc space-y-1.5 pl-5 text-sm text-gray-600">
                {CONSEJOS.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </Card.Body>
          </Card>

          <Card>
            <Card.Body>
              <div className="mb-1 flex items-center gap-2 text-sm font-semibold text-noche">
                <Bot size={16} /> ¿Prefieres ayuda inmediata?
              </div>
              <p className="mb-3 text-sm text-gray-600">
                Minutito puede darte pasos para resolverlo ahora mismo. Si no te sirve, tu ticket queda listo para un técnico.
              </p>
              <Link to="/usuario" className="text-sm font-medium text-noche hover:underline">
                Hablar con Minutito →
              </Link>
            </Card.Body>
          </Card>
        </div>
      </div>
    </>
  );
}
