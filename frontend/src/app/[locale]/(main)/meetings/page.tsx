'use client';

/**
 * K-04/05 會議記錄頁面
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { Video, Plus, Mic, CheckSquare, Clock } from 'lucide-react';
import { clsx } from 'clsx';
import { useTranslations } from 'next-intl';

const MEETING_TYPE_KEYS = ['weekly_admin', 'channel_negotiation', 'supplier_meeting', 'internal', 'board', 'other'] as const;

export default function MeetingsPage() {
  const t = useTranslations('meetings');
  const [showForm, setShowForm] = useState(false);
  const [selectedMeeting, setSelectedMeeting] = useState<string | null>(null);
  const [form, setForm] = useState({
    title: '',
    meeting_type: 'internal',
    meeting_date: new Date().toISOString().split('T')[0],
    location: '',
    summary: '',
  });
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['meeting-records'],
    queryFn: async () => {
      const res = await apiClient.get('/compliance/meetings', { params: { limit: 30 } });
      return res.data;
    },
  });

  const { data: actionData } = useQuery({
    queryKey: ['meeting-actions', selectedMeeting],
    queryFn: async () => {
      if (!selectedMeeting) return null;
      const res = await apiClient.get(`/compliance/meetings/${selectedMeeting}/actions`);
      return res.data;
    },
    enabled: !!selectedMeeting,
  });

  const addMeeting = useMutation({
    mutationFn: (d: any) => apiClient.post('/compliance/meetings', d),
    onSuccess: () => {
      setShowForm(false);
      qc.invalidateQueries({ queryKey: ['meeting-records'] });
    },
  });

  const meetings = data?.items || [];
  const actions = actionData?.items || [];

  const selectedMeetingData = meetings.find((m: any) => m.id === selectedMeeting);

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Video className="text-primary-600" size={24} />
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
              <label className="block text-gray-600 mb-1">{t('labelType')}</label>
              <select
                value={form.meeting_type}
                onChange={e => setForm(p => ({ ...p, meeting_type: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              >
                {MEETING_TYPE_KEYS.map(k => (
                  <option key={k} value={k}>{t(`meetingType.${k}`)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelDate')}</label>
              <input
                type="date"
                value={form.meeting_date}
                onChange={e => setForm(p => ({ ...p, meeting_date: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelLocation')}</label>
              <input
                type="text"
                value={form.location}
                onChange={e => setForm(p => ({ ...p, location: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div className="col-span-3">
              <label className="block text-gray-600 mb-1">{t('labelSummary')}</label>
              <textarea
                value={form.summary}
                onChange={e => setForm(p => ({ ...p, summary: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm h-20"
              />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">{t('cancelBtn')}</button>
            <button
              onClick={() => addMeeting.mutate(form)}
              disabled={!form.title}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
            >
              {t('saveBtn')}
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* 會議列表 */}
        <div className="col-span-1 space-y-2">
          <h2 className="font-semibold text-gray-900 text-sm">{t('listTitle')}</h2>
          {isLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-white rounded-xl border p-3 animate-pulse h-16" />
            ))
          ) : meetings.length === 0 ? (
            <div className="bg-white rounded-xl border p-4 text-center text-gray-400 text-sm">{t('noMeetings')}</div>
          ) : (
            meetings.map((m: any) => (
              <button
                key={m.id}
                onClick={() => setSelectedMeeting(selectedMeeting === m.id ? null : m.id)}
                className={clsx(
                  'w-full bg-white rounded-xl border p-3 text-left hover:shadow-sm transition-shadow',
                  selectedMeeting === m.id && 'ring-2 ring-primary-500'
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 text-sm truncate">{m.title}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-gray-400">{m.meeting_date}</span>
                      <span className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                        {t(`meetingType.${m.meeting_type}` as any, { defaultValue: m.meeting_type })}
                      </span>
                    </div>
                  </div>
                  {m.ai_summary && (
                    <Mic size={13} className="text-purple-400 flex-shrink-0 mt-0.5" title={t('aiSummaryTooltip')} />
                  )}
                </div>
              </button>
            ))
          )}
        </div>

        {/* 會議詳情 */}
        <div className="col-span-2">
          {selectedMeetingData ? (
            <div className="space-y-4">
              <div className="bg-white rounded-xl border p-5">
                <h2 className="font-semibold text-gray-900 text-lg mb-1">{selectedMeetingData.title}</h2>
                <div className="flex items-center gap-3 text-sm text-gray-500 mb-3">
                  <span>{selectedMeetingData.meeting_date}</span>
                  {selectedMeetingData.location && <span>· {selectedMeetingData.location}</span>}
                  <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                    {t(`meetingType.${selectedMeetingData.meeting_type}` as any, { defaultValue: selectedMeetingData.meeting_type })}
                  </span>
                </div>
                {selectedMeetingData.ai_summary ? (
                  <div className="bg-purple-50 border border-purple-100 rounded-lg p-3 text-sm text-gray-700">
                    <p className="text-xs text-purple-500 font-medium mb-1 flex items-center gap-1">
                      <Mic size={11} /> {t('aiSummary')}
                    </p>
                    {selectedMeetingData.ai_summary}
                  </div>
                ) : selectedMeetingData.summary ? (
                  <p className="text-sm text-gray-700">{selectedMeetingData.summary}</p>
                ) : (
                  <p className="text-sm text-gray-400">{t('noSummary')}</p>
                )}
              </div>

              {/* 行動事項 */}
              <div className="bg-white rounded-xl border overflow-hidden">
                <div className="px-4 py-3 border-b bg-gray-50 flex items-center gap-2">
                  <CheckSquare size={15} className="text-gray-500" />
                  <h3 className="font-semibold text-gray-900 text-sm">{t('actionsTitle')}</h3>
                </div>
                {actions.length === 0 ? (
                  <div className="p-4 text-center text-gray-400 text-sm">{t('noActions')}</div>
                ) : (
                  <div className="divide-y divide-gray-100">
                    {actions.map((a: any) => (
                      <div key={a.id} className="px-4 py-3 flex items-center gap-3">
                        <span className={clsx('w-2 h-2 rounded-full flex-shrink-0',
                          a.status === 'done' ? 'bg-green-500' :
                          a.status === 'in_progress' ? 'bg-blue-500' :
                          a.status === 'cancelled' ? 'bg-red-500' : 'bg-gray-300'
                        )} />
                        <div className="flex-1">
                          <p className="text-sm text-gray-900">{a.action_title}</p>
                          {a.owner_user_id && (
                            <p className="text-xs text-gray-400">{t('ownerLabel')}{a.owner_user_id}</p>
                          )}
                        </div>
                        {a.due_date && (
                          <div className="text-right flex-shrink-0">
                            <p className="text-xs text-gray-500 flex items-center gap-1">
                              <Clock size={11} />
                              {a.due_date}
                            </p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border p-8 text-center text-gray-400 h-full flex items-center justify-center">
              <div>
                <Video size={32} className="mx-auto mb-2 text-gray-300" />
                <p className="text-sm">{t('selectPrompt')}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
