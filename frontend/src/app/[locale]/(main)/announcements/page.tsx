'use client';

/**
 * K-01 公告管理頁面
 */
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { Megaphone, Plus, AlertTriangle, Info, CheckCircle } from 'lucide-react';
import { clsx } from 'clsx';

const PRIORITY_COLORS: Record<string, string> = {
  low:    'bg-gray-100 text-gray-600',
  normal: 'bg-blue-100 text-blue-700',
  high:   'bg-orange-100 text-orange-700',
  urgent: 'bg-red-100 text-red-700',
};

export default function AnnouncementsPage() {
  const t = useTranslations('announcements');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    title: '',
    category: 'general',
    priority: 'normal',
    content: '',
    is_pinned: false,
    is_published: true,
  });
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['announcements'],
    queryFn: async () => {
      const res = await apiClient.get('/compliance/announcements', { params: { limit: 30 } });
      return res.data;
    },
  });

  const addAnnouncement = useMutation({
    mutationFn: (d: any) => apiClient.post('/compliance/announcements', d),
    onSuccess: () => {
      setShowForm(false);
      qc.invalidateQueries({ queryKey: ['announcements'] });
    },
  });

  const announcements = data?.items || [];

  const PRIORITY_KEYS = ['low', 'normal', 'high', 'urgent'] as const;
  const CATEGORY_KEYS = ['general', 'policy', 'hr', 'it', 'safety', 'training', 'other'] as const;

  const PriorityIcon = ({ p }: { p: string }) => {
    if (p === 'urgent' || p === 'high') return <AlertTriangle size={14} />;
    if (p === 'normal') return <Info size={14} />;
    return <CheckCircle size={14} />;
  };

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Megaphone className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700"
        >
          <Plus size={15} />
          {t('addBtn')}
        </button>
      </div>

      {/* 新增表單 */}
      {showForm && (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <h3 className="font-semibold text-gray-900">{t('formTitle')}</h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="col-span-2">
              <label className="block text-gray-600 mb-1">{t('labelTitle')} <span className="text-red-500">*</span></label>
              <input
                type="text"
                value={form.title}
                onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelCategory')}</label>
              <select
                value={form.category}
                onChange={e => setForm(p => ({ ...p, category: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              >
                {CATEGORY_KEYS.map(k => (
                  <option key={k} value={k}>{t(`category.${k}`)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelPriority')}</label>
              <select
                value={form.priority}
                onChange={e => setForm(p => ({ ...p, priority: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              >
                {PRIORITY_KEYS.map(k => (
                  <option key={k} value={k}>{t(`priority.${k}`)}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2 self-end pb-1">
              <input
                type="checkbox"
                id="is_published"
                checked={form.is_published}
                onChange={e => setForm(p => ({ ...p, is_published: e.target.checked }))}
                className="w-4 h-4"
              />
              <label htmlFor="is_published" className="text-sm text-gray-700">{t('checkPublish')}</label>
            </div>
            <div className="col-span-3">
              <label className="block text-gray-600 mb-1">{t('labelContent')} <span className="text-red-500">*</span></label>
              <textarea
                value={form.content}
                onChange={e => setForm(p => ({ ...p, content: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm h-24"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_pinned"
                checked={form.is_pinned}
                onChange={e => setForm(p => ({ ...p, is_pinned: e.target.checked }))}
                className="w-4 h-4"
              />
              <label htmlFor="is_pinned" className="text-sm text-gray-700">{t('checkPinned')}</label>
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">{t('cancelBtn')}</button>
            <button
              onClick={() => addAnnouncement.mutate(form)}
              disabled={!form.title || !form.content}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
            >
              {t('submitBtn')}
            </button>
          </div>
        </div>
      )}

      {/* 公告列表 */}
      <div className="space-y-3">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border p-4 animate-pulse h-24" />
          ))
        ) : announcements.length === 0 ? (
          <div className="bg-white rounded-xl border p-8 text-center text-gray-400">{t('noData')}</div>
        ) : (
          announcements.map((ann: any) => (
            <div key={ann.id} className={clsx(
              'bg-white rounded-xl border p-4',
              ann.is_pinned && 'border-primary-300 bg-primary-50',
              ann.priority === 'urgent' && 'border-red-200'
            )}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    {ann.is_pinned && (
                      <span className="text-xs text-primary-600 font-medium">📌 {t('pinnedBadge')}</span>
                    )}
                    <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium',
                      PRIORITY_COLORS[ann.priority]
                    )}>
                      <PriorityIcon p={ann.priority} />
                      {t(`priority.${ann.priority}` as any)}
                    </span>
                    <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                      {t(`category.${ann.category}` as any, { defaultValue: ann.category })}
                    </span>
                  </div>
                  <h3 className="font-semibold text-gray-900">{ann.title}</h3>
                  <p className="text-sm text-gray-600 mt-1 line-clamp-2">{ann.content}</p>
                </div>
                <div className="text-right text-xs text-gray-400 flex-shrink-0">
                  <p>{ann.created_at ? ann.created_at.split('T')[0] : ''}</p>
                  {ann.expires_at && <p>{t('expiresPrefix')} {ann.expires_at.split('T')[0]}</p>}
                  {ann.view_count != null && <p className="mt-1">{t('viewCount', { count: ann.view_count })}</p>}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
