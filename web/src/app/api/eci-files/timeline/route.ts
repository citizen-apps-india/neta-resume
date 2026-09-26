import { NextResponse, type NextRequest } from "next/server";

const API_BASE = process.env.NETA_API_BASE ?? "http://localhost:8000";

/** Same-origin proxy for the compact timeline (`GET /eci-files/timeline?fields=compact`). The reworked
 *  /eci-files/timeline page changes its window, topic and person client-side (no full page reload — see
 *  `TimelineView`), which means the browser does the fetching; `NETA_API_BASE` is server-side only
 *  (`.env.example`), so this route relays the request instead of the client ever learning that URL. */
export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const q = new URLSearchParams();
  for (const key of ["topic", "person", "lane", "from", "to", "state"]) {
    const v = sp.get(key);
    if (v) q.set(key, v);
  }
  q.set("fields", "compact");

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/eci-files/timeline?${q.toString()}`, { cache: "no-store" });
  } catch {
    return NextResponse.json({ error: "unreachable" }, { status: 502 });
  }
  if (!res.ok) return NextResponse.json({ error: `API ${res.status}` }, { status: res.status });
  return NextResponse.json(await res.json());
}
