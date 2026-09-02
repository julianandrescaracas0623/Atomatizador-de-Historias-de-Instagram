import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { deleteStory } from "./api";
import { DeleteConfirmDialog, StoryList } from "./StoryComponents";
import { useStories } from "./StoryProvider";
import { filterHistory } from "./storyUtils";
import type { Story } from "./types";

export function HistoryPage() {
  const { stories, loading, refresh } = useStories();
  const history = useMemo(() => filterHistory(stories), [stories]);
  const [deleteTarget, setDeleteTarget] = useState<Story | null>(null);

  async function onDeleteConfirm() {
    if (!deleteTarget) return;
    await deleteStory(deleteTarget.id);
    toast.info("Eliminada del historial");
    await refresh();
    setDeleteTarget(null);
  }

  return (
    <div className="mx-auto w-full max-w-[90rem]">
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Historial</CardTitle>
          <CardDescription>
            Stories publicadas o fallidas. Puedes eliminarlas para limpiar el registro.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <StoryList
              stories={history}
              emptyMessage="Aún no hay historial. Cuando una Story se publique o falle, aparecerá aquí."
              actionLabel="Eliminar"
              onAction={setDeleteTarget}
            />
          )}
        </CardContent>
      </Card>

      <DeleteConfirmDialog
        open={deleteTarget !== null}
        title="Eliminar del historial"
        message="¿Eliminar esta Story del historial? También se borrará el archivo local."
        confirmLabel="Eliminar"
        onClose={() => setDeleteTarget(null)}
        onConfirm={onDeleteConfirm}
      />
    </div>
  );
}
