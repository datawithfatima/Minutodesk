export default function Card({ children, className = "" }) {
  return (
    <div
      className={`lamina rounded-md border border-linea bg-superficie shadow-[0_1px_0_rgb(27_30_34/0.04),0_1px_3px_rgb(27_30_34/0.05)] ${className}`}
    >
      {children}
    </div>
  );
}

Card.Body = function CardBody({ children, className = "" }) {
  return <div className={`p-4 sm:p-5 ${className}`}>{children}</div>;
};
