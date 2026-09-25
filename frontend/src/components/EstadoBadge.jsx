import Badge from "./ui/Badge";

const COLORES = {
  abierto: "amber",
  en_proceso: "sky",
  resuelto: "green",
};

export default function EstadoBadge({ estado }) {
  return <Badge color={COLORES[estado] || "gray"}>{estado}</Badge>;
}
