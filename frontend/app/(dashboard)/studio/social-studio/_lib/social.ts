/** Shapes and constants shared by the Social pages. They mirror the FastAPI responses. */

export const SCHEDULE_PLATFORMS = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "x", label: "X" },
  { value: "instagram", label: "Instagram" },
  { value: "facebook", label: "Facebook" },
] as const;

export type QueuePost = {
  id: number;
  platform: string;
  text?: string;
  text_preview?: string;
  publish_at?: string | null;
  status: string;
  approval_status?: string;
  media_urls?: string[];
  updated_at?: string;
};

export type SocialAccount = {
  id: number;
  network: string;
  network_label: string;
  account_name: string;
  handle: string;
  oauth_status: string;
  oauth_provider?: string;
  followers?: number;
  connected_at?: string;
};

export function platformLabel(value: string): string {
  return SCHEDULE_PLATFORMS.find((item) => item.value === value)?.label ?? value.charAt(0).toUpperCase() + value.slice(1);
}

export function postText(post: QueuePost): string {
  return (post.text ?? post.text_preview ?? "").trim();
}
