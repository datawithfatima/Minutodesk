import { useState } from "react";

export default function Logo({ size = "h-16 w-16" }) {
  const [error, setError] = useState(false);

  if (error) {
    return (
      <div className={`flex ${size} items-center justify-center rounded-xl bg-slate-900 font-bold text-white`}>
        MD
      </div>
    );
  }

  return (
    <img
      src="/img/logo.png"
      alt="MinutoDesk"
      className={`${size} rounded-xl object-cover`}
      onError={() => setError(true)}
    />
  );
}
