const VARIANTES = {
  gray: "bg-gray-100 text-gray-700 ring-gray-200",
  amber: "bg-amber-50 text-amber-800 ring-amber-200",
  sky: "bg-sky-50 text-sky-800 ring-sky-200",
  green: "bg-green-50 text-green-800 ring-green-200",
};

export default function Badge({ color = "gray", children, className = "" }) {
  return (
    <span
      className={`inline-flex max-w-full items-center rounded px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
        VARIANTES[color] || VARIANTES.gray
      } ${className}`}
    >
      {children}
    </span>
  );
}
