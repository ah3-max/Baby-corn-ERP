'use client';

/**
 * 頂部列 — 精緻版
 */
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { LogOut, KeyRound, ChevronDown } from 'lucide-react';
import LanguageSwitcher from './LanguageSwitcher';
import { authApi } from '@/lib/api';
import { clearTokens, getRefreshToken } from '@/lib/auth';
import type { UserMe } from '@/types';

interface TopBarProps {
  user: UserMe | null;
}

export default function TopBar({ user }: TopBarProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const t = useTranslations('nav');
  const locale = useLocale();
  const router = useRouter();

  const handleLogout = async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try { await authApi.logout(refreshToken); } catch {}
    }
    clearTokens();
    router.push(`/${locale}/login`);
  };

  // 取使用者名稱首字母
  const initials = user?.full_name
    ? user.full_name.charAt(0).toUpperCase()
    : '?';

  return (
    <header className="h-14 bg-white border-b border-gray-200/80 flex items-center justify-end px-6 gap-3">
      <LanguageSwitcher />

      {user && (
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="flex items-center gap-2.5 pl-1 pr-2 py-1 rounded-full hover:bg-gray-50 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-emerald-600 flex items-center justify-center text-white text-xs font-bold shadow-sm">
              {initials}
            </div>
            <span className="text-sm font-medium text-gray-700 hidden sm:inline">{user.full_name}</span>
            <ChevronDown size={14} className="text-gray-400" />
          </button>

          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-full mt-2 z-20 bg-white border border-gray-200 rounded-xl shadow-lg min-w-[200px] py-1 overflow-hidden">
                {/* 使用者資訊 */}
                <div className="px-4 py-3 border-b border-gray-100">
                  <p className="text-sm font-semibold text-gray-800">{user.full_name}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{user.email}</p>
                  {user.role && (
                    <span className="inline-block mt-1.5 px-2 py-0.5 text-[10px] font-medium bg-primary-50 text-primary-600 rounded-full">
                      {user.role.name}
                    </span>
                  )}
                </div>

                <button
                  onClick={() => { setMenuOpen(false); router.push(`/${locale}/settings/profile`); }}
                  className="w-full text-left px-4 py-2.5 text-sm text-gray-700 flex items-center gap-2.5 hover:bg-gray-50 transition-colors"
                >
                  <KeyRound size={15} className="text-gray-400" />
                  {t('profile')}
                </button>

                <div className="border-t border-gray-100" />

                <button
                  onClick={handleLogout}
                  className="w-full text-left px-4 py-2.5 text-sm text-red-600 flex items-center gap-2.5 hover:bg-red-50 transition-colors"
                >
                  <LogOut size={15} />
                  {t('logout')}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </header>
  );
}
