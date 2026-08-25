import { NavLink } from "react-router-dom";
import { LayoutDashboard, Search, ScrollText, Activity, AlertTriangle, MapPin } from "lucide-react";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/audit", label: "Audit Log", icon: ScrollText },
  { to: "/metrics", label: "Metrics", icon: Activity },
  { to: "/failure-demo", label: "Failure Demo", icon: AlertTriangle },
  { to: "/address-normalization", label: "Address Normalization", icon: MapPin },
];

export default function Layout({ children }) {
  return (
    <div className="flex h-screen bg-background text-foreground">
      <aside className="w-56 border-r border-border bg-card">
        <div className="h-16 flex items-center px-4 border-b border-border font-semibold text-lg">
          RingWatch
        </div>
        <nav className="p-2 space-y-1">
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
      </aside>
      <main className="flex-1 overflow-y-auto">
        <header className="h-16 border-b border-border flex items-center px-6">
          <h1 className="text-sm font-medium text-muted-foreground">
            Post-delivery abuse investigation
          </h1>
        </header>
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}