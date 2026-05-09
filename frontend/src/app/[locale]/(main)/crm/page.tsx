'use client';

/**
 * CRM 管理 — 儀表板 + 活動 + 任務 + 排行
 */
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { UserCircle, Target, ListTodo, Trophy, Plus, Phone, Calendar, X } from 'lucide-react';
import { crmApi, customersApi } from '@/lib/api';
import type { Supplier } from '@/types';
import { useToast } from '@/contexts/ToastContext';
import { useUser } from '@/contexts/UserContext';

export default function CRMPage() {
  const t  = useTranslations('crm');
  const tc = useTranslations('common');
  const { showToast } = useToast();
  const { user } = useUser();
  const [tab, setTab] = useState<'dashboard' | 'activities' | 'tasks' | 'ranking'>('dashboard');
  const [dashboard, setDashboard] = useState<any>(null);
  const [activities, setActivities] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [ranking, setRanking] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showActivityForm, setShowActivityForm] = useState(false);
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [customers, setCustomers] = useState<any[]>([]);

  useEffect(() => { customersApi.list({}).then(r => setCustomers(r.data)).catch(() => {}); }, []);

  const TABS = [
    { key: 'dashboard',  label: t('tabs.dashboard') },
    { key: 'activities', label: t('tabs.activities') },
    { key: 'tasks',      label: t('tabs.tasks') },
    { key: 'ranking',    label: t('tabs.ranking') },
  ] as const;

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        if (tab === 'dashboard') {
          const { data } = await crmApi.dashboard();
          setDashboard(data);
        } else if (tab === 'activities') {
          const { data } = await crmApi.listActivities({});
          setActivities(data);
        } else if (tab === 'tasks') {
          const { data } = await crmApi.listTasks({});
          setTasks(data);
        } else if (tab === 'ranking') {
          const { data } = await crmApi.ranking();
          setRanking(data);
        }
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    };
    load();
  }, [tab]);

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
        <div className="flex gap-2">
          {tab === 'activities' && (
            <button onClick={() => setShowActivityForm(true)} className="btn-primary flex items-center gap-2"><Plus size={16} /> {t('addActivity')}</button>
          )}
          {tab === 'tasks' && (
            <button onClick={() => setShowTaskForm(true)} className="btn-primary flex items-center gap-2"><Plus size={16} /> {t('assignTask')}</button>
          )}
        </div>
      </div>

      {/* Tab */}
      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-lg w-fit">
        {TABS.map(tb => (
          <button key={tb.key} onClick={() => setTab(tb.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${tab === tb.key ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
            {tb.label}
          </button>
        ))}
      </div>

      {loading ? <div className="text-center py-16 text-gray-400">{tc('loading')}</div> : (
        <>
          {/* 業務總覽 */}
          {tab === 'dashboard' && dashboard && (
            <div>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                {[
                  { label: t('monthlyRevenue'),    value: `$${(dashboard.total_revenue_twd || 0).toLocaleString()}`, icon: Target,    color: 'blue' },
                  { label: t('confirmedPayments'), value: `$${(dashboard.confirmed_payments_twd || 0).toLocaleString()}`, icon: Target, color: 'green' },
                  { label: t('activeCustomers'),   value: dashboard.active_customers, icon: UserCircle, color: 'purple' },
                  { label: t('pendingTasks'),       value: dashboard.pending_tasks,    icon: ListTodo,   color: 'orange' },
                ].map((card, i) => (
                  <div key={i} className="card p-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 bg-${card.color}-100 rounded-lg flex items-center justify-center`}>
                        <card.icon size={20} className={`text-${card.color}-600`} />
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">{card.label}</p>
                        <p className="text-xl font-bold text-gray-800">{card.value}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="card p-4">
                  <p className="text-sm text-gray-500">{t('newCustomers')}</p>
                  <p className="text-2xl font-bold text-gray-800">{dashboard.new_customers}</p>
                </div>
                <div className="card p-4">
                  <p className="text-sm text-gray-500">{t('activityCount')}</p>
                  <p className="text-2xl font-bold text-gray-800">{dashboard.activity_count}</p>
                </div>
              </div>
            </div>
          )}

          {/* 活動記錄 */}
          {tab === 'activities' && (
            <div className="space-y-3">
              {activities.length === 0 ? <p className="text-gray-400 text-center py-10">{t('noActivities')}</p> : activities.map((a: any) => (
                <div key={a.id} className="card p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-mono text-sm text-gray-500">{a.activity_no}</span>
                      <span className={`ml-2 px-2 py-0.5 rounded-full text-xs font-medium ${
                        a.activity_type === 'visit' ? 'bg-blue-100 text-blue-700' :
                        a.activity_type === 'call' ? 'bg-green-100 text-green-700' :
                        a.activity_type === 'complaint' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>{t(`activityTypes.${a.activity_type}` as any) || a.activity_type}</span>
                    </div>
                    <span className="text-xs text-gray-400">{new Date(a.activity_date).toLocaleDateString()}</span>
                  </div>
                  <div className="mt-2 flex items-center gap-4 text-sm text-gray-600">
                    <span className="font-medium">{a.customer_name}</span>
                    <span className="text-gray-400">by {a.sales_user_name}</span>
                  </div>
                  {a.summary && <p className="mt-1 text-sm text-gray-500">{a.summary}</p>}
                  {a.follow_up_date && (
                    <div className="mt-2 flex items-center gap-1 text-xs text-orange-600">
                      <Calendar size={12} /> {t('followUp')}{a.follow_up_date} {a.follow_up_action || ''}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* 任務看板 */}
          {tab === 'tasks' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {(['pending', 'in_progress', 'completed'] as const).map(status => (
                <div key={status}>
                  <h3 className="text-sm font-semibold text-gray-500 mb-3 uppercase">
                    {t(`taskStatus.${status}`)}
                    <span className="ml-1 text-gray-400">({tasks.filter((tk: any) => tk.status === status).length})</span>
                  </h3>
                  <div className="space-y-2">
                    {tasks.filter((tk: any) => tk.status === status).map((tk: any) => (
                      <div key={tk.id} className={`card p-3 border-l-4 ${
                        tk.priority === 'urgent' ? 'border-red-500' :
                        tk.priority === 'high' ? 'border-orange-500' :
                        tk.priority === 'normal' ? 'border-blue-500' : 'border-gray-300'
                      }`}>
                        <p className="text-sm font-medium text-gray-800">{tk.title}</p>
                        <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                          <span>{tk.assignee_name}</span>
                          {tk.customer_name && <span>· {tk.customer_name}</span>}
                          {tk.due_date && <span>· {tk.due_date}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 業績排行 */}
          {tab === 'ranking' && ranking && (
            <div className="card p-5">
              <h3 className="font-semibold text-gray-800 mb-4">{t('monthRanking', { month: ranking.month })}</h3>
              <div className="space-y-3">
                {(ranking.ranking || []).map((r: any) => (
                  <div key={r.user_id} className="flex items-center justify-between py-3 border-b border-gray-50 last:border-0">
                    <div className="flex items-center gap-3">
                      <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                        r.rank === 1 ? 'bg-yellow-100 text-yellow-700' :
                        r.rank === 2 ? 'bg-gray-200 text-gray-700' :
                        r.rank === 3 ? 'bg-orange-100 text-orange-700' : 'bg-gray-100 text-gray-500'
                      }`}>{r.rank}</span>
                      <span className="font-medium text-gray-800">{r.user_name}</span>
                    </div>
                    <div className="flex items-center gap-6 text-sm">
                      <span className="text-gray-600">${r.total_revenue_twd.toLocaleString()}</span>
                      <div className="w-24">
                        <div className="bg-gray-100 rounded-full h-2">
                          <div className="bg-primary-500 h-2 rounded-full" style={{ width: `${Math.min(100, r.achievement_pct)}%` }} />
                        </div>
                      </div>
                      <span className={`font-semibold w-14 text-right ${r.achievement_pct >= 100 ? 'text-green-600' : 'text-gray-600'}`}>
                        {r.achievement_pct}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* 新增活動 Modal */}
      {showActivityForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-gray-800">{t('addActivityTitle')}</h3>
              <button onClick={() => setShowActivityForm(false)}><X size={18} className="text-gray-400" /></button>
            </div>
            <form onSubmit={async (e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              try {
                await crmApi.createActivity({
                  customer_id: fd.get('customer_id'),
                  activity_type: fd.get('activity_type'),
                  summary: fd.get('summary'),
                });
                setShowActivityForm(false);
                setTab('activities');
                const { data } = await crmApi.listActivities({});
                setActivities(data);
                showToast(t('activityCreated'), 'success');
              } catch { showToast(t('activityFailed'), 'error'); }
            }} className="space-y-3">
              <select name="customer_id" required className="input w-full">
                <option value="">{t('selectCustomer')}</option>
                {customers.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <select name="activity_type" className="input w-full">
                {(['visit','call','email','meeting','sample','complaint'] as const).map(type => (
                  <option key={type} value={type}>{t(`activityTypes.${type}`)}</option>
                ))}
              </select>
              <textarea name="summary" placeholder={t('activitySummaryPlaceholder')} className="input w-full h-20 resize-none" />
              <div className="flex gap-2">
                <button type="button" onClick={() => setShowActivityForm(false)} className="btn-secondary flex-1">{tc('cancel')}</button>
                <button type="submit" className="btn-primary flex-1">{t('createBtn')}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 指派任務 Modal */}
      {showTaskForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-gray-800">{t('assignTaskTitle')}</h3>
              <button onClick={() => setShowTaskForm(false)}><X size={18} className="text-gray-400" /></button>
            </div>
            <form onSubmit={async (e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              try {
                await crmApi.createTask({
                  assigned_to: fd.get('assigned_to'),
                  title: fd.get('title'),
                  task_type: fd.get('task_type'),
                  priority: fd.get('priority'),
                  customer_id: fd.get('customer_id') || undefined,
                  due_date: fd.get('due_date') || undefined,
                });
                setShowTaskForm(false);
                setTab('tasks');
                const { data } = await crmApi.listTasks({});
                setTasks(data);
                showToast(t('taskAssigned'), 'success');
              } catch { showToast(t('taskFailed'), 'error'); }
            }} className="space-y-3">
              <input name="assigned_to" placeholder={t('assignToPlaceholder')} required className="input w-full" />
              <input name="title" placeholder={t('taskTitlePlaceholder')} required className="input w-full" />
              <div className="grid grid-cols-2 gap-3">
                <select name="task_type" className="input">
                  {(['follow_up','visit','collection','delivery','sample','other'] as const).map(type => (
                    <option key={type} value={type}>{t(`taskTypes.${type}`)}</option>
                  ))}
                </select>
                <select name="priority" className="input">
                  {(['urgent','high','normal','low'] as const).map(p => (
                    <option key={p} value={p}>{t(`priority.${p}`)}</option>
                  ))}
                </select>
              </div>
              <select name="customer_id" className="input w-full">
                <option value="">{t('optionalCustomer')}</option>
                {customers.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <input name="due_date" type="date" className="input w-full" />
              <div className="flex gap-2">
                <button type="button" onClick={() => setShowTaskForm(false)} className="btn-secondary flex-1">{tc('cancel')}</button>
                <button type="submit" className="btn-primary flex-1">{t('assignBtn')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
