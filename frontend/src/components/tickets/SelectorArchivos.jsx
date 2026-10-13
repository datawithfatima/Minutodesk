import { FileText, Paperclip, X } from "lucide-react";
import { useRef, useState } from "react";
import { formatearBytes, problemaConArchivo } from "./formato";

/**
 * Elige los archivos antes de crear el ticket (se suben justo después de crearlo).
 * Valida en el momento los mismos límites que el servidor: cantidad, tamaño y tipo.
 */
export default function SelectorArchivos({ archivos, onCambio, limites }) {
  const entrada = useRef(null);
  const [aviso, setAviso] = useState(null);
  const [arrastrando, setArrastrando] = useState(false);
  const maximo = limites?.maximo ?? 3;

  function agregar(lista) {
    const nuevos = [...lista];
    const avisos = [];
    const aceptados = [...archivos];
    for (const f of nuevos) {
      const motivo = problemaConArchivo(f, limites);
      if (motivo) avisos.push(`«${f.name}» ${motivo}.`);
      else if (aceptados.length >= maximo) avisos.push(`Solo se pueden adjuntar ${maximo} archivos; «${f.name}» no se agregó.`);
      else if (aceptados.some((a) => a.name === f.name && a.size === f.size)) avisos.push(`«${f.name}» ya estaba en la lista.`);
      else aceptados.push(f);
    }
    setAviso(avisos.length ? avisos.join(" ") : null);
    onCambio(aceptados);
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setArrastrando(true);
        }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => {
          e.preventDefault();
          setArrastrando(false);
          agregar(e.dataTransfer.files);
        }}
        className={`flex flex-wrap items-center gap-3 rounded-lg border border-dashed p-4 text-sm transition-colors ${
          arrastrando ? "border-noche bg-marfil" : "border-gray-300"
        }`}
      >
        <button
          type="button"
          onClick={() => entrada.current?.click()}
          disabled={archivos.length >= maximo}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-1.5 font-medium text-gray-700 hover:bg-marfil disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Paperclip size={15} /> Adjuntar archivos
        </button>
        <span className="text-xs text-gray-500">
          o arrástralos aquí · hasta {maximo} archivos de {limites?.megabytes ?? 10} MB (Word, Excel, PowerPoint,
          PDF, imagen, video, audio o texto)
        </span>
        <input
          ref={entrada}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            agregar(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {aviso && <p className="mt-2 text-xs text-red-600">{aviso}</p>}

      {archivos.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {archivos.map((f, i) => (
            <li key={`${f.name}-${i}`} className="flex items-center gap-2 rounded-lg bg-marfil px-3 py-1.5 text-sm">
              <FileText size={15} className="shrink-0 text-gray-400" />
              <span className="min-w-0 flex-1 truncate text-gray-800" title={f.name}>
                {f.name}
              </span>
              <span className="shrink-0 text-xs text-gray-400">{formatearBytes(f.size)}</span>
              <button
                type="button"
                onClick={() => onCambio(archivos.filter((_, j) => j !== i))}
                className="shrink-0 text-gray-400 hover:text-red-600"
                aria-label={`Quitar ${f.name}`}
              >
                <X size={15} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
