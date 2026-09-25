const VARIANTES = {
  danger: "bg-red-50 text-red-800 border-red-200",
  success: "bg-green-50 text-green-800 border-green-200",
  secondary: "bg-gray-50 text-gray-700 border-gray-200",
  info: "bg-sky-50 text-sky-800 border-sky-200",
  warning: "bg-amber-50 text-amber-800 border-amber-200",
};

export default function Alert({ variant = "secondary", children, className = "" }) {
  return (
    <div
      className={`rounded-md border px-4 py-3 text-sm ${
        VARIANTES[variant] || VARIANTES.secondary
      } ${className}`}
    >
      {children}
    </div>
  );
}
