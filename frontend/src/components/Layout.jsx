import Logo from "../components/Logo";
import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
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
  { to: "/rings", label: "Ring Network", icon: Search },
  { to: "/audit", label: "Audit Log", icon: ScrollText },
  { to: "/metrics", label: "Metrics", icon: Activity },
  { to: "/failure-demo", label: "Failure Demo", icon: AlertTriangle },
  { to: "/address-normalization", label: "Address Normalization", icon: MapPin },
  { to: "/about", label: "About", icon: Info },
];

export default function Layout() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  return (
    <div className="flex h-screen bg-background text-foreground">
      <aside className="w-56 border-r border-border bg-card flex flex-col">
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
      <main className="flex-1 overflow-y-auto">
        <header className="h-16 border-b border-border flex items-center px-6">
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