import { NextResponse, type NextRequest } from "next/server";

const API_BASE = process.env.NETA_API_BASE ?? "http://localhost:8000";

/** Same-origin proxy for `GET /eci-files/entries/{id}` — the timeline's in-place entry card fetches the
 *  full record (summary, context, citations) client-side when it opens, so this relays the request the
 *  same way `api/eci-files/timeline` does (see that route's doc comment). */
export async function GET(_req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/eci-files/entries/${encodeURIComponent(id)}`, { cache: "no-store" });
  } catch {
    return NextResponse.json({ error: "unreachable" }, { status: 502 });
  }
  if (res.status === 404) return NextResponse.json({ error: "not found" }, { status: 404 });
  if (!res.ok) return NextResponse.json({ error: `API ${res.status}` }, { status: res.status });
  return NextResponse.json(await res.json());
}
