/**
 * @file proxy.ts
 * @brief Edge route gate. /(app)/** requires the session-hint cookie;
 *        /(auth)/** is bounced to /app when already signed in. The real
 *        refresh token is HttpOnly and scoped to /api/v1/auth, invisible
 *        to the edge runtime — so we read a non-sensitive `nx_session`
 *        hint cookie set client-side after a successful login. The actual
 *        auth check happens client-side via session restore.
 */
import { NextResponse, type NextRequest } from "next/server";

const REFRESH_COOKIE = "nx_session";
const AUTH_PAGES = [
  "/login",
  "/register",
  "/magic-link",
  "/reset-password",
  "/two-factor",
];

export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const hasRefresh = req.cookies.has(REFRESH_COOKIE);

  if (pathname === "/") {
    const url = req.nextUrl.clone();
    url.pathname = hasRefresh ? "/app" : "/login";
    url.search = "";
    return NextResponse.redirect(url);
  }

  if (pathname.startsWith("/app")) {
    if (!hasRefresh) {
      const url = req.nextUrl.clone();
      url.pathname = "/login";
      url.searchParams.set("next", pathname);
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  }

  if (AUTH_PAGES.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    if (hasRefresh) {
      const url = req.nextUrl.clone();
      url.pathname = "/app";
      url.search = "";
      return NextResponse.redirect(url);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/",
    "/app/:path*",
    "/login",
    "/register",
    "/magic-link",
    "/reset-password",
    "/two-factor",
  ],
};
