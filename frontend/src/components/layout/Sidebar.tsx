'use client';

/**
 * 左側導航欄 — 精緻版
 */
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTranslations, useLocale } from 'next-intl';
import {
  LayoutDashboard, Users, ShoppingCart, Package,
  Factory, Ship, Warehouse, BarChart3, DollarSign,
  Settings, Sprout, Archive
} from 'lucide-react';
import { clsx } from 'clsx';
import { useUser } from '@/contexts/UserContext';

const NAV_ITEMS = [
  { key: 'dashboard',  icon: LayoutDashboard, href: '/',          module: null },
  { key: 'suppliers',  icon: Users,           href: '/suppliers', module: 'supplier' },
  { key: 'purchases',  icon: ShoppingCart,    href: '/purchases', module: 'purchase' },
  { key: 'batches',    icon: Package,         href: '/batches',   module: 'batch' },
  { key: 'factory',    icon: Factory,         href: '/factory',   module: 'qc' },
  { key: 'shipments',  icon: Ship,            href: '/shipments', module: 'shipment' },
  { key: 'inventory',  icon: Warehouse,       href: '/inventory', module: 'stock' },
  { key: 'sales',      icon: BarChart3,       href: '/sales',     module: 'daily_sale' },
  { key: 'cost',       icon: DollarSign,      href: '/cost',      module: 'cost_sheet' },
  { key: 'finance',    icon: Archive,         href: '/finance',   module: 'profit' },
];

const SETTINGS_ITEMS = [
  { key: 'users',        href: '/settings/users',         module: 'user' },
  { key: 'roles',        href: '/settings/roles',         module: 'user' },
  { key: 'productTypes', href: '/settings/product-types', module: 'system' },
];

export default function Sidebar() {
  const t = useTranslations('nav');
  const locale = useLocale();
  const pathname = usePathname();
  const cleanPath = pathname.replace(`/${locale}`, '') || '/';
  const { hasPermission } = useUser();

  return (
    <aside className="w-[240px] min-h-screen bg-gray-900 flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center gap-2.5 px-5">
        <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
          <Sprout size={18} className="text-white" />
        </div>
        <span className="font-bold text-white text-sm tracking-tight">玉米筍 ERP</span>
      </div>

      {/* 主導航 */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.filter(({ module }) => !module || hasPermission(module, 'read')).map(({ key, icon: Icon, href }) => {
          const isActive = cleanPath === href || (href !== '/' && cleanPath.startsWith(href));
          return (
            <Link
              key={key}
              href={`/${locale}${href}`}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-150',
                isActive
                  ? 'bg-primary-600/20 text-primary-400'
                  : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
              )}
            >
              <Icon size={18} className={isActive ? 'text-primary-400' : ''} />
              <span>{t(key as any)}</span>
            </Link>
          );
        })}

        {/* 分隔線 */}
        <div className="pt-4 pb-2">
          <div className="border-t border-gray-800" />
        </div>

        {/* 設定 */}
        <p className="px-3 mb-2 text-[11px] font-semibold text-gray-600 uppercase tracking-wider">
          {t('settings')}
        </p>
        {SETTINGS_ITEMS.filter(({ module }) => hasPermission(module, 'read')).map(({ key, href }) => {
          const isActive = cleanPath.startsWith(href);
          return (
            <Link
              key={key}
              href={`/${locale}${href}`}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-150',
                isActive
                  ? 'bg-primary-600/20 text-primary-400'
                  : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
              )}
            >
              <Settings size={18} className={isActive ? 'text-primary-400' : ''} />
              <span>{t(key as any)}</span>
            </Link>
          );
        })}
      </nav>

      {/* 底部版本 */}
      <div className="px-5 py-4 border-t border-gray-800">
        <p className="text-[11px] text-gray-600">v1.0.0 · Phase 1</p>
      </div>
    </aside>
  );
}
