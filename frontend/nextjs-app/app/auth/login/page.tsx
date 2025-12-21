import { SignIn } from '@clerk/nextjs'

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background-light to-gray-100 dark:from-background-dark dark:to-gray-900 px-4">
      <div className="max-w-md w-full space-y-8">
        {/* Logo and Title */}
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <img
              src="/HERO-Lab-logo-no-words.png"
              alt="HERO Lab Logo"
              width={64}
              height={64}
              className="rounded-full"
              style={{ height: 'auto' }}
            />
          </div>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">HERO Lab Evidence Library</h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Sign in to access your bibliography
          </p>
        </div>

        {/* Clerk SignIn Component */}
        <div className="bg-white dark:bg-gray-800 py-8 px-6 shadow-xl rounded-lg">
          <SignIn
            path="/auth/login"
            routing="path"
            signUpUrl="/auth/register"
            redirectUrl="/"
            appearance={{
              baseTheme: undefined,
              variables: {
                colorPrimary: '#4e989e',
              },
              elements: {
                formButtonPrimary: 'bg-[#4e989e] hover:bg-[#3d7a7f] text-white',
                card: 'bg-transparent shadow-none',
                headerTitle: 'hidden',
                headerSubtitle: 'hidden',
                socialButtonsBlockButton: 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600',
                formFieldInput: 'bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600',
                footerActionLink: 'text-[#4e989e] hover:text-[#3d7a7f] dark:text-[#94d2bd] dark:hover:text-[#4e989e]',
              }
            }}
          />
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-gray-500 dark:text-gray-400">
          Lab Internal Use Only
        </p>
      </div>
    </div>
  )
}
