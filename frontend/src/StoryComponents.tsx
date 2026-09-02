import { useState } from "react";
import { MagicCard, MagicCardContent } from "@/components/ui/magic-card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { formatWhen, STATUS_BADGE, STATUS_LABEL } from "./storyUtils";
import type { Story } from "./types";

type DeleteConfirmDialogProps = {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  onClose: () => void;
  onConfirm: () => Promise<void>;
};

export function DeleteConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  onClose,
  onConfirm,
}: DeleteConfirmDialogProps) {
  const [busy, setBusy] = useState(false);

  async function handleConfirm() {
    setBusy(true);
    try {
      await onConfirm();
      onClose();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(value) => !value && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{message}</DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={onClose} disabled={busy}>
            Volver
          </Button>
          <Button variant="destructive" onClick={() => void handleConfirm()} disabled={busy}>
            {busy ? "…" : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

type StoryListProps = {
  stories: Story[];
  emptyMessage: string;
  actionLabel?: string;
  onAction?: (story: Story) => void;
  actionDisabled?: (story: Story) => boolean;
};

export function StoryList({ stories, emptyMessage, actionLabel, onAction, actionDisabled }: StoryListProps) {
  if (stories.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">{emptyMessage}</p>;
  }

  return (
    <ul className="flex flex-col divide-y divide-border">
      {stories.map((item) => (
        <li key={item.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 flex-1 gap-3">
            <Avatar className="size-16 shrink-0 rounded-md sm:size-20">
              {item.media_type === "video" ? (
                <video src={item.media_url} muted className="size-full object-cover" />
              ) : (
                <>
                  <AvatarImage src={item.media_url} alt="" className="object-cover" />
                  <AvatarFallback>IG</AvatarFallback>
                </>
              )}
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="text-base font-medium">{formatWhen(item.scheduled_at)}</p>
              <Badge variant="outline" className={cn("mt-2", STATUS_BADGE[item.status])}>
                {STATUS_LABEL[item.status]}
              </Badge>
              {item.error_message ? (
                <p className="mt-2 text-sm text-destructive">{item.error_message}</p>
              ) : null}
            </div>
          </div>
          {actionLabel && onAction ? (
            <Button
              variant="outline"
              size="sm"
              className="min-h-10 shrink-0 self-start border-destructive/40 text-destructive hover:bg-destructive/10"
              onClick={() => onAction(item)}
              disabled={actionDisabled?.(item)}
            >
              {actionLabel}
            </Button>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

type StoryPreviewProps = {
  src: string | null;
  isVideo: boolean;
  caption?: string | null;
  placeholder?: string;
};

export function StoryPreview({ src, isVideo, caption, placeholder }: StoryPreviewProps) {
  return (
    <div className="mx-auto flex w-full max-w-[380px] flex-col items-center">
      <MagicCard className="w-full">
        <MagicCardContent className="p-3 sm:p-4">
          <div className="mx-auto aspect-[9/16] w-full overflow-hidden rounded-lg bg-black/40">
            {src ? (
              isVideo ? (
                <video src={src} muted playsInline className="size-full object-cover" />
              ) : (
                <img src={src} alt="Vista previa 9:16" className="size-full object-cover" />
              )
            ) : (
              <div className="flex size-full items-center justify-center px-4 text-center text-sm text-neutral-400">
                {placeholder ?? "Vista previa 9:16"}
              </div>
            )}
          </div>
        </MagicCardContent>
      </MagicCard>
      {caption ? <p className="mt-2 text-center text-xs text-muted-foreground">{caption}</p> : null}
    </div>
  );
}
