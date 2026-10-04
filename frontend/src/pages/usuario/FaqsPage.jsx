import { HelpCircle } from "lucide-react";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";

const PREGUNTAS = [
  {
    p: "¿Qué es Minutito y qué puede hacer?",
    r: "Minutito es el asistente virtual de MinutoDesk. Responde consultas de primer nivel (contraseñas, uso de software, orientación básica de hardware) y te da pasos concretos para intentar resolver el problema. Si no logra resolverlo, tu caso queda registrado para que lo atienda una persona del equipo de soporte.",
  },
  {
    p: "¿Cómo creo un ticket?",
    r: "Desde Inicio, escribe tu consulta en el chat con Minutito. El ticket se crea automáticamente con tu primer mensaje y el sistema lo clasifica por tipo y categoría.",
  },
  {
    p: "¿Qué significan los estados de un ticket?",
    r: "Abierto: recibimos tu consulta y aún no se atiende. En proceso: alguien del equipo de soporte la está trabajando. Resuelto: la consulta quedó cerrada, ya sea por Minutito o por el equipo.",
  },
  {
    p: "¿Qué pasa si Minutito no resuelve mi consulta?",
    r: "Minutito te lo indica y tu ticket sigue abierto para el equipo de soporte. Si después de varios intentos con Minutito sigue sin resolverse, el ticket pasa a “en proceso” para que lo tome una persona.",
  },
  {
    p: "¿Cómo gano puntos?",
    r: "Ganas 10 puntos cuando Minutito resuelve tu consulta, y 3 puntos si primero lo intentaste con Minutito y luego el equipo de soporte cerró el ticket. Según tus puntos tu nivel es: Nuevo (0–49), Autosuficiente (50–149) o Experto en autoservicio (150 o más). Lo ves en “Mis logros”.",
  },
  {
    p: "¿Dónde veo mis consultas anteriores?",
    r: "En “Mis tickets” ves todas tus consultas. En “Mi histórico” ves solo las resueltas, con quién las resolvió, cuánto tardó y los puntos que ganaste.",
  },
  {
    p: "¿Por qué mi ticket quedó en una categoría que no es?",
    r: "La clasificación es automática y aproximada: el sistema la predice a partir de lo que escribiste. El equipo de soporte revisa cada caso, así que una categoría imprecisa no afecta la atención.",
  },
  {
    p: "¿Qué hago si olvidé mi contraseña?",
    r: "En la pantalla de inicio de sesión usa “¿Olvidaste tu contraseña?”. Te enviaremos por correo un enlace de un solo uso que vence en 30 minutos.",
  },
];

export default function FaqsPage() {
  return (
    <>
      <PageHeader
        icon={HelpCircle}
        title="Preguntas frecuentes"
        subtitle="Respuestas rápidas sobre cómo usar MinutoDesk."
      />
      <div className="flex max-w-3xl flex-col gap-3">
        {PREGUNTAS.map((item) => (
          <Card key={item.p}>
            <details className="group">
              <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium text-gray-900 marker:hidden">
                <span className="mr-2 inline-block text-gray-400 transition-transform group-open:rotate-90">
                  ›
                </span>
                {item.p}
              </summary>
              <p className="px-4 pb-4 text-sm leading-relaxed text-gray-600">{item.r}</p>
            </details>
          </Card>
        ))}
      </div>
    </>
  );
}
