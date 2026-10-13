export default function Card({ children, className = "" }) {
  return (
    <div
      className={`rounded-xl border border-linea bg-white shadow-[0_1px_2px_rgba(16,27,48,0.04)] ${className}`}
    >
      {children}
    </div>
  );
}

Card.Body = function CardBody({ children, className = "" }) {
  return <div className={`p-4 sm:p-5 ${className}`}>{children}</div>;
};
