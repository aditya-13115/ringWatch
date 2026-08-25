import { Link } from "react-router-dom";
import { motion } from "framer-motion";

export default function Landing() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Animated graph background */}
      <div className="absolute inset-0 -z-10 opacity-10">
        <svg className="w-full h-full" viewBox="0 0 800 600">
          {[...Array(20)].map((_, i) => (
            <circle
              key={i}
              cx={Math.random() * 800}
              cy={Math.random() * 600}
              r={3}
              className="fill-foreground"
            />
          ))}
          <path
            d="M100,100 L300,200 L500,100 L700,300 L600,500 L200,400 Z"
            stroke="currentColor"
            strokeWidth="1"
            fill="none"
            className="animate-pulse"
          />
        </svg>
      </div>

      <div className="container mx-auto px-6 py-24 text-center">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-5xl md:text-7xl font-bold tracking-tight"
        >
          RingWatch
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto"
        >
          Post-delivery refund abuse detection through cross-account graph analysis.
        </motion.p>
        <div className="mt-8 flex gap-4 justify-center">
          <Link
            to="/dashboard"
            className="rounded-md bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            Open Dashboard
          </Link>
          <Link
            to="/about"
            className="rounded-md border border-border px-6 py-3 text-sm font-medium hover:bg-accent"
          >
            Learn More
          </Link>
        </div>
      </div>
    </div>
  );
}