/**
 * Next.js Middleware
 * 處理 i18n 路由自動導向（依使用者語言偏好）
 */
import createMiddleware from 'next-intl/middleware';

export default createMiddleware({
  locales: ['zh-TW', 'en', 'th'],
  defaultLocale: 'zh-TW',
  localePrefix: 'always',
});

export const config = {
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)'],
};
