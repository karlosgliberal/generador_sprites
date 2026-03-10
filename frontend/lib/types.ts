export interface Avatar {
  id: string;
  description: string;
  character_name: string | null;
  avatar_image_url: string | null;
  created_at: string;
  action_count: number;
}

export interface Action {
  id: string;
  avatar_id: string;
  action_name: string;
  status: "pending" | "generating" | "completed" | "failed" | "cancelled";
  frame_count: number | null;
  strip_url: string | null;
  gif_url: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface Frame {
  id: string;
  frame_index: number;
  image_url: string;
}

export interface SSEEvent {
  event: "frame_complete" | "postprocessing" | "completed" | "error" | "cancelled";
  frame_index?: number;
  total_frames?: number;
  image_url?: string;
  frame_count?: number;
  strip_url?: string;
  gif_url?: string;
  message?: string;
}
