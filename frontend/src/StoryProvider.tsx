import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { toast } from "sonner";
import { instagramStatus, listStories } from "./api";
import type { InstagramStatus, Story } from "./types";

const POLL_MS = 5000;

type StoryContextValue = {
  stories: Story[];
  ig: InstagramStatus | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const StoryContext = createContext<StoryContextValue | null>(null);

function detectTransitions(prev: Map<string, Story["status"]>, next: Story[]) {
  for (const story of next) {
    const before = prev.get(story.id);
    if (before === undefined) continue;
    if (before === story.status) continue;
    if (story.status === "published") {
      toast.success("Story publicada con éxito");
    } else if (story.status === "failed") {
      const detail = story.error_message ? `: ${story.error_message}` : "";
      toast.error(`No se pudo publicar${detail}`);
    }
  }
}

export function StoryProvider({ children }: { children: ReactNode }) {
  const [stories, setStories] = useState<Story[]>([]);
  const [ig, setIg] = useState<InstagramStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const statusRef = useRef<Map<string, Story["status"]>>(new Map());

  const refresh = useCallback(async () => {
    try {
      const [queue, status] = await Promise.all([listStories(), instagramStatus()]);
      detectTransitions(statusRef.current, queue);
      statusRef.current = new Map(queue.map((s) => [s.id, s.status]));
      setStories(queue);
      setIg(status);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la cola");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    let alive = true;

    const tick = () => {
      if (document.visibilityState !== "visible") return;
      void refresh();
    };

    const id = window.setInterval(tick, POLL_MS);
    const onVisible = () => {
      if (alive && document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      alive = false;
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [refresh]);

  const value = useMemo(
    () => ({ stories, ig, loading, error, refresh }),
    [stories, ig, loading, error, refresh],
  );

  return <StoryContext.Provider value={value}>{children}</StoryContext.Provider>;
}

export function useStories() {
  const ctx = useContext(StoryContext);
  if (!ctx) throw new Error("useStories must be used within StoryProvider");
  return ctx;
}
