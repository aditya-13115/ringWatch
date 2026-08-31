import { motion, useReducedMotion } from "framer-motion";
import { AMBIENT_BLOBS } from "../constants";

// Single ambient layer behind the whole shell: an opaque base (bg-background)
// with exactly three large, slow, blurred blobs in the app's own edge-link
// colors (device blue / ip violet / address teal). Frosted panels + backdrop
// blur reveal it. Reduced motion -> static. No additional gradients.
const BLOBS = [
  { color: AMBIENT_BLOBS[0], className: "-top-32 -left-24 h-[42rem] w-[42rem]", drift: { x: [0, 60, 0], y: [0, 40, 0] } },
  { color: AMBIENT_BLOBS[1], className: "top-1/3 -right-32 h-[38rem] w-[38rem]", drift: { x: [0, -50, 0], y: [0, 60, 0] } },
  { color: AMBIENT_BLOBS[2], className: "-bottom-40 left-1/4 h-[36rem] w-[36rem]", drift: { x: [0, 40, 0], y: [0, -40, 0] } },
];

export default function AmbientBackground() {
  const reduce = useReducedMotion();
  return (
    <div className="absolute inset-0 -z-10 overflow-hidden bg-background pointer-events-none" aria-hidden="true">
      {BLOBS.map((blob, i) => (
        <motion.div
          key={i}
          className={`absolute rounded-full blur-3xl opacity-25 dark:opacity-30 ${blob.className}`}
          style={{ background: `radial-gradient(circle, ${blob.color} 0%, transparent 70%)` }}
          animate={reduce ? undefined : blob.drift}
          transition={
            reduce
              ? undefined
              : { duration: 26 + i * 6, repeat: Infinity, repeatType: "mirror", ease: "easeInOut" }
          }
        />
      ))}
    </div>
  );
}
