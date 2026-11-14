// Tema claro / oscuro. Se guarda en este navegador (localStorage); si no hay preferencia
// guardada, se usa la del sistema operativo. El atributo data-tema="oscuro" en <html>
// activa los colores de modo oscuro definidos en index.css.
const CLAVE = "minutodesk_tema";

export function temaActual() {
  return document.documentElement.dataset.tema === "oscuro" ? "oscuro" : "claro";
}

function aplicar(tema) {
  if (tema === "oscuro") document.documentElement.dataset.tema = "oscuro";
  else delete document.documentElement.dataset.tema;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", tema === "oscuro" ? "#0e1012" : "#1b1e22");
}

/** Cambia de tema. Si el navegador lo permite, la nueva luz se abre en círculo desde (x, y). */
export function alternarTema(x, y) {
  const nuevo = temaActual() === "oscuro" ? "claro" : "oscuro";
  try {
    localStorage.setItem(CLAVE, nuevo);
  } catch {
    // sin almacenamiento (modo privado): el cambio vale solo para esta visita
  }
  const raiz = document.documentElement;
  if (x != null) {
    raiz.style.setProperty("--tema-x", `${x}px`);
    raiz.style.setProperty("--tema-y", `${y}px`);
  }
  const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (document.startViewTransition && !reducido) document.startViewTransition(() => aplicar(nuevo));
  else aplicar(nuevo);
  window.dispatchEvent(new CustomEvent("cambio-tema", { detail: nuevo }));
  return nuevo;
}
