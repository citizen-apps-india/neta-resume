import { connection } from "next/server";

/** The catch block of a cached (ISR) page whose API call failed. A page that renders an error state gets
 *  that error cached for its whole revalidate window, so this never renders one:
 *  - during `next build` (API unreachable) the page becomes request-time for that deploy instead;
 *  - at request time it rethrows, so a background refresh keeps serving the last good copy, and a page
 *    with no good copy answers 500 through `app/error.tsx`. */
export async function failIsrPage(error: unknown): Promise<never> {
  await connection();
  throw error;
}
