export default function Card({ children, className = "" }) {
  return (
    <div className={`rounded-lg border border-gray-200 bg-white shadow-sm ${className}`}>
      {children}
    </div>
  );
}

Card.Body = function CardBody({ children, className = "" }) {
  return <div className={`p-4 ${className}`}>{children}</div>;
};
