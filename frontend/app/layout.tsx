import Link from 'next/link';
import { Public_Sans } from 'next/font/google';
import localFont from 'next/font/local';
import { headers } from 'next/headers';
import { LogoutButton } from '@/components/app/logout-button';
import { ThemeProvider } from '@/components/app/theme-provider';
import { ThemeToggle } from '@/components/app/theme-toggle';
import { getCurrentUser } from '@/lib/auth';
import { cn } from '@/lib/shadcn/utils';
import { getAppConfig, getStyles } from '@/lib/utils';
import '@/styles/globals.css';

const publicSans = Public_Sans({
  variable: '--font-public-sans',
  subsets: ['latin'],
});

const commitMono = localFont({
  display: 'swap',
  variable: '--font-commit-mono',
  src: [
    {
      path: '../fonts/CommitMono-400-Regular.otf',
      weight: '400',
      style: 'normal',
    },
    {
      path: '../fonts/CommitMono-700-Regular.otf',
      weight: '700',
      style: 'normal',
    },
    {
      path: '../fonts/CommitMono-400-Italic.otf',
      weight: '400',
      style: 'italic',
    },
    {
      path: '../fonts/CommitMono-700-Italic.otf',
      weight: '700',
      style: 'italic',
    },
  ],
});

interface RootLayoutProps {
  children: React.ReactNode;
}

export default async function RootLayout({ children }: RootLayoutProps) {
  const hdrs = await headers();
  const appConfig = await getAppConfig(hdrs);
  const currentUser = await getCurrentUser();
  const styles = getStyles(appConfig);
  const { pageTitle, pageDescription } = appConfig;

  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn(
        publicSans.variable,
        commitMono.variable,
        'scroll-smooth font-sans antialiased'
      )}
    >
      <head>
        {styles && <style>{styles}</style>}
        <title>{pageTitle}</title>
        <meta name="description" content={pageDescription} />
      </head>
      <body className="overflow-x-hidden">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {currentUser && (
            <header className="hidden w-full items-center justify-between border-b border-border/80 bg-background p-6 md:flex">
              <div className="flex items-center gap-6">
                <nav className="flex items-center gap-4 text-sm">
                  <Link href="/" className="text-foreground hover:text-primary transition-colors">
                    Главная
                  </Link>
                  <Link
                    href="/sessions"
                    className="text-foreground hover:text-primary transition-colors"
                  >
                    Тренировки
                  </Link>
                  {currentUser.role === 'coach' && (
                    <Link
                      href="/users"
                      className="text-foreground hover:text-primary transition-colors"
                    >
                      Пользователи
                    </Link>
                  )}
                </nav>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <div className="text-foreground text-sm font-medium">{currentUser.email}</div>
                  <div className="text-muted-foreground text-xs uppercase">{currentUser.role}</div>
                </div>
                <LogoutButton />
              </div>
            </header>
          )}

          {children}
          <div className="group fixed bottom-0 left-1/2 z-50 mb-2 -translate-x-1/2">
            <ThemeToggle className="translate-y-20 transition-transform delay-150 duration-300 group-hover:translate-y-0" />
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
