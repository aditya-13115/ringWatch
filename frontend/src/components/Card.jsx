export default function Card({ className = "", children }) {
  return (
    <div className={`rounded-lg border border-border bg-card shadow-sm ${className}`}>
      {children}
    </div>
  );
}