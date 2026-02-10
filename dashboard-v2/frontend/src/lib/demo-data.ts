/**
 * Mock data for demo/preview mode.
 * Used when NEXT_PUBLIC_DEMO=true (e.g. Vercel preview deployment).
 */
import { AllStats } from "@/types/tracker";

const now = Math.floor(Date.now() / 1000);

export const DEMO_STATS: AllStats = {
  _timestamp: now,
  "Tracker Alpha": {
    ratio: "4.82",
    buffer: "128.5 Go",
    vol_upload: "256.3 Go",
    vol_download: "53.2 Go",
    points_bonus: "42,850",
    fl_tokens: "3",
    count_seed: "47",
    count_leech: "0",
    count_downloaded: "52",
    seed_time_total: "182j 14h 32min",
    seed_time_avg: "3j 12h 8min",
    warnings_active: "0",
    hit_and_run: "0",
    real_ratio: "4.82",
    seed_size: "312.7 Go",
  },
  "Tracker Bravo": {
    ratio: "2.15",
    buffer: "45.8 Go",
    vol_upload: "85.6 Go",
    vol_download: "39.8 Go",
    points_bonus: "18,200",
    fl_tokens: "7",
    count_seed: "23",
    count_leech: "1",
    count_downloaded: "31",
    seed_time_total: "95j 6h 11min",
    seed_time_avg: "3j 1h 30min",
    warnings_active: "0",
    hit_and_run: "0",
    real_ratio: "2.15",
    seed_size: "156.2 Go",
  },
  "Tracker Charlie": {
    ratio: "12.67",
    buffer: "89.3 Go",
    vol_upload: "96.4 Go",
    vol_download: "7.61 Go",
    points_bonus: "0",
    fl_tokens: "0",
    count_seed: "12",
    count_leech: "0",
    count_downloaded: "8",
    seed_time_total: "64j 3h 45min",
    seed_time_avg: "5j 8h 12min",
    warnings_active: "0",
    hit_and_run: "0",
    real_ratio: "12.67",
    seed_size: "78.9 Go",
  },
  "Tracker Delta": {
    ratio: "1.03",
    buffer: "2.4 Go",
    vol_upload: "78.2 Go",
    vol_download: "75.8 Go",
    points_bonus: "5,430",
    fl_tokens: "0",
    count_seed: "8",
    count_leech: "0",
    count_downloaded: "15",
    seed_time_total: "42j 18h 5min",
    seed_time_avg: "2j 20h 33min",
    warnings_active: "0",
    hit_and_run: "0",
  },
};

// Generate fake history (30 data points over ~30 days)
function generateHistory(): AllStats[] {
  const history: AllStats[] = [];
  const trackers = Object.keys(DEMO_STATS).filter(k => k !== "_timestamp");
  const baseTs = now - 30 * 24 * 3600;

  for (let i = 0; i < 30; i++) {
    const ts = baseTs + i * 24 * 3600;
    const entry: AllStats = { _timestamp: ts };

    for (const name of trackers) {
      const base = DEMO_STATS[name] as unknown as Record<string, string>;
      const baseRatio = parseFloat(base.ratio);
      const drift = baseRatio * (0.85 + (i / 30) * 0.15);
      const baseBuffer = parseFloat(base.buffer);
      const bufferDrift = baseBuffer * (0.7 + (i / 30) * 0.3);

      entry[name] = {
        ...base,
        ratio: drift.toFixed(2),
        buffer: `${bufferDrift.toFixed(1)} Go`,
      } as any;
    }

    history.push(entry);
  }

  return history;
}

export const DEMO_HISTORY: AllStats[] = generateHistory();
