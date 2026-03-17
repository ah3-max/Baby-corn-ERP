'use client';

/**
 * 語言切換按鈕元件
 * 右上角的 🌐 下拉選單，支援繁中 / EN / ภาษาไทย
 */
import { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Globe } from 'lucide-react';
import { useLocale } from 'next-intl';
import { authApi } from '@/lib/api';
import { isLoggedIn } from '@/lib/auth';

const LANGUAGES = [
  { code: 'zh-TW', label: '繁體中文', flag: '🇹🇼' },
  { code: 'en',    label: 'English',  flag: '🇺🇸' },
  { code: 'th',    label: 'ภาษาไทย',  flag: '🇹🇭' },
] as const;

export default function LanguageSwitcher() {
  const [open, setOpen] = useState(false);
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const handleSelect = async (code: string) => {
    setOpen(false);

    // 若已登入，同步更新後端使用者偏好
    if (isLoggedIn()) {
      try {
        await authApi.updateLanguage(code);
      } catch {
        // 靜默忽略，前端切換仍然生效
      }
    }

    // 切換 next-intl locale（替換路徑前綴）
    const newPath = pathname.replace(`/${locale}`, `/${code}`);
    router.push(newPath || `/${code}`);
  };

  const current = LANGUAGES.find((l) => l.code === locale) || LANGUAGES[0];

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-gray-600 hover:bg-gray-100 transition-colors"
      >
        <Globe size={16} />
        <span>{current.flag} {current.label}</span>
      </button>

      {open && (
        <>
          {/* 點擊背景關閉 */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 top-full mt-1 z-20 bg-white border border-gray-200 rounded-lg shadow-lg min-w-[160px] py-1">
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                onClick={() => handleSelect(lang.code)}
                className={`w-full text-left px-4 py-2 text-sm flex items-center gap-2 hover:bg-gray-50 transition-colors ${
                  locale === lang.code ? 'text-primary-600 font-medium bg-primary-50' : 'text-gray-700'
                }`}
              >
                <span>{lang.flag}</span>
                <span>{lang.label}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
