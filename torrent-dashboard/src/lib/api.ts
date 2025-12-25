import { AllStats } from "@/types/tracker";

export async function fetchTorrentStats(): Promise<AllStats | null> {
  try {
    const response = await fetch("/api/stats", {
      cache: "no-store",
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
    const response = await fetch("/api/history", {
      cache: "no-store",
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
