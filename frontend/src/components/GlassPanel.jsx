import { motion, useReducedMotion } from "framer-motion";

// Frosted surface primitive. Shares Card's API (className + children, spreads
// ...rest) so `Card` can wrap it and every existing card frosts over with no
// per-site edits. Hover is opt-in and gentle, so dense/mechanical cards stay
// static and readable; only KPI / feed / interactive cards pass `hover`.
export default function GlassPanel({ className = "", children, hover = false, ...rest }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={`rounded-lg border border-border bg-card shadow-sm backdrop-blur-lg ${className}`}
      whileHover={hover && !reduce ? { y: -2, scale: 1.01 } : undefined}
      transition={{ type: "spring", stiffness: 300, damping: 26 }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}
