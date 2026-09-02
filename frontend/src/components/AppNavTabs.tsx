import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";

const tabs = [
  { to: "/", label: "Cola" },
  { to: "/historial", label: "Historial" },
] as const;

type AppNavTabsProps = {
  className?: string;
  onNavigate?: () => void;
  vertical?: boolean;
};

export function AppNavTabs({ className, onNavigate, vertical }: AppNavTabsProps) {
  const location = useLocation();

  return (
    <nav
      className={cn(
        vertical ? "flex w-full flex-col gap-1" : "flex flex-wrap gap-1 rounded-lg bg-muted p-1",
        className,
      )}
    >
      {tabs.map((tab) => {
        const active =
          tab.to === "/"
            ? location.pathname === "/"
            : location.pathname.startsWith(tab.to);
        return (
          <Link
            key={tab.to}
            to={tab.to}
            onClick={onNavigate}
            className={cn(
              "inline-flex min-h-11 items-center justify-center rounded-md px-4 text-sm font-medium transition-colors",
              vertical ? "w-full justify-start" : "",
              active
                ? vertical
                  ? "bg-accent text-accent-foreground"
                  : "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
