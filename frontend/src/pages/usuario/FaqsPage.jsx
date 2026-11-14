import { HelpCircle } from "lucide-react";
import Card from "../../components/ui/Card";
import PageHeader from "../../components/ui/PageHeader";

const PREGUNTAS = [
  {
    p: "¿Qué es Minutito y qué puede hacer?",
    r: "Minutito es el asistente virtual de MinutoDesk. Conversas con él como con un chat: te hace preguntas, te da pasos y recuerda lo que ya probaste. Atiende consultas de primer nivel (contraseñas, internet, VPN, impresoras, Office, Teams…). Si no logra resolverlo, o es algo que solo puede hacer el equipo de sistemas, te ayuda a crear el ticket con lo que conversaron.",
  },
  {
    p: "¿Puedo enviarle una captura de pantalla a Minutito?",
    r: "Sí, con el botón de imagen o pegándola en el chat (hasta 3 por conversación). Minutito lee el texto que aparece en la captura, como el mensaje de un error, y lo usa para ayudarte. No ve el resto de la imagen (por ejemplo, una foto de un equipo): en ese caso cuéntale qué muestra. Si se crea el ticket, las capturas van adjuntas para que el equipo de sistemas las vea.",
  },
  {
    p: "¿Cómo creo un ticket?",
    r: "Hay dos formas: desde «Crear ticket», con el formulario, o desde el chat con Minutito en Inicio, pulsando «Crear ticket con esta conversación». En ese caso Minutito redacta la descripción con lo que hablaron y el sistema propone el tipo y la categoría; tú revisas y envías. Conversar con Minutito no crea tickets por sí solo.",
  },
  {
    p: "¿Qué significan los estados de un ticket?",
    r: "Nuevo: recibimos tu consulta y aún no se atiende. En proceso: alguien del equipo de soporte la está trabajando. Resuelto: la consulta quedó cerrada, ya sea por Minutito o por el equipo. Cancelado: el equipo de soporte la cerró sin resolverla (por ejemplo, porque estaba duplicada o ya no hacía falta); en el ticket verás el motivo.",
  },
  {
    p: "¿Qué pasa si Minutito no resuelve mi consulta?",
    r: "Minutito te ofrece crear el ticket con la conversación. El equipo de soporte la ve completa, así que no tendrás que volver a explicar todo.",
  },
  {
    p: "¿Cómo gano puntos?",
    r: "Ganas 10 puntos cuando Minutito resuelve tu consulta y lo confirmas, y 3 puntos si primero lo intentaste con Minutito y luego el equipo de soporte cerró el ticket. Cada 25 puntos tu edificio sube un piso, y tu obra avanza por etapas: Cimientos (0–49), Estructura (50–149), Acabados (150–299) y Entrega de llaves (300 o más). También hay insignias por logros especiales. Lo ves en “Mi obra”, junto con la Ciudad MinutoDesk.",
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
      />
      <div className="flex max-w-3xl flex-col gap-3">
        {PREGUNTAS.map((item) => (
          <Card key={item.p}>
            <details className="group">
              <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium text-noche marker:hidden">
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
