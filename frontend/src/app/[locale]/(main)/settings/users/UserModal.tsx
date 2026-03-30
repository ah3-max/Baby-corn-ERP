'use client';

/**
 * 使用者新增 / 編輯 Modal
 */
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { X } from 'lucide-react';
import { usersApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import type { User, Role } from '@/types';

interface Props {
  user: User | null;
  roles: Role[];
  onClose: (refresh?: boolean) => void;
}

const LANGUAGES = [
  { code: 'zh-TW', label: '繁體中文' },
  { code: 'en',    label: 'English' },
  { code: 'th',    label: 'ภาษาไทย' },
];

export default function UserModal({ user, roles, onClose }: Props) {
  const t = useTranslations('users');
  const tc = useTranslations('common');
  const { showToast } = useToast();
  const isEdit = !!user;

  const [form, setForm] = useState({
    full_name:          user?.full_name ?? '',
    email:              user?.email ?? '',
    password:           '',
    role_id:            user?.role?.id ?? '',
    preferred_language: user?.preferred_language ?? 'zh-TW',
    note:               user?.note ?? '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const set = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isEdit) {
        const { password, email, ...rest } = form;
        await usersApi.update(user.id, {
          ...rest,
          role_id: rest.role_id || undefined,
        });
      } else {
        await usersApi.create({
          ...form,
          role_id: form.role_id || undefined,
        });
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="card w-full max-w-lg p-6 shadow-xl">
        {/* 標題列 */}
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-gray-800">
            {isEdit ? t('editUser') : t('addUser')}
          </h2>
          <button onClick={() => onClose()} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 姓名 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('fullName')} *</label>
            <input value={form.full_name} onChange={(e) => set('full_name', e.target.value)}
              required className="input" />
          </div>

          {/* Email（編輯時不可改） */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('email')} *</label>
            <input value={form.email} onChange={(e) => set('email', e.target.value)}
              type="email" required disabled={isEdit} className="input" />
          </div>

          {/* 密碼（僅新增時顯示） */}
          {!isEdit && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('password')} *</label>
              <input value={form.password} onChange={(e) => set('password', e.target.value)}
                type="password" required className="input" />
            </div>
          )}

          {/* 角色 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('role')}</label>
            <select value={form.role_id} onChange={(e) => set('role_id', e.target.value)} className="input">
              <option value="">— {tc('noAssigned')} —</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>

          {/* 偏好語言 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('language')}</label>
            <select value={form.preferred_language} onChange={(e) => set('preferred_language', e.target.value)} className="input">
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>

          {/* 備註 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('note')}</label>
            <textarea value={form.note} onChange={(e) => set('note', e.target.value)}
              rows={2} className="input resize-none" />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-2 rounded-md">
              {error}
            </div>
          )}

          {/* 按鈕 */}
          <div className="flex justify-end gap-3 pt-2">
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
