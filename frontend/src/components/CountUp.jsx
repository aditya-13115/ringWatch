import { useEffect } from "react";
import { animate, useMotionValue, useTransform, motion, useReducedMotion } from "framer-motion";

// Animates only when `value` changes, from the current value -> new value.
// On polling that means 120 -> 123, never 120 -> 0 -> 123. First mount runs
// 0 -> value. Reduced motion jumps straight to the final value.
export default function CountUp({ value, duration = 1, decimals = 0, prefix = "", suffix = "" }) {
  const reduce = useReducedMotion();
  const mv = useMotionValue(reduce ? value : 0);
  const text = useTransform(mv, (v) =>
    `${prefix}${Number(v).toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    })}${suffix}`
  );

  useEffect(() => {
    if (reduce) {
      mv.set(value);
      return;
    }
    const controls = animate(mv, value, { duration, ease: "easeOut" });
    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return <motion.span>{text}</motion.span>;
}
