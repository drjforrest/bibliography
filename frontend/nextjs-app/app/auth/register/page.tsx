'use client'

import { useEffect } from 'react'

export default function RegisterPage() {
  useEffect(() => {
    // Redirect to external Clerk hosted sign-up page
    const signUpUrl = process.env.NEXT_PUBLIC_CLERK_SIGN_UP_URL || 'https://accounts.counterforce-hero.tech/sign-up'
    window.location.href = signUpUrl
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background-light to-gray-100 dark:from-background-dark dark:to-gray-900">
      <div className="text-center">
        <div className="flex justify-center mb-4">
          <img
            src="/HERO-Lab-logo-no-words.png"
            alt="HERO Lab Logo"
            width={64}
            height={64}
            className="rounded-full animate-pulse"
            style={{ height: 'auto' }}
          />
        </div>
        <p className="text-lg text-gray-600 dark:text-gray-400">
          Redirecting to sign up...
        </p>
      </div>
    </div>
  )
}
