import { Upload } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { toast } from "sonner";
import dayjs from "dayjs";
import timezone from "dayjs/plugin/timezone";
import utc from "dayjs/plugin/utc";
import "dayjs/locale/es";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { approveStory, createStory, deleteStory, publicUrl } from "./api";
import { DeleteConfirmDialog, StoryList, StoryPreview } from "./StoryComponents";
import { useStories } from "./StoryProvider";
import { defaultScheduleLocal, filterQueue, formatWhen } from "./storyUtils";
import type { Story } from "./types";

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.locale("es");

const BOGOTA = "America/Bogota";

function defaultScheduleParts() {
  const dt = dayjs.tz(defaultScheduleLocal(), BOGOTA);
  return { date: dt.toDate(), time: dt.format("HH:mm") };
}

export function QueuePage() {
  const { stories, ig, loading, refresh } = useStories();
  const queue = useMemo(() => filterQueue(stories), [stories]);

  const [file, setFile] = useState<File | null>(null);
  const [scheduleDate, setScheduleDate] = useState<Date>(() => defaultScheduleParts().date);
  const [scheduleTime, setScheduleTime] = useState(() => defaultScheduleParts().time);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Story | null>(null);
  const [calendarOpen, setCalendarOpen] = useState(false);

  const nextUp = useMemo(() => queue.find((item) => item.status === "pending") ?? queue[0] ?? null, [queue]);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const plateSrc = previewUrl ?? (nextUp ? publicUrl(nextUp.media_url) : null);
  const plateIsVideo = file ? file.type.startsWith("video") : nextUp?.media_type === "video";

  async function onSchedule(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      setError("Elige una imagen o un video");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const datePart = dayjs(scheduleDate).format("YYYY-MM-DD");
      const when = dayjs.tz(`${datePart}T${scheduleTime}`, BOGOTA).format("YYYY-MM-DDTHH:mm");
      await createStory(file, when);
      setFile(null);
      const defaults = defaultScheduleParts();
      setScheduleDate(defaults.date);
      setScheduleTime(defaults.time);
      toast.success("Story programada");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo programar");
    } finally {
      setBusy(false);
    }
  }

  const drafts = useMemo(() => stories.filter((s) => s.status === "draft"), [stories]);

  async function onApprove(story: Story) {
    try {
      await approveStory(story.id);
      toast.success("Borrador aprobado y programado");
      await refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "No se pudo aprobar");
    }
  }

  async function onCancelConfirm() {
    if (!deleteTarget) return;
    await deleteStory(deleteTarget.id);
    toast.info("Story cancelada");
    await refresh();
    setDeleteTarget(null);
  }

  return (
    <div className="mx-auto grid w-full max-w-[90rem] grid-cols-1 gap-10 lg:grid-cols-[minmax(300px,400px)_1fr] lg:items-start">
      <div className="flex justify-center">
        <StoryPreview
          src={plateSrc}
          isVideo={plateIsVideo}
          caption={nextUp && !previewUrl ? formatWhen(nextUp.scheduled_at) : null}
          placeholder="La próxima Story en cola aparece aquí."
        />
      </div>

      <div className="flex flex-col gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Programar Story</CardTitle>
            <CardDescription>Horario en America/Bogota. Instagram descarga el archivo por HTTPS.</CardDescription>
          </CardHeader>
          <CardContent>
            {error ? (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            ) : null}
            <form onSubmit={onSchedule} className="flex flex-col gap-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <Button variant="outline" className="min-h-11 shrink-0" asChild>
                  <label>
                    <Upload data-icon="inline-start" />
                    Elegir archivo
                    <input
                      type="file"
                      className="sr-only"
                      accept="image/jpeg,image/png,video/mp4,video/quicktime"
                      onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    />
                  </label>
                </Button>
                <p className="truncate text-sm text-muted-foreground">
                  {file ? file.name : "JPEG, PNG, MP4 o MOV"}
                </p>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-2">
                  <Label>Fecha (Bogotá)</Label>
                  <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
                    <PopoverTrigger asChild>
                      <Button variant="outline" className={cn("min-h-11 w-full justify-start font-normal")}>
                        {dayjs(scheduleDate).format("DD MMM YYYY")}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={scheduleDate}
                        onSelect={(date) => {
                          if (date) setScheduleDate(date);
                          setCalendarOpen(false);
                        }}
                      />
                    </PopoverContent>
                  </Popover>
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="schedule-time">Hora (24 h)</Label>
                  <Input
                    id="schedule-time"
                    type="time"
                    className="min-h-11"
                    value={scheduleTime}
                    onChange={(e) => setScheduleTime(e.target.value)}
                    required
                  />
                </div>
              </div>

              <Button type="submit" className="min-h-11 w-full sm:w-auto" disabled={busy}>
                {busy ? "Programando…" : "Programar Story"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {drafts.length > 0 ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Borradores por aprobar</CardTitle>
              <CardDescription>Nada se publica hasta que lo apruebes aquí.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {drafts.map((draft) => (
                <div key={draft.id} className="flex flex-col gap-3 rounded-md border p-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="text-sm font-medium">
                      {draft.media_type === "video" ? "Video" : "Imagen"} · {formatWhen(draft.scheduled_at)}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">{draft.filename}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button className="min-h-11" onClick={() => onApprove(draft)}>
                      Aprobar
                    </Button>
                    <Button variant="outline" className="min-h-11" onClick={() => setDeleteTarget(draft)}>
                      Descartar
                    </Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Cola activa</CardTitle>
            {ig?.username && ig.quota_total != null ? (
              <CardDescription>
                @{ig.username} · {ig.quota_usage ?? 0}/{ig.quota_total} publicaciones Graph en 24 h
              </CardDescription>
            ) : null}
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-sm text-muted-foreground">Cargando…</p>
            ) : (
              <StoryList
                stories={queue}
                emptyMessage="No hay nada en cola. Programa la primera Story."
                actionLabel="Cancelar"
                onAction={setDeleteTarget}
                actionDisabled={(story) => story.status !== "pending"}
              />
            )}
          </CardContent>
        </Card>
      </div>

      <DeleteConfirmDialog
        open={deleteTarget !== null}
        title="Cancelar Story"
        message="¿Cancelar esta Story pendiente? Se eliminará de la cola."
        confirmLabel="Cancelar Story"
        onClose={() => setDeleteTarget(null)}
        onConfirm={onCancelConfirm}
      />
    </div>
  );
}
