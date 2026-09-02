export type MediaType = "image" | "video";
export type StoryStatus = "pending" | "publishing" | "published" | "failed";

export type Story = {
  id: string;
  filename: string;
  media_type: MediaType;
  scheduled_at: string;
  status: StoryStatus;
  instagram_media_id: string | null;
  error_message: string | null;
  created_at: string;
  media_url: string;
};

export type InstagramStatus = {
  configured: boolean;
  ig_user_id: string | null;
  username: string | null;
  error: string | null;
  quota_usage: number | null;
  quota_total: number | null;
  token_expires_at: string | null;
  token_warning: string | null;
};
