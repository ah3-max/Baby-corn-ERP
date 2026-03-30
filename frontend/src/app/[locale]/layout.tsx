/**
 * 全站根佈局（含 locale 路由）
 * 包含 next-intl Provider、QueryClient Provider
 */
import type { Metadata } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import { notFound } from 'next/navigation';
import './globals.css';

const SUPPORTED_LOCALES = ['zh-TW', 'en', 'th'];

export const metadata: Metadata = {
  title: '玉米筍 ERP',
  description: '玉米筍跨境供應鏈管理系統',
};

export default async function RootLayout({
  children,
  params: { locale },
}: {
  children: React.ReactNode;
  params: { locale: string };
}) {
  // 不支援的語言回傳 404
  if (!SUPPORTED_LOCALES.includes(locale)) {
    notFound();
  }

  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body>
        <NextIntlClientProvider messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
