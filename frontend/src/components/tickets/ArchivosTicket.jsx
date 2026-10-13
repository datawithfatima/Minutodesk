import {
  Download,
  File,
  FileImage,
  FileSpreadsheet,
  FileText,
  FileVideo,
  Music,
  Paperclip,
  Presentation,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  descargarAdjunto,
  eliminarAdjunto,
  listarAdjuntos,
  obtenerCatalogos,
  subirAdjunto,
} from "../../api";
import { obtenerUsuario } from "../../auth";
import Alert from "../ui/Alert";
import Spinner from "../ui/Spinner";
import { extensionDe, formatearBytes, problemaConArchivo } from "./formato";

function iconoDe(nombre) {
  const e = extensionDe(nombre);
  if ([".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"].includes(e)) return FileImage;
  if ([".mp4", ".mov", ".avi", ".mkv", ".webm"].includes(e)) return FileVideo;
  if ([".mp3", ".wav", ".m4a", ".ogg"].includes(e)) return Music;
  if ([".xls", ".xlsx", ".csv"].includes(e)) return FileSpreadsheet;
  if ([".ppt", ".pptx"].includes(e)) return Presentation;
  if ([".doc", ".docx", ".pdf", ".txt", ".log"].includes(e)) return FileText;
  return File;
}

/** Archivos de un ticket: ver, descargar, subir más y quitar los propios. */
export default function ArchivosTicket({ ticketId, resuelto, avisoInicial, onCambio }) {
  const yo = obtenerUsuario();
  const personal = yo.rol !== "usuario";
  const [adjuntos, setAdjuntos] = useState(null);
  const [limites, setLimites] = useState(null);
  const [error, setError] = useState(avisoInicial ?? null);
  const [subiendo, setSubiendo] = useState(false);
  const entrada = useRef(null);

  const cargar = useCallback(async () => setAdjuntos(await listarAdjuntos(ticketId)), [ticketId]);

  useEffect(() => {
    cargar().catch((e) => setError(e.message));
    obtenerCatalogos()
      .then((c) => setLimites(c.adjuntos))
      .catch(() => {});
  }, [cargar]);

  const maximo = limites?.maximo ?? 3;
  // El usuario ya no sube a un ticket resuelto; el personal sí.
  const puedeSubir = (personal || !resuelto) && (adjuntos?.length ?? 0) < maximo;
  const puedeQuitar = (a) => yo.rol === "administrador" || (a.subido_por_id === yo.id && !resuelto);

  async function subir(lista) {
    setError(null);
    setSubiendo(true);
    const fallos = [];
    let cantidad = adjuntos?.length ?? 0;
    for (const f of lista) {
      const motivo = problemaConArchivo(f, limites) ?? (cantidad >= maximo ? `ya hay ${maximo} archivos` : null);
      if (motivo) {
        fallos.push(`«${f.name}»: ${motivo}.`);
        continue;
      }
      try {
        await subirAdjunto(ticketId, f);
        cantidad += 1;
      } catch (e) {
        fallos.push(`«${f.name}»: ${e.message}`);
      }
    }
    await cargar().catch(() => {});
    onCambio?.();
    setSubiendo(false);
    if (fallos.length) setError(fallos.join(" "));
  }

  async function quitar(a) {
    if (!window.confirm(`¿Quitar «${a.nombre_original}» del ticket?`)) return;
    setError(null);
    try {
      await eliminarAdjunto(a.id);
      await cargar();
      onCambio?.();
    } catch (e) {
      setError(e.message);
    }
  }

  async function bajar(a) {
    setError(null);
    try {
      await descargarAdjunto(a);
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div>
      {error && (
        <Alert variant="danger" className="mb-3">
          {error}
        </Alert>
      )}
      {!adjuntos && !error && <Spinner size="sm" />}

      {adjuntos && adjuntos.length === 0 && (
        <p className="text-sm text-gray-500">Este ticket no tiene archivos adjuntos.</p>
      )}

      {adjuntos && adjuntos.length > 0 && (
        <ul className="divide-y divide-gray-100 rounded-lg border border-linea">
          {adjuntos.map((a) => {
            const Icono = iconoDe(a.nombre_original);
            return (
              <li key={a.id} className="flex items-center gap-3 px-3 py-2.5">
                <Icono size={18} className="shrink-0 text-gray-400" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-noche" title={a.nombre_original}>
                    {a.nombre_original}
                  </div>
                  <div className="text-xs text-gray-500">
                    {formatearBytes(a.tamano)} · {a.subido_por} · {new Date(a.creado_en).toLocaleDateString("es-EC")}
                  </div>
                </div>
                <button
                  onClick={() => bajar(a)}
                  aria-label={`Descargar ${a.nombre_original}`}
                  className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-marfil"
                >
                  <Download size={13} /> <span className="hidden sm:inline">Descargar</span>
                </button>
                {puedeQuitar(a) && (
                  <button
                    onClick={() => quitar(a)}
                    className="shrink-0 text-gray-400 hover:text-red-600"
                    aria-label={`Quitar ${a.nombre_original}`}
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {adjuntos && puedeSubir && (
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1">
          <button
            onClick={() => entrada.current?.click()}
            disabled={subiendo}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-marfil disabled:opacity-50"
          >
            {subiendo ? <Spinner size="sm" /> : <Paperclip size={15} />} Adjuntar archivo
          </button>
          <span className="text-xs text-gray-400">
            {adjuntos.length} de {maximo} · hasta {limites?.megabytes ?? 10} MB cada uno
          </span>
          <input
            ref={entrada}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => {
              subir([...e.target.files]);
              e.target.value = "";
            }}
          />
        </div>
      )}
    </div>
  );
}
