import Card from "./Card";

export default function PageHeader({ icon: Icon, title, subtitle }) {
  return (
    <Card className="mb-4">
      <Card.Body className="flex items-start gap-3">
        <Icon className="mt-0.5 shrink-0 text-gray-700" size={22} />
        <div>
          <h1 className="text-lg font-bold text-gray-900">{title}</h1>
          {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
        </div>
      </Card.Body>
    </Card>
  );
}
