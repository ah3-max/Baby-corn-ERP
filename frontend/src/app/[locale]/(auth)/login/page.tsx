'use client';

/**
 * 登入頁面 — 重新設計
 * 左側品牌視覺 + 右側登入表單
 */
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { Sprout, ArrowRight, Loader2, Zap } from 'lucide-react';
import { authApi } from '@/lib/api';
import { setTokens } from '@/lib/auth';
import LanguageSwitcher from '@/components/layout/LanguageSwitcher';

// 測試階段：超級管理員快速登入帳號
const DEV_ADMIN_EMAIL = 'admin@babycorn.com';
const DEV_ADMIN_PASSWORD = 'admin1234';

export default function LoginPage() {
  const t = useTranslations('auth');
  const locale = useLocale();
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e?: React.FormEvent, overrideEmail?: string, overridePassword?: string) => {
    if (e) e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const loginEmail = overrideEmail || email;
      const loginPassword = overridePassword || password;
      const { data } = await authApi.login(loginEmail, loginPassword);
      setTokens(data.access_token, data.refresh_token);
      router.push(`/${locale}`);
    } catch {
      setError(t('loginError'));
    } finally {
      setLoading(false);
    }
  };

  // 超級管理員一鍵登入
  const handleQuickLogin = () => {
    handleLogin(undefined, DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD);
  };

  return (
    <div className="min-h-screen flex">
      {/* ── 左側品牌區 ── */}
      <div className="hidden lg:flex lg:w-[55%] relative bg-gradient-to-br from-primary-600 via-primary-700 to-emerald-800 text-white overflow-hidden">
        {/* 裝飾圓形 */}
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-white/5 rounded-full" />
        <div className="absolute bottom-20 -right-20 w-80 h-80 bg-white/5 rounded-full" />
        <div className="absolute top-1/2 left-1/3 w-60 h-60 bg-white/5 rounded-full" />

        <div className="relative z-10 flex flex-col justify-center px-16 xl:px-24">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-12">
            <div className="w-12 h-12 bg-white/15 backdrop-blur-sm rounded-xl flex items-center justify-center">
              <Sprout size={28} />
            </div>
            <span className="text-2xl font-bold tracking-tight">玉米筍 ERP</span>
          </div>

          <h1 className="text-4xl xl:text-5xl font-bold leading-tight mb-6">
            {t('brandTitle')}
          </h1>
          <p className="text-lg text-white/70 leading-relaxed max-w-md mb-12">
            {t('brandDesc')}
          </p>

          {/* 功能亮點 */}
          <div className="space-y-4">
            {[
              { label: t('feature1'), desc: t('feature1Desc') },
              { label: t('feature2'), desc: t('feature2Desc') },
              { label: t('feature3'), desc: t('feature3Desc') },
            ].map((item) => (
              <div key={item.label} className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <div className="w-2 h-2 rounded-full bg-white" />
                </div>
                <div>
                  <p className="font-medium">{item.label}</p>
                  <p className="text-sm text-white/50">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── 右側登入區 ── */}
      <div className="flex-1 flex flex-col bg-gray-50">
        {/* 語言切換 */}
        <div className="flex justify-end p-6">
          <LanguageSwitcher />
        </div>

        <div className="flex-1 flex items-center justify-center px-6 sm:px-12">
          <div className="w-full max-w-sm">
            {/* Mobile Logo */}
            <div className="lg:hidden flex items-center gap-3 mb-8">
              <div className="w-11 h-11 bg-primary-600 rounded-xl flex items-center justify-center">
                <Sprout size={24} className="text-white" />
              </div>
              <span className="text-xl font-bold text-gray-800">玉米筍 ERP</span>
            </div>

            <h2 className="text-2xl font-bold text-gray-900 mb-2">{t('welcome')}</h2>
            <p className="text-sm text-gray-500 mb-8">{t('subtitle')}</p>

            {/* 快速登入按鈕（測試階段） */}
            <button
              type="button"
              onClick={handleQuickLogin}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 mb-6 bg-amber-50 hover:bg-amber-100 border-2 border-amber-300 border-dashed text-amber-700 rounded-lg text-sm font-medium transition-colors"
            >
              <Zap size={16} />
              {t('quickLogin')}
            </button>

            <form onSubmit={(e) => handleLogin(e)} className="space-y-5">
              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  {t('email')}
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="input"
                  placeholder="admin@babycorn.com"
                  autoComplete="email"
                />
              </div>

              {/* 密碼 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  {t('password')}
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="input"
                  autoComplete="current-password"
                />
              </div>

              {/* 錯誤訊息 */}
              {error && (
                <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-3 rounded-lg">
                  <span className="flex-shrink-0">⚠</span>
                  {error}
                </div>
              )}

              {/* 登入按鈕 */}
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                {loading ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <>
                    {t('loginButton')}
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </form>

            {/* 底部版權 */}
            <p className="text-center text-xs text-gray-400 mt-12">
              &copy; {new Date().getFullYear()} 玉米筍國際貿易有限公司
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
