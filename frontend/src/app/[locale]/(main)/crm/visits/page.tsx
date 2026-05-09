'use client';

/**
 * P-05 業務拜訪排程頁面（F-06）
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { apiClient } from '@/lib/api';
import { CalendarDays, Plus, MapPin, CheckCircle, Clock } from 'lucide-react';
import { clsx } from 'clsx';

type ScheduleType = 'first_visit' | 'second_visit' | 'payment_collect' | 'delivery' | 'expo' | 'follow_up' | 'meeting' | 'other';

const SCHEDULE_TYPES: ScheduleType[] = [
  'first_visit', 'second_visit', 'payment_collect', 'delivery', 'expo', 'follow_up', 'meeting', 'other',
];

export default function VisitsPage() {
  const t  = useTranslations('crmVisits');
  const tc = useTranslations('common');
  const [showForm, setShowForm] = useState(false);
  const [dateFilter, setDateFilter] = useState(new Date().toISOString().split('T')[0]);
  const [form, setForm] = useState({
    schedule_date: new Date().toISOString().split('T')[0],
    start_time: '09:00',
    end_time: '10:00',
    schedule_type: 'follow_up',
    title: '',
    location: '',
    description: '',
  });
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['sales-schedules', dateFilter],
    queryFn: async () => {
      const res = await apiClient.get('/crm/schedules', {
        params: { schedule_date: dateFilter || undefined, limit: 50 },
      });
      return res.data;
    },
  });

  const addSchedule = useMutation({
    mutationFn: (d: any) => apiClient.post('/crm/schedules', d),
    onSuccess: () => {
      setShowForm(false);
      qc.invalidateQueries({ queryKey: ['sales-schedules'] });
    },
  });

  const toggleComplete = useMutation({
    mutationFn: ({ id, is_completed }: { id: string; is_completed: boolean }) =>
      apiClient.patch(`/crm/schedules/${id}`, { is_completed }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sales-schedules'] }),
  });

  const schedules = data?.items || [];
  const todayStr = new Date().toISOString().split('T')[0];

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <CalendarDays className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700"
        >
          <Plus size={15} />
          {t('addSchedule')}
        </button>
      </div>

      {/* 新增表單 */}
      {showForm && (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <h3 className="font-semibold text-gray-900">{t('addScheduleTitle')}</h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="col-span-2">
              <label className="block text-gray-600 mb-1">{t('form.title')} <span className="text-red-500">*</span></label>
              <input
                type="text"
                value={form.title}
                onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('form.scheduleType')}</label>
              <select
                value={form.schedule_type}
                onChange={e => setForm(p => ({ ...p, schedule_type: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              >
                {SCHEDULE_TYPES.map(k => (
                  <option key={k} value={k}>{t(`scheduleTypes.${k}`)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('form.date')}</label>
              <input
                type="date"
                value={form.schedule_date}
                onChange={e => setForm(p => ({ ...p, schedule_date: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('form.startTime')}</label>
              <input
                type="time"
                value={form.start_time}
                onChange={e => setForm(p => ({ ...p, start_time: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('form.endTime')}</label>
              <input
                type="time"
                value={form.end_time}
                onChange={e => setForm(p => ({ ...p, end_time: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div className="col-span-3">
              <label className="block text-gray-600 mb-1">{t('form.location')}</label>
              <input
                type="text"
                value={form.location}
                onChange={e => setForm(p => ({ ...p, location: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div className="col-span-3">
              <label className="block text-gray-600 mb-1">{t('form.description')}</label>
              <textarea
                value={form.description}
                onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm h-16"
              />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">{tc('cancel')}</button>
            <button
              onClick={() => addSchedule.mutate(form)}
              disabled={!form.title}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
            >
              {tc('save')}
            </button>
          </div>
        </div>
      )}

      {/* 日期篩選 */}
      <div className="flex items-center gap-3">
        <input
          type="date"
          value={dateFilter}
          onChange={e => setDateFilter(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
        />
        <button
          onClick={() => setDateFilter(todayStr)}
          className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50"
        >
          {t('today')}
        </button>
        <button
          onClick={() => setDateFilter('')}
          className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50"
        >
          {t('all')}
        </button>
        <span className="text-sm text-gray-500">{t('schedulesCount', { count: schedules.length })}</span>
      </div>

      {/* 行程卡片 */}
      <div className="space-y-3">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border p-4 animate-pulse h-20" />
          ))
        ) : schedules.length === 0 ? (
          <div className="bg-white rounded-xl border p-8 text-center text-gray-400">{t('noSchedules')}</div>
        ) : (
          schedules.map((s: any) => (
            <div key={s.id} className={clsx(
              'bg-white rounded-xl border p-4 flex items-start gap-4',
              s.is_completed && 'opacity-60'
            )}>
              <button
                onClick={() => toggleComplete.mutate({ id: s.id, is_completed: !s.is_completed })}
                className="mt-0.5 flex-shrink-0"
              >
                {s.is_completed
                  ? <CheckCircle size={20} className="text-green-500" />
                  : <Clock size={20} className="text-gray-300 hover:text-gray-400" />}
              </button>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className={clsx('font-semibold text-gray-900', s.is_completed && 'line-through')}>
                    {s.title}
                  </h3>
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                    {t(`scheduleTypes.${s.schedule_type}` as any) || s.schedule_type}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span>{s.schedule_date} {s.start_time} – {s.end_time}</span>
                  {s.location && (
                    <span className="flex items-center gap-1">
                      <MapPin size={11} />
                      {s.location}
                    </span>
                  )}
                  {s.customer_name && <span>{t('customerLabel')}{s.customer_name}</span>}
                </div>
                {s.description && (
                  <p className="text-xs text-gray-400 mt-1">{s.description}</p>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
