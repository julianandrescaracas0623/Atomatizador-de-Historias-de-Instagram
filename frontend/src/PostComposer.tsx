import { Upload } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import { toast } from "sonner";
import dayjs from "dayjs";
import timezone from "dayjs/plugin/timezone";
import utc from "dayjs/plugin/utc";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createPost, type PostKind } from "./api";
import type { Platform } from "./types";
import { defaultScheduleLocal } from "./storyUtils";

dayjs.extend(utc);
dayjs.extend(timezone);

const BOGOTA = "America/Bogota";
const MAX_CAPTION = 2200;
const MAX_LINKEDIN_TEXT = 3000;

const PLATFORM_LABEL: Record<Platform, string> = {
  instagram: "Instagram",
  linkedin: "LinkedIn (feed con 1 imagen, texto obligatorio)",
};

const KIND_LABEL: Record<PostKind, string> = {
  feed: "Feed (1 imagen)",
  reel: "Reel (1 video)",
  carousel: "Carrusel (2 a 10 archivos)",
};

const KIND_ACCEPT: Record<PostKind, string> = {
  feed: "image/jpeg,image/png",
  reel: "video/mp4,video/quicktime",
  carousel: "image/jpeg,image/png,video/mp4,video/quicktime",
};

function isVideo(file: File): boolean {
  return file.type.startsWith("video") || /\.(mp4|mov)$/i.test(file.name);
}

/** Validación rápida en el cliente. El servidor valida de nuevo y es la fuente de verdad. */
function validateFiles(kind: PostKind, files: File[], platform: Platform): string | null {
  if (files.length === 0) return "Elige al menos un archivo";
  if (platform === "linkedin") {
    if (files.length !== 1 || isVideo(files[0])) return "LinkedIn necesita exactamente una imagen";
    return null;
  }
  if (kind === "feed") {
    if (files.length !== 1 || isVideo(files[0])) return "Un feed necesita exactamente una imagen";
  }
  if (kind === "reel") {
    if (files.length !== 1 || !isVideo(files[0])) return "Un Reel necesita exactamente un video";
  }
  if (kind === "carousel" && (files.length < 2 || files.length > 10)) {
    return "Un carrusel necesita entre 2 y 10 archivos";
  }
  return null;
}

export function PostComposer({ onCreated }: { onCreated: () => void | Promise<void> }) {
  const defaults = useMemo(() => {
    const dt = dayjs.tz(defaultScheduleLocal(), BOGOTA);
    return { date: dt.format("YYYY-MM-DD"), time: dt.format("HH:mm") };
  }, []);

  const [platform, setPlatform] = useState<Platform>("instagram");
  const [kind, setKind] = useState<PostKind>("feed");
  const [files, setFiles] = useState<File[]>([]);
  const [caption, setCaption] = useState("");
  const [date, setDate] = useState(defaults.date);
  const [time, setTime] = useState(defaults.time);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function changeKind(next: PostKind) {
    setKind(next);
    setFiles([]);
    setError(null);
  }

  function changePlatform(next: Platform) {
    setPlatform(next);
    setFiles([]);
    setError(null);
    if (next === "linkedin") setKind("feed");
  }

  const isLinkedin = platform === "linkedin";
  const captionLimit = isLinkedin ? MAX_LINKEDIN_TEXT : MAX_CAPTION;

  async function submit(draft: boolean) {
    const problem = validateFiles(kind, files, platform);
    if (problem) {
      setError(problem);
      return;
    }
    if (isLinkedin && !caption.trim()) {
      setError("LinkedIn necesita texto en el post");
      return;
    }
    if (caption.length > captionLimit) {
      setError(`El texto supera ${captionLimit} caracteres`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const when = dayjs.tz(`${date}T${time}`, BOGOTA).format("YYYY-MM-DDTHH:mm");
      await createPost(files, kind, caption, when, draft, platform);
      setFiles([]);
      setCaption("");
      toast.success(draft ? "Borrador guardado para revisión" : "Post programado");
      await onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear el post");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">Crear post</CardTitle>
        <CardDescription>
          Guardar como borrador no publica nada hasta que lo apruebes en la cola.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {error ? (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <form
          className="flex flex-col gap-4"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            void submit(false);
          }}
        >
          <div className="flex flex-col gap-2">
            <Label htmlFor="post-platform">Red</Label>
            <select
              id="post-platform"
              className="min-h-11 rounded-md border bg-background px-3 text-sm"
              value={platform}
              onChange={(e) => changePlatform(e.target.value as Platform)}
            >
              {(Object.keys(PLATFORM_LABEL) as Platform[]).map((key) => (
                <option key={key} value={key}>
                  {PLATFORM_LABEL[key]}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="post-kind">Tipo de post</Label>
            <select
              id="post-kind"
              className="min-h-11 rounded-md border bg-background px-3 text-sm"
              value={kind}
              disabled={isLinkedin}
              onChange={(e) => changeKind(e.target.value as PostKind)}
            >
              {(Object.keys(KIND_LABEL) as PostKind[]).map((key) => (
                <option key={key} value={key}>
                  {KIND_LABEL[key]}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Button variant="outline" className="min-h-11 shrink-0" asChild>
              <label>
                <Upload data-icon="inline-start" />
                {kind === "carousel" ? "Elegir archivos" : "Elegir archivo"}
                <input
                  type="file"
                  className="sr-only"
                  multiple={kind === "carousel" && !isLinkedin}
                  accept={isLinkedin ? "image/jpeg,image/png" : KIND_ACCEPT[kind]}
                  onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
                />
              </label>
            </Button>
            <p className="truncate text-sm text-muted-foreground">
              {files.length === 0
                ? "Ningún archivo elegido"
                : files.length === 1
                  ? files[0].name
                  : `${files.length} archivos`}
            </p>
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="post-caption">Caption</Label>
              <span className="text-xs text-muted-foreground">
                {caption.length}/{captionLimit}
              </span>
            </div>
            <textarea
              id="post-caption"
              className="min-h-24 rounded-md border bg-background px-3 py-2 text-sm"
              value={caption}
              maxLength={captionLimit + 1}
              onChange={(e) => setCaption(e.target.value)}
              placeholder="Escribe el texto del post"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="post-date">Fecha (Bogotá)</Label>
              <Input id="post-date" type="date" className="min-h-11" value={date} onChange={(e) => setDate(e.target.value)} required />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="post-time">Hora (24 h)</Label>
              <Input id="post-time" type="time" className="min-h-11" value={time} onChange={(e) => setTime(e.target.value)} required />
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row">
            <Button type="button" variant="outline" className="min-h-11" disabled={busy} onClick={() => void submit(true)}>
              Guardar borrador
            </Button>
            <Button type="submit" className="min-h-11" disabled={busy}>
              {busy ? "Guardando…" : "Programar post"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
