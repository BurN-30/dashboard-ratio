export interface PlexLibrary {
  title: string;
  type: string;
  count: number;
}

export interface PlexData {
  libraries: PlexLibrary[];
  active_streams: number;
}

export interface RadarrDisk {
  path: string;
  free_gb: number;
  total_gb: number;
}

export interface RadarrUpcoming {
  title: string;
  year: number;
  status: string;
}

export interface RadarrData {
  total_movies: number;
  monitored: number;
  queue_count: number;
  disk_space: RadarrDisk[];
  upcoming: RadarrUpcoming[];
}

export interface SonarrUpcoming {
  series: string;
  title: string;
  season: number;
  episode: number;
  air_date: string;
}

export interface SonarrData {
  total_series: number;
  monitored: number;
  total_episodes: number;
  queue_count: number;
  upcoming: SonarrUpcoming[];
}

export interface TautulliSession {
  user: string;
  title: string;
  state: string;
  progress: string;
  quality: string;
  player: string;
}

export interface TautulliMostWatched {
  title: string;
  total_plays: number;
}

export interface TautulliData {
  stream_count: number;
  total_bandwidth_mbps: number;
  sessions: TautulliSession[];
  most_watched: TautulliMostWatched[];
}

export interface MediaOverview {
  plex: PlexData | null;
  radarr: RadarrData | null;
  sonarr: SonarrData | null;
  tautulli: TautulliData | null;
}
