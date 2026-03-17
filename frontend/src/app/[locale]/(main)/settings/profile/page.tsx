'use client';

/**
 * 個人設定頁面 /settings/profile
 */
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { authApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';

export default function ProfilePage() {
  const t = useTranslations('profile');
  const tc = useTranslations('common');
  const { showToast } = useToast();

  const [oldPwd, setOldPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg('');
    setError('');

    if (newPwd !== confirmPwd) {
      setError(t('passwordMismatch'));
      return;
    }

    setLoading(true);
    try {
      await authApi.changePassword(oldPwd, newPwd);
      showToast(t('passwordChangeSuccess'), 'success');
      setMsg(t('passwordChangeSuccess'));
      setOldPwd('');
      setNewPwd('');
      setConfirmPwd('');
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? tc('error');
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">{t('title')}</h1>

      <div className="card p-6">
        <h2 className="text-base font-semibold text-gray-700 mb-4">{t('changePassword')}</h2>
        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('oldPassword')}</label>
            <input type="password" value={oldPwd} onChange={(e) => setOldPwd(e.target.value)}
              required className="input" autoComplete="current-password" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('newPassword')}</label>
            <input type="password" value={newPwd} onChange={(e) => setNewPwd(e.target.value)}
              required className="input" autoComplete="new-password" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('confirmNewPassword')}</label>
            <input type="password" value={confirmPwd} onChange={(e) => setConfirmPwd(e.target.value)}
              required className="input" autoComplete="new-password" />
          </div>

          {msg && (
            <div className="bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-2 rounded-md">{msg}</div>
          )}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-2 rounded-md">{error}</div>
          )}

          <div className="flex justify-end pt-2">
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? '...' : tc('save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
