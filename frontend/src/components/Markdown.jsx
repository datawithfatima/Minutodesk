/**
 * Markdown básico para las respuestas de Minutito: párrafos, listas numeradas y con viñetas,
 * títulos, **negrita** y `código`. Arma elementos de React (nunca HTML crudo), así que un
 * texto con etiquetas se muestra tal cual y no se ejecuta.
 */
function enLinea(texto, clave) {
  const partes = texto.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean);
  return partes.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**")) return <strong key={`${clave}-${i}`} className="font-semibold text-noche">{p.slice(2, -2)}</strong>;
    if (p.startsWith("`") && p.endsWith("`"))
      return (
        <code key={`${clave}-${i}`} className="rounded bg-marfil px-1 py-0.5 font-mono text-[0.85em]">
          {p.slice(1, -1)}
        </code>
      );
    return p;
  });
}

export default function Markdown({ texto }) {
  const bloques = [];
  let lista = null; // { tipo: "ol" | "ul", items: [[nivel, texto]] }

  const cerrarLista = () => {
    if (lista) bloques.push(lista);
    lista = null;
  };

  for (const linea of (texto || "").split("\n")) {
    const numerada = linea.match(/^(\s*)\d+[.)]\s+(.*)$/);
    const vineta = linea.match(/^(\s*)[-*•]\s+(.*)$/);
    if (numerada || vineta) {
      const [, sangria, contenido] = numerada || vineta;
      const tipo = numerada ? "ol" : "ul";
      const nivel = sangria.length >= 2 ? 1 : 0;
      // Una sublista de viñetas dentro de una lista numerada se queda en la misma lista.
      if (!lista || (lista.tipo !== tipo && nivel === 0)) {
        cerrarLista();
        lista = { tipo, items: [] };
      }
      lista.items.push([nivel, contenido]);
      continue;
    }
    cerrarLista();
    if (!linea.trim()) continue;
    const titulo = linea.match(/^\s*#{1,6}\s+(.*)$/);
    bloques.push({ tipo: titulo ? "h" : "p", texto: titulo ? titulo[1] : linea });
  }
  cerrarLista();

  return (
    <div className="space-y-2">
      {bloques.map((b, i) => {
        if (b.tipo === "p") return <p key={i}>{enLinea(b.texto, i)}</p>;
        if (b.tipo === "h")
          return (
            <p key={i} className="font-semibold text-noche">
              {enLinea(b.texto, i)}
            </p>
          );
        const Lista = b.tipo;
        return (
          <Lista key={i} className={`space-y-1 pl-5 ${b.tipo === "ol" ? "list-decimal" : "list-disc"}`}>
            {b.items.map(([nivel, t], j) => (
              <li key={j} className={nivel ? "ml-4 list-[circle]" : ""}>
                {enLinea(t, `${i}-${j}`)}
              </li>
            ))}
          </Lista>
        );
      })}
    </div>
  );
}
