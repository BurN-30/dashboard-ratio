export interface Unit3DStats {
  // Warnings
  warnings_active: string;
  hit_and_run: string;

  // Seed Stats
  seed_time_total: string;
  seed_time_avg: string;
  seed_size: string;

  // Torrent Count
  count_up_non_anon?: string;
  count_up_anon?: string;
  count_up_total?: string;
  count_downloaded: string;
  count_seed: string;
  count_leech: string;
  count_inactive: string;

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
  torrent_downloader_credited?: string;
  torrent_downloader_refunded?: string;

  // Rewards / Points
  points_bonus: string;
  fl_tokens: string;
  thanks_given: string;
  thanks_received?: string;
  
  // Community / Extra
  invitations?: string;
  points_bonus_received?: string;
  points_bonus_given?: string;
  primes_received?: string;
  primes_given?: string;
}

export interface SharewoodStats {
  // Counts
  count_upload: string;
  count_download: string;
  count_seed: string;
  count_leech: string;

  // Traffic
  vol_download: string;
  vol_upload_detail?: string;
  vol_upload: string;
  ratio: string;
  buffer: string;
  freeleech_pool: string;

  // Seed Time
  time_seed_total: string;
  time_seed_avg: string;

  // Extra
  points_bonus: string;
  fl_tokens: string;
  thanks_received: string;
  thanks_given: string;
  hit_and_run: string;
  
  // Warnings
  warnings?: string;
}

export type TrackerData = Unit3DStats | SharewoodStats;

export interface AllStats {
  [key: string]: TrackerData;
  _timestamp?: number;
}
