import logo from "../assets/ringwatch-logo.png";

export default function Logo({ size = "md", showName = true }) {
  const sizes = {
    sm: "h-7 w-7",
    md: "h-9 w-9",
    lg: "h-16 w-16",
    xl: "h-24 w-24",
  };

  return (
    <div className="flex items-center gap-2">
      <img
        src={logo}
        alt="RingWatch"
        className={`${sizes[size]} object-contain`}
      />

      {showName && (
        <span className="font-semibold tracking-tight">
          RingWatch
        </span>
      )}
    </div>
  );
}