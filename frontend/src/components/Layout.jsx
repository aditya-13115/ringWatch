import Logo from "../components/Logo";
import AmbientBackground from "./AmbientBackground";
import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Radar,
  Search,
  ScrollText,
  Activity,
  AlertTriangle,
  MapPin,
  Moon,
  Sun,
  Info,
} from "lucide-react";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/live", label: "Live Ops", icon: Radar },
  { to: "/rings", label: "Ring Network", icon: Search },
  { to: "/audit", label: "Audit Log", icon: ScrollText },
  { to: "/metrics", label: "Metrics", icon: Activity },
  { to: "/failure-demo", label: "Failure Demo", icon: AlertTriangle },
  { to: "/address-normalization", label: "Address Normalization", icon: MapPin },
  { to: "/about", label: "About", icon: Info },
];

export default function Layout() {
  const [dark, setDark] = useState(() => {
    if (typeof window === "undefined") return true;
    const stored = localStorage.getItem("theme");
    return stored === null ? true : stored === "dark";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try {
      localStorage.setItem("theme", dark ? "dark" : "light");
    } catch {
      /* storage unavailable — theme still applies for this session */
    }
  }, [dark]);

  return (
    <div className="relative flex h-screen overflow-hidden bg-background text-foreground">
      <AmbientBackground />
      <aside className="relative z-10 w-56 border-r border-border bg-card backdrop-blur-lg flex flex-col">
        <div className="h-16 flex items-center px-4 border-b border-border">
          <Logo size="md" />
        </div>
        <nav className="p-2 space-y-1 flex-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-2 border-t border-border">
          <button
            onClick={() => setDark(!dark)}
            className="w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          >
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {dark ? "Light Mode" : "Dark Mode"}
          </button>
        </div>
      </aside>
      <main className="relative z-10 flex-1 overflow-y-auto">
        <header className="h-16 border-b border-border bg-card/60 backdrop-blur-lg flex items-center px-6">
          <h1 className="text-sm font-medium text-muted-foreground">
            Post-delivery abuse investigation
          </h1>
        </header>
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}