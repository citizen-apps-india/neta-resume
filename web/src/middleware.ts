import { NextResponse, type NextRequest } from "next/server";

// Mark a first-time browser so the homepage counts it once (unique visitors). A server component can't
// set cookies during render, so middleware sets the cookie + forwards an `x-nr-new` request header that
// the page reads to decide whether to increment. Only real document loads from non-bots count.
export function middleware(req: NextRequest) {
  const seen = req.cookies.get("nr_uv");
  const accept = req.headers.get("accept") ?? "";
  const ua = req.headers.get("user-agent") ?? "";
  const looksBot = /bot|crawl|spider|slurp|bingpreview|facebookexternalhit|headless|monitor|preview/i.test(ua);
  const isNew = !seen && accept.includes("text/html") && !looksBot;

  const headers = new Headers(req.headers);
  if (isNew) headers.set("x-nr-new", "1");
  const res = NextResponse.next({ request: { headers } });
  if (isNew) {
    res.cookies.set("nr_uv", "1", {
      maxAge: 60 * 60 * 24 * 365 * 5, // ~5 years
      httpOnly: true,
      sameSite: "lax",
      path: "/",
    });
  }
  return res;
}

// Only the homepage drives the counter.
export const config = { matcher: ["/"] };
