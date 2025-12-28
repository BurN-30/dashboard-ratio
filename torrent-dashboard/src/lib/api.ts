import { AllStats } from "@/types/tracker";

export async function fetchTorrentStats(): Promise<AllStats | null> {
  try {
    const response = await fetch("https://submedial-bloodlike-sarah.ngrok-free.dev/torrent/stats", {
      cache: "no-store",
      headers: {
        "ngrok-skip-browser-warning": "true",
      },
    });

    if (!response.ok) {
      console.error("Failed to fetch stats");
      return null;
    }

    const data: AllStats = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching stats:", error);
    return null;
  }
}

export async function fetchTorrentHistory(): Promise<AllStats[] | null> {
  try {
    const response = await fetch("https://submedial-bloodlike-sarah.ngrok-free.dev/torrent/history", {
      cache: "no-store",
      headers: {
        "ngrok-skip-browser-warning": "true",
      },
    });

    if (!response.ok) {
      console.error("Failed to fetch history");
      return null;
    }

    const data: AllStats[] = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching history:", error);
    return null;
  }
}
