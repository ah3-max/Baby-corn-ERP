'use client';

/**
 * 角色管理頁面 /settings/roles
 */
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Plus, Pencil, Trash2, ShieldCheck } from 'lucide-react';
import { rolesApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import type { Role, Permission } from '@/types';
import RoleModal from './RoleModal';

export default function RolesPage() {
  const t = useTranslations('roles');
  const tc = useTranslations('common');
  const { showToast } = useToast();

  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);

  const fetchData = async () => {
    try {
      const [rolesRes, permsRes] = await Promise.all([
        rolesApi.list(),
        rolesApi.listPermissions(),
      ]);
      setRoles(rolesRes.data);
      setPermissions(permsRes.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleDelete = async (role: Role) => {
    if (role.is_system) { showToast(t('cannotDeleteSystem'), 'warning'); return; }
    if (!confirm(`${tc('confirmDelete')} (${role.name})`)) return;
    try {
      await rolesApi.delete(role.id);
      showToast(t('deleteSuccess'), 'success');
      fetchData();
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    }
  };

  const handleModalClose = (refresh?: boolean) => {
    setModalOpen(false);
    setEditingRole(null);
    if (refresh) fetchData();
  };

  return (
    <div>
      {/* 頁首 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{tc('total', { count: roles.length })}</p>
        </div>
        <button onClick={() => { setEditingRole(null); setModalOpen(true); }}
          className="btn-primary flex items-center gap-2">
          <Plus size={16} />
          {t('addRole')}
        </button>
      </div>

      {/* 角色列表 */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">{t('roleName')}</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">{t('description')}</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">{t('userCount')}</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">{tc('actions')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">{tc('loading')}</td></tr>
            ) : roles.map((role) => (
              <tr key={role.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-800">{role.name}</span>
                    {role.is_system && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-blue-50 text-blue-600">
                        <ShieldCheck size={11} />
                        {t('systemRole')}
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-500">{role.description ?? '—'}</td>
                <td className="px-4 py-3 text-gray-600">{role.permissions.length} {tc('permissions_count')}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <button onClick={() => { setEditingRole(role); setModalOpen(true); }}
                      className="p-1.5 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded transition-colors">
                      <Pencil size={15} />
                    </button>
                    {!role.is_system && (
                      <button onClick={() => handleDelete(role)}
                        className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded transition-colors">
                        <Trash2 size={15} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modalOpen && (
        <RoleModal
          role={editingRole}
          permissions={permissions}
          onClose={handleModalClose}
        />
      )}
    </div>
  );
}
