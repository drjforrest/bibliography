import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isProtectedRoute = createRouteMatcher([
  '/',
  '/dashboard(.*)',
  '/papers(.*)',
  '/favorites(.*)',
  '/messages(.*)',
  '/profile(.*)',
  '/recent(.*)',
  '/topics(.*)',
])

export default clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) {
    // Use external Clerk hosted sign-in page
    const clerkSignInUrl = process.env.NEXT_PUBLIC_CLERK_SIGN_IN_URL || 'https://accounts.counterforce-hero.tech/sign-in'
    await auth.protect({
      unauthenticatedUrl: clerkSignInUrl,
      unauthorizedUrl: clerkSignInUrl,
    })
  }
})

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
}