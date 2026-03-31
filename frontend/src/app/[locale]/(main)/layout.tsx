'use client';

/**
 * 主系統佈局（登入後的頁面）
 * 包含左側導航、頂部列
 */
import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useLocale } from 'next-intl';
import Sidebar from '@/components/layout/Sidebar';
import TopBar from '@/components/layout/TopBar';
import { authApi } from '@/lib/api';
import { isLoggedIn } from '@/lib/auth';
import { ToastProvider } from '@/contexts/ToastContext';
import { UserProvider } from '@/contexts/UserContext';
import { Toaster } from 'sonner';
import type { UserMe } from '@/types';

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserMe | null>(null);
  const router = useRouter();
  const locale = useLocale();
  const pathname = usePathname();

  useEffect(() => {
    // 未登入直接跳回登入頁
    if (!isLoggedIn()) {
      router.push(`/${locale}/login`);
      return;
    }

    // 取得目前使用者資訊
    authApi.getMe()
      .then(({ data }) => setUser(data))
      .catch(() => {
        router.push(`/${locale}/login`);
      });
  }, [pathname]);

  return (
    <ToastProvider>
      <UserProvider user={user}>
        <div className="flex min-h-screen bg-gray-50">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <TopBar user={user} />
            <main className="flex-1 p-6 lg:p-8 overflow-auto">
              {children}
            </main>
          </div>
        </div>
        <Toaster position="top-right" richColors closeButton />
      </UserProvider>
    </ToastProvider>
  );
}
