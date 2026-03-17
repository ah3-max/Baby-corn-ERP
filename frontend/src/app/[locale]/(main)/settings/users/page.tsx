'use client';

/**
 * 使用者管理頁面 /settings/users
 */
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Plus, Pencil, UserX, UserCheck } from 'lucide-react';
import { usersApi, rolesApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import type { User, Role } from '@/types';
import UserModal from './UserModal';

export default function UsersPage() {
  const t = useTranslations('users');
  const tc = useTranslations('common');
  const { showToast } = useToast();

  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  const fetchData = async () => {
    try {
      const [usersRes, rolesRes] = await Promise.all([
        usersApi.list(),
        rolesApi.list(),
      ]);
      setUsers(usersRes.data);
      setRoles(rolesRes.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleToggleActive = async (user: User) => {
    if (!confirm(user.is_active ? t('confirmDeactivate') : `${t('activate')} ${user.full_name}?`)) return;
    try {
      await usersApi.update(user.id, { is_active: !user.is_active });
      showToast(user.is_active ? t('deactivateSuccess') : t('activate'), 'success');
      fetchData();
    } catch {
      showToast(tc('error'), 'error');
    }
  };

  const handleOpenCreate = () => {
    setEditingUser(null);
    setModalOpen(true);
  };

  const handleOpenEdit = (user: User) => {
    setEditingUser(user);
    setModalOpen(true);
  };

  const handleModalClose = (refresh?: boolean) => {
    setModalOpen(false);
    setEditingUser(null);
    if (refresh) fetchData();
  };

  return (
    <div>
      {/* 頁首 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{tc('total', { count: users.length })}</p>
        </div>
        <button onClick={handleOpenCreate} className="btn-primary flex items-center gap-2">
          <Plus size={16} />
          {t('addUser')}
        </button>
      </div>

      {/* 使用者表格 */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">{t('fullName')}</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">{t('email')}</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">{t('role')}</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">{t('status')}</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">{tc('createdAt')}</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">{tc('actions')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">{tc('loading')}</td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">{tc('noData')}</td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{user.full_name}</td>
                  <td className="px-4 py-3 text-gray-600">{user.email}</td>
                  <td className="px-4 py-3 text-gray-600">{user.role?.name ?? '—'}</td>
                  <td className="px-4 py-3">
                    {user.is_active
                      ? <span className="badge-active">{tc('active')}</span>
                      : <span className="badge-inactive">{tc('inactive')}</span>
                    }
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleOpenEdit(user)}
                        className="p-1.5 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded transition-colors"
                        title={tc('edit')}
                      >
                        <Pencil size={15} />
                      </button>
                      <button
                        onClick={() => handleToggleActive(user)}
                        className={`p-1.5 rounded transition-colors ${
                          user.is_active
                            ? 'text-gray-500 hover:text-red-600 hover:bg-red-50'
                            : 'text-gray-500 hover:text-green-600 hover:bg-green-50'
                        }`}
                        title={user.is_active ? t('deactivate') : t('activate')}
                      >
                        {user.is_active ? <UserX size={15} /> : <UserCheck size={15} />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* 新增/編輯 Modal */}
      {modalOpen && (
        <UserModal
          user={editingUser}
          roles={roles}
          onClose={handleModalClose}
        />
      )}
    </div>
  );
}
