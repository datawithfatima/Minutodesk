export default function Spinner({ size = "md", className = "" }) {
  const dim = size === "sm" ? "h-4 w-4 border-2" : "h-8 w-8 border-4";
  return (
    <span
      className={`inline-block animate-spin rounded-full border-current border-t-transparent ${dim} ${className}`}
      role="status"
      aria-label="Cargando"
    />
  );
}
