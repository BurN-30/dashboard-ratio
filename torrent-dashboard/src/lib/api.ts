import { AllStats } from "@/types/tracker";

export async function fetchTorrentStats(): Promise<AllStats | null> {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_NGROK_URL || "http://localhost:8888";
    const response = await fetch(`${baseUrl}/torrent/stats`, {
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
    const baseUrl = process.env.NEXT_PUBLIC_NGROK_URL || "http://localhost:8888";
    const response = await fetch(`${baseUrl}/torrent/history`, {
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
