const VARIANTES = {
  gray: "bg-gray-100 text-gray-700",
  amber: "bg-amber-100 text-amber-800",
  sky: "bg-sky-100 text-sky-800",
  green: "bg-green-100 text-green-800",
};

export default function Badge({ color = "gray", children, className = "" }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
        VARIANTES[color] || VARIANTES.gray
      } ${className}`}
    >
      {children}
    </span>
  );
}
