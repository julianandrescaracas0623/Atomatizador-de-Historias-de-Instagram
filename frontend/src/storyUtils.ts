import type { Story, StoryStatus } from "./types";

export const STATUS_LABEL: Record<StoryStatus, string> = {
  pending: "Pendiente",
  publishing: "Publicando",
  published: "Publicada",
  failed: "Fallida",
};

export const STATUS_BADGE: Record<StoryStatus, string> = {
  pending: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  publishing: "border-sky-500/40 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  published: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  failed: "border-destructive/40 bg-destructive/10 text-destructive",
};

export function formatWhen(iso: string): string {
  return new Intl.DateTimeFormat("es-CO", {
    timeZone: "America/Bogota",
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function defaultScheduleLocal(): string {
  const date = new Date(Date.now() + 60 * 60 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function sortByScheduledAt(stories: Story[]): Story[] {
  return [...stories].sort(
    (a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime(),
  );
}

export function filterQueue(stories: Story[]): Story[] {
  return sortByScheduledAt(stories.filter((s) => s.status === "pending" || s.status === "publishing"));
}

export function filterHistory(stories: Story[]): Story[] {
  return sortByScheduledAt(stories.filter((s) => s.status === "published" || s.status === "failed")).reverse();
}
