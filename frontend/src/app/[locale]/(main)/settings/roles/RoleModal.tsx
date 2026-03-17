'use client';

/**
 * 角色新增 / 編輯 Modal
 * 包含權限矩陣勾選
 */
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { X } from 'lucide-react';
import { rolesApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import type { Role, Permission } from '@/types';

interface Props {
  role: Role | null;
  permissions: Permission[];
  onClose: (refresh?: boolean) => void;
}

// 模組顯示順序
const MODULE_ORDER = [
  'supplier', 'purchase', 'batch', 'qc', 'factory',
  'shipment', 'inventory', 'sales', 'customer', 'cost',
  'user', 'role', 'report',
];

// 動作顯示順序
const ACTION_ORDER = ['view', 'create', 'edit', 'delete', 'export', 'view_cost', 'view_profit'];

export default function RoleModal({ role, permissions, onClose }: Props) {
  const t = useTranslations('roles');
  const tc = useTranslations('common');
  const { showToast } = useToast();
  const isEdit = !!role;

  const [name, setName] = useState(role?.name ?? '');
  const [description, setDescription] = useState(role?.description ?? '');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    new Set(role?.permissions.map((p) => p.id) ?? [])
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // 按模組分組權限
  const grouped = MODULE_ORDER.reduce((acc, module) => {
    const perms = permissions.filter((p) => p.module === module);
    if (perms.length > 0) acc[module] = perms;
    return acc;
  }, {} as Record<string, Permission[]>);

  const togglePerm = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleModule = (module: string) => {
    const modulePerms = grouped[module] ?? [];
    const allSelected = modulePerms.every((p) => selectedIds.has(p.id));
    setSelectedIds((prev) => {
      const next = new Set(prev);
      modulePerms.forEach((p) => allSelected ? next.delete(p.id) : next.add(p.id));
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const payload = { name, description, permission_ids: Array.from(selectedIds) };
      if (isEdit) {
        await rolesApi.update(role.id, payload);
      } else {
        await rolesApi.create(payload);
      }
      showToast(isEdit ? t('updateSuccess') : t('createSuccess'), 'success');
      onClose(true);
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? tc('error');
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="card w-full max-w-3xl max-h-[90vh] flex flex-col shadow-xl">
        {/* 標題列 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 flex-shrink-0">
          <h2 className="text-lg font-semibold text-gray-800">
            {isEdit ? t('editRole') : t('addRole')}
          </h2>
          <button onClick={() => onClose()} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
          <div className="overflow-y-auto flex-1 px-6 py-4 space-y-5">
            {/* 基本資料 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('roleName')} *</label>
                <input value={name} onChange={(e) => setName(e.target.value)}
                  required className="input" disabled={isEdit && role.is_system} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('description')}</label>
                <input value={description} onChange={(e) => setDescription(e.target.value)} className="input" />
              </div>
            </div>

            {/* 權限矩陣 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">{t('permissions')}</label>
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left px-3 py-2 font-medium text-gray-600 w-32">{tc('module')}</th>
                      {ACTION_ORDER.map((action) => (
                        <th key={action} className="text-center px-2 py-2 font-medium text-gray-600">
                          {t(`actions.${action}` as any)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {Object.entries(grouped).map(([module, perms]) => {
                      const allSelected = perms.every((p) => selectedIds.has(p.id));
                      return (
                        <tr key={module} className="hover:bg-gray-50">
                          {/* 模組名稱（點擊全選/取消） */}
                          <td className="px-3 py-2">
                            <button
                              type="button"
                              onClick={() => toggleModule(module)}
                              className={`text-left font-medium transition-colors ${
                                allSelected ? 'text-primary-700' : 'text-gray-700'
                              }`}
                            >
                              {t(`modules.${module}` as any)}
                            </button>
                          </td>
                          {/* 各動作的勾選格 */}
                          {ACTION_ORDER.map((action) => {
                            const perm = perms.find((p) => p.action === action);
                            return (
                              <td key={action} className="text-center px-2 py-2">
                                {perm ? (
                                  <input
                                    type="checkbox"
                                    checked={selectedIds.has(perm.id)}
                                    onChange={() => togglePerm(perm.id)}
                                    className="w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                                  />
                                ) : (
                                  <span className="text-gray-200">—</span>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-2 rounded-md">
                {error}
              </div>
            )}
          </div>

          {/* 按鈕列 */}
          <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 flex-shrink-0">
            <button type="button" onClick={() => onClose()} className="btn-secondary">
              {tc('cancel')}
            </button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? '...' : tc('save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
