import { timingSafeEqual } from "node:crypto";
import { revalidateTag } from "next/cache";
import { API_CACHE_TAG } from "@/lib/api";

function authorised(header: string | null, secret: string): boolean {
  const given = Buffer.from(header ?? "");
  const expected = Buffer.from(`Bearer ${secret}`);
  return given.length === expected.length && timingSafeEqual(given, expected);
}

/** Called by the ingest job after it changes data: marks every cached API read stale, so the next visit
 *  to each page rebuilds it from fresh data while the old copy is still served. Pages prerendered at
 *  build time do not carry the tag and refresh on their own day-long timer instead. `revalidatePath` is
 *  deliberately not used: it expires pages outright, so an API outage would turn them into 500s.
 *  Disabled (503) until `NETA_REVALIDATE_SECRET` is set. */
export async function POST(req: Request) {
  const secret = process.env.NETA_REVALIDATE_SECRET;
  if (!secret) return Response.json({ error: "revalidation is not configured" }, { status: 503 });
  if (!authorised(req.headers.get("authorization"), secret)) {
    return Response.json({ error: "unauthorised" }, { status: 401 });
  }
  revalidateTag(API_CACHE_TAG, "max");
  return Response.json({ revalidated: API_CACHE_TAG });
}
