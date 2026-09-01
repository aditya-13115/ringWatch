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
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";

import Logo from "../components/Logo";
import AmbientBackground from "./AmbientBackground";

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

  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;

    const stored = localStorage.getItem("sidebarCollapsed");
    return stored === "true";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);

    try {
      localStorage.setItem("theme", dark ? "dark" : "light");
    } catch {
      /* storage unavailable — theme still applies for this session */
    }
  }, [dark]);

  useEffect(() => {
    try {
      localStorage.setItem(
        "sidebarCollapsed",
        sidebarCollapsed ? "true" : "false"
      );
    } catch {
      /* storage unavailable — state still applies for this session */
    }
  }, [sidebarCollapsed]);

  const toggleSidebar = () => {
    setSidebarCollapsed((current) => !current);
  };

  return (
    <div className="relative flex h-screen overflow-hidden bg-background text-foreground">
      <AmbientBackground />

      {/* SIDEBAR */}
      <aside
        className={[
          "relative z-10 shrink-0 border-r border-border bg-card backdrop-blur-lg flex flex-col",
          "transition-[width] duration-300 ease-in-out",
          sidebarCollapsed ? "w-16" : "w-56",
        ].join(" ")}
      >
        {/* Logo / Toggle */}
        <div
          className={[
            "h-16 flex items-center border-b border-border",
            sidebarCollapsed
              ? "justify-center px-2"
              : "justify-between px-4",
          ].join(" ")}
        >
          {!sidebarCollapsed && <Logo size="md" />}

          {sidebarCollapsed && (
            <button
              type="button"
              onClick={toggleSidebar}
              aria-label="Expand sidebar"
              title="Expand sidebar"
              className="flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              <PanelLeftOpen className="h-5 w-5" />
            </button>
          )}

          {!sidebarCollapsed && (
            <button
              type="button"
              onClick={toggleSidebar}
              aria-label="Collapse sidebar"
              title="Collapse sidebar"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-2 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              title={sidebarCollapsed ? item.label : undefined}
              className={({ isActive }) =>
                [
                  "flex items-center rounded-md text-sm font-medium transition-all duration-200",
                  sidebarCollapsed
                    ? "justify-center px-2 py-2.5"
                    : "gap-2 px-3 py-2",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                ].join(" ")
              }
            >
              <item.icon className="h-4 w-4 shrink-0" />

              {!sidebarCollapsed && (
                <span className="truncate">{item.label}</span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Theme Toggle */}
        <div className="border-t border-border p-2">
          <button
            type="button"
            onClick={() => setDark(!dark)}
            title={sidebarCollapsed ? (dark ? "Light Mode" : "Dark Mode") : undefined}
            className={[
              "w-full flex items-center rounded-md text-sm text-muted-foreground",
              "hover:bg-accent hover:text-accent-foreground transition-colors",
              sidebarCollapsed
                ? "justify-center px-2 py-2.5"
                : "gap-2 px-3 py-2",
            ].join(" ")}
          >
            {dark ? (
              <Sun className="h-4 w-4 shrink-0" />
            ) : (
              <Moon className="h-4 w-4 shrink-0" />
            )}

            {!sidebarCollapsed && (
              <span>{dark ? "Light Mode" : "Dark Mode"}</span>
            )}
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="relative z-10 min-w-0 flex-1 overflow-y-auto">
        <header className="sticky top-0 z-20 h-16 border-b border-border bg-card/60 backdrop-blur-lg flex items-center px-6">
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