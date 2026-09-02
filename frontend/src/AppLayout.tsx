import { LogOut, Menu } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { AppNavTabs } from "@/components/AppNavTabs";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { logout, me, setToken } from "./api";
import { useStories } from "./StoryProvider";

type AppLayoutProps = {
  children: ReactNode;
};

export function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate();
  const { ig, error } = useStories();
  const [username, setUsername] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    me()
      .then((user) => setUsername(user.username))
      .catch(() => {
        setToken(null);
        navigate("/login", { replace: true });
      });
  }, [navigate]);

  async function onLogout() {
    try {
      await logout();
    } catch {
      /* token se descarta igual */
    }
    setToken(null);
    navigate("/login", { replace: true });
  }

  const userLine = [username, ig?.username ? `@${ig.username}` : null].filter(Boolean).join(" · ");

  return (
    <div className="min-h-dvh w-full bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <div className="mx-auto grid w-full max-w-[90rem] grid-cols-[1fr_auto] items-center gap-4 px-4 py-3 sm:px-6 lg:grid-cols-[1fr_auto_1fr] lg:px-8">
          <p className="text-xl font-semibold text-primary">Automatize Histories</p>

          <div className="hidden justify-self-center lg:block">
            <AppNavTabs />
          </div>

          <div className="flex items-center justify-end gap-2 justify-self-end">
            <ThemeToggle />

            <div className="hidden items-center gap-2 md:flex">
              {userLine ? (
                <span className="max-w-[220px] truncate text-sm text-muted-foreground">{userLine}</span>
              ) : null}
              <Button variant="outline" size="sm" className="min-h-10" onClick={() => void onLogout()}>
                <LogOut data-icon="inline-start" />
                Salir
              </Button>
            </div>

            <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
              <SheetTrigger asChild>
                <Button variant="outline" size="icon" className="size-10 lg:hidden" aria-label="Abrir menú">
                  <Menu className="size-4" />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-[min(100vw-2rem,320px)]">
                <SheetHeader>
                  <SheetTitle>Menú</SheetTitle>
                </SheetHeader>
                <div className="flex flex-col gap-4 px-4 pb-6">
                  {userLine ? <p className="text-sm text-muted-foreground">{userLine}</p> : null}
                  <AppNavTabs vertical onNavigate={() => setMenuOpen(false)} />
                  <Separator />
                  <Button variant="destructive" className="min-h-11 w-full" onClick={() => void onLogout()}>
                    <LogOut data-icon="inline-start" />
                    Cerrar sesión
                  </Button>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[90rem] px-4 py-8 sm:px-6 lg:px-8">
        {ig?.token_warning ? (
          <Alert className="mb-4">
            <AlertDescription>{ig.token_warning}</AlertDescription>
          </Alert>
        ) : null}
        {error ? (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
        {children}
      </main>
    </div>
  );
}
