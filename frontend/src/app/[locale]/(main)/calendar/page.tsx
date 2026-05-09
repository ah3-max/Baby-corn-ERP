'use client';

/**
 * 行事曆頁面
 * 整合業務行程（SalesSchedule）與會議紀錄（MeetingRecord），以月曆形式顯示。
 */
import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { useTranslations } from 'next-intl';
import { Calendar, ChevronLeft, ChevronRight, Plus, X, Clock, MapPin } from 'lucide-react';
import { clsx } from 'clsx';

const SCHEDULE_TYPE_KEYS = [
  'first_visit', 'second_visit', 'payment_collect', 'delivery',
  'expo', 'follow_up', 'meeting', 'other',
] as const;

/** 以 YYYY-MM-DD 格式回傳本地日期字串 */
function toLocalDate(d: Date) {
  return d.toISOString().split('T')[0];
}

export default function CalendarPage() {
  const t  = useTranslations('calendar');
  const tc = useTranslations('common');

  const today = new Date();
  const [year,  setYear]  = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth()); // 0-based
  const [selectedDate, setSelectedDate] = useState<string>(toLocalDate(today));
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    title: '',
    schedule_type: 'other',
    schedule_date: toLocalDate(today),
    start_time: '',
    end_time: '',
    location: '',
    description: '',
  });

  const qc = useQueryClient();

  /* ── 月份範圍 ── */
  const rangeStart = `${year}-${String(month + 1).padStart(2, '0')}-01`;
  const lastDay    = new Date(year, month + 1, 0).getDate();
  const rangeEnd   = `${year}-${String(month + 1).padStart(2, '0')}-${lastDay}`;

  /* ── API 查詢 ── */
  const { data: schedules = [] } = useQuery({
    queryKey: ['cal-schedules', rangeStart, rangeEnd],
    queryFn: async () => {
      const res = await apiClient.get('/schedules', {
        params: { date_from: rangeStart, date_to: rangeEnd, limit: 200 },
      });
      return res.data?.items ?? res.data ?? [];
    },
  });

  const { data: meetings = [] } = useQuery({
    queryKey: ['cal-meetings', rangeStart, rangeEnd],
    queryFn: async () => {
      const res = await apiClient.get('/compliance/meetings', {
        params: { date_from: rangeStart, date_to: rangeEnd, limit: 200 },
      });
      return res.data?.items ?? res.data ?? [];
    },
  });

  /* ── 新增行程 ── */
  const addSchedule = useMutation({
    mutationFn: (d: any) => apiClient.post('/schedules', d),
    onSuccess: () => {
      setShowForm(false);
      setForm(f => ({ ...f, title: '', start_time: '', end_time: '', location: '', description: '' }));
      qc.invalidateQueries({ queryKey: ['cal-schedules'] });
    },
  });

  /* ── 月曆格子 ── */
  const cells = useMemo(() => {
    const firstWeekday = new Date(year, month, 1).getDay(); // 0=Sun
    const totalDays    = new Date(year, month + 1, 0).getDate();
    const grid: (string | null)[] = Array(firstWeekday).fill(null);
    for (let d = 1; d <= totalDays; d++) {
      grid.push(`${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`);
    }
    // 補滿 6 行
    while (grid.length % 7 !== 0) grid.push(null);
    return grid;
  }, [year, month]);

  /* ── 依日期建立事件 map ── */
  const eventMap = useMemo(() => {
    const map: Record<string, { type: 'schedule' | 'meeting'; item: any }[]> = {};
    for (const s of schedules) {
      const k = s.schedule_date?.slice(0, 10);
      if (!k) continue;
      (map[k] ??= []).push({ type: 'schedule', item: s });
    }
    for (const m of meetings) {
      const k = m.meeting_date?.slice(0, 10);
      if (!k) continue;
      (map[k] ??= []).push({ type: 'meeting', item: m });
    }
    return map;
  }, [schedules, meetings]);

  /* ── 月份切換 ── */
  const prevMonth = () => {
    if (month === 0) { setYear(y => y - 1); setMonth(11); }
    else setMonth(m => m - 1);
  };
  const nextMonth = () => {
    if (month === 11) { setYear(y => y + 1); setMonth(0); }
    else setMonth(m => m + 1);
  };
  const goToday = () => {
    setYear(today.getFullYear());
    setMonth(today.getMonth());
    setSelectedDate(toLocalDate(today));
  };

  const selectedEvents = eventMap[selectedDate] ?? [];
  const weekdayKeys = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'] as const;
  const monthLabel  = new Date(year, month, 1).toLocaleDateString('zh-TW', { year: 'numeric', month: 'long' });

  return (
    <div className="p-6 space-y-5">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Calendar className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">{t('subtitle')}</p>
        </div>
        <button
          onClick={() => {
            setForm(f => ({ ...f, schedule_date: selectedDate }));
            setShowForm(true);
          }}
          className="flex items-center gap-1.5 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700"
        >
          <Plus size={15} />
          {t('addSchedule')}
        </button>
      </div>

      {/* 新增表單 */}
      {showForm && (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">{t('addSchedule')}</h3>
            <button onClick={() => setShowForm(false)}><X size={16} className="text-gray-400" /></button>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            {/* 標題 */}
            <div className="col-span-2">
              <label className="block text-gray-600 mb-1">{t('form.title')} <span className="text-red-500">*</span></label>
              <input
                type="text"
                value={form.title}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            {/* 行程類型 */}
            <div>
              <label className="block text-gray-600 mb-1">{t('form.scheduleType')}</label>
              <select
                value={form.schedule_type}
                onChange={e => setForm(f => ({ ...f, schedule_type: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              >
                {SCHEDULE_TYPE_KEYS.map(k => (
                  <option key={k} value={k}>{t(`scheduleTypes.${k}`)}</option>
                ))}
              </select>
            </div>
            {/* 日期 */}
            <div>
              <label className="block text-gray-600 mb-1">{t('form.date')}</label>
              <input
                type="date"
                value={form.schedule_date}
                onChange={e => setForm(f => ({ ...f, schedule_date: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            {/* 開始 / 結束時間 */}
            <div>
              <label className="block text-gray-600 mb-1">{t('form.startTime')}</label>
              <input
                type="time"
                value={form.start_time}
                onChange={e => setForm(f => ({ ...f, start_time: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('form.endTime')}</label>
              <input
                type="time"
                value={form.end_time}
                onChange={e => setForm(f => ({ ...f, end_time: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            {/* 地點 */}
            <div className="col-span-2">
              <label className="block text-gray-600 mb-1">{t('form.location')}</label>
              <input
                type="text"
                value={form.location}
                onChange={e => setForm(f => ({ ...f, location: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            {/* 說明 */}
            <div className="col-span-2">
              <label className="block text-gray-600 mb-1">{t('form.description')}</label>
              <textarea
                value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm h-16"
              />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">{t('cancelBtn')}</button>
            <button
              onClick={() => addSchedule.mutate(form)}
              disabled={!form.title || addSchedule.isPending}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
            >
              {t('saveBtn')}
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* ── 月曆 ── */}
        <div className="col-span-2 bg-white rounded-xl border p-5">
          {/* 月份導航 */}
          <div className="flex items-center justify-between mb-4">
            <button onClick={prevMonth} className="p-1.5 hover:bg-gray-100 rounded-lg" title={t('prevMonth')}>
              <ChevronLeft size={18} />
            </button>
            <div className="flex items-center gap-3">
              <h2 className="text-base font-semibold text-gray-900">{monthLabel}</h2>
              <button
                onClick={goToday}
                className="text-xs px-2.5 py-1 bg-primary-50 text-primary-700 rounded-full hover:bg-primary-100"
              >
                {t('today')}
              </button>
            </div>
            <button onClick={nextMonth} className="p-1.5 hover:bg-gray-100 rounded-lg" title={t('nextMonth')}>
              <ChevronRight size={18} />
            </button>
          </div>

          {/* 星期標頭 */}
          <div className="grid grid-cols-7 mb-1">
            {weekdayKeys.map(k => (
              <div key={k} className="text-center text-xs font-medium text-gray-400 py-1">
                {t(`weekdays.${k}`)}
              </div>
            ))}
          </div>

          {/* 日期格子 */}
          <div className="grid grid-cols-7 gap-px bg-gray-100 rounded-lg overflow-hidden">
            {cells.map((dateStr, idx) => {
              if (!dateStr) {
                return <div key={`empty-${idx}`} className="bg-white min-h-[72px]" />;
              }
              const isToday    = dateStr === toLocalDate(today);
              const isSelected = dateStr === selectedDate;
              const events     = eventMap[dateStr] ?? [];
              const dayNum     = parseInt(dateStr.slice(8), 10);

              return (
                <button
                  key={dateStr}
                  onClick={() => setSelectedDate(dateStr)}
                  className={clsx(
                    'bg-white min-h-[72px] p-1.5 text-left hover:bg-gray-50 transition-colors',
                    isSelected && 'ring-2 ring-inset ring-primary-500',
                  )}
                >
                  {/* 日期數字 */}
                  <span className={clsx(
                    'inline-flex items-center justify-center w-6 h-6 text-xs rounded-full mb-1',
                    isToday ? 'bg-primary-600 text-white font-bold' : 'text-gray-700',
                  )}>
                    {dayNum}
                  </span>
                  {/* 事件小點 / 標籤 */}
                  <div className="space-y-0.5">
                    {events.slice(0, 3).map((ev, i) => (
                      <div
                        key={i}
                        className={clsx(
                          'text-[10px] truncate rounded px-1 leading-4',
                          ev.type === 'schedule'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-blue-100 text-blue-800',
                        )}
                      >
                        {ev.item.title}
                      </div>
                    ))}
                    {events.length > 3 && (
                      <div className="text-[10px] text-gray-400 pl-1">+{events.length - 3}</div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {/* 圖例 */}
          <div className="flex gap-4 mt-3 justify-end">
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <span className="w-3 h-3 rounded bg-green-200 inline-block" />
              {t('scheduleLabel')}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <span className="w-3 h-3 rounded bg-blue-200 inline-block" />
              {t('meetingLabel')}
            </div>
          </div>
        </div>

        {/* ── 右側：選定日期的事件列表 ── */}
        <div className="bg-white rounded-xl border p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-1">{selectedDate}</h3>
          <p className="text-xs text-gray-400 mb-4">
            {selectedEvents.length > 0
              ? t('eventsCount', { count: selectedEvents.length })
              : t('noEvents')}
          </p>

          {selectedEvents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-300">
              <Calendar size={36} />
              <p className="text-sm mt-2">{t('noEvents')}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {selectedEvents.map((ev, i) => {
                const isSchedule = ev.type === 'schedule';
                return (
                  <div
                    key={i}
                    className={clsx(
                      'rounded-lg p-3 border-l-4',
                      isSchedule ? 'border-green-400 bg-green-50' : 'border-blue-400 bg-blue-50',
                    )}
                  >
                    {/* 類型標籤 */}
                    <div className="flex items-center justify-between mb-1">
                      <span className={clsx(
                        'text-[10px] font-semibold uppercase tracking-wide',
                        isSchedule ? 'text-green-600' : 'text-blue-600',
                      )}>
                        {isSchedule ? t('scheduleLabel') : t('meetingLabel')}
                      </span>
                      {isSchedule && ev.item.is_completed && (
                        <span className="text-[10px] px-1.5 py-0.5 bg-gray-200 text-gray-600 rounded-full">
                          {t('completedBadge')}
                        </span>
                      )}
                    </div>
                    {/* 標題 */}
                    <p className="text-sm font-medium text-gray-900 leading-snug">{ev.item.title}</p>
                    {/* 時間 */}
                    {isSchedule && (ev.item.start_time || ev.item.end_time) && (
                      <div className="flex items-center gap-1 mt-1 text-xs text-gray-500">
                        <Clock size={11} />
                        {ev.item.start_time}{ev.item.end_time ? ` – ${ev.item.end_time}` : ''}
                      </div>
                    )}
                    {/* 地點 */}
                    {ev.item.location && (
                      <div className="flex items-center gap-1 mt-0.5 text-xs text-gray-500">
                        <MapPin size={11} />
                        {ev.item.location}
                      </div>
                    )}
                    {/* 行程類型（schedule） / 會議類型（meeting） */}
                    {isSchedule && ev.item.schedule_type && (
                      <p className="text-[10px] text-gray-400 mt-1">
                        {t(`scheduleTypes.${ev.item.schedule_type}` as any, { defaultValue: ev.item.schedule_type })}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
