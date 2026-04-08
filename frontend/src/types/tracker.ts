export interface Unit3DStats {
  // Warnings
  warnings_active: string;
  hit_and_run: string;

  // Seed Stats
  seed_time_total: string;
  seed_time_avg: string;
  seed_size: string;

  // Torrent Count
  count_downloaded: string;
  count_seed: string;
  count_leech: string;

  // Traffic
  ratio: string;
  real_ratio: string;
  buffer: string;
  vol_upload: string;
  vol_download: string;

  // Torrent Details
  torrent_uploader?: string;
  torrent_uploader_credited?: string;
  torrent_downloader?: string;

  // Rewards / Points
  points_bonus: string;
  fl_tokens: string;
}

export interface SharewoodStats {
  // Counts
  count_downloaded: string;
  count_seed: string;
  count_leech: string;

  // Traffic
  vol_download: string;
  vol_upload: string;
  ratio: string;
  buffer: string;

  // Seed Time
  seed_time_total: string;
  seed_time_avg: string;

  // Extra
  points_bonus: string;
  fl_tokens: string;
  hit_and_run: string;

  // Warnings
  warnings_active?: string;
  warnings_limit?: string;
}

export type TrackerData = Unit3DStats | SharewoodStats;

export interface AllStats {
  [key: string]: TrackerData | number | undefined;
  _timestamp?: number;
}
