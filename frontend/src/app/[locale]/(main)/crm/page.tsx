'use client';

/**
 * CRM 管理 — 儀表板 + 活動 + 任務 + 排行
 */
import { useEffect, useState } from 'react';
import { UserCircle, Target, ListTodo, Trophy, Plus, Phone, Calendar, X } from 'lucide-react';
import { crmApi, customersApi } from '@/lib/api';
import type { Supplier } from '@/types';
import { useToast } from '@/contexts/ToastContext';
import { useUser } from '@/contexts/UserContext';

export default function CRMPage() {
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
    { key: 'dashboard', label: '業務總覽' },
    { key: 'activities', label: '活動記錄' },
    { key: 'tasks', label: '任務看板' },
    { key: 'ranking', label: '業績排行' },
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
        <h1 className="text-2xl font-bold text-gray-800">CRM 管理</h1>
        <div className="flex gap-2">
          {tab === 'activities' && (
            <button onClick={() => setShowActivityForm(true)} className="btn-primary flex items-center gap-2"><Plus size={16} /> 新增活動</button>
          )}
          {tab === 'tasks' && (
            <button onClick={() => setShowTaskForm(true)} className="btn-primary flex items-center gap-2"><Plus size={16} /> 指派任務</button>
          )}
        </div>
      </div>

      {/* Tab */}
      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-lg w-fit">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${tab === t.key ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {loading ? <div className="text-center py-16 text-gray-400">載入中...</div> : (
        <>
          {/* 業務總覽 */}
          {tab === 'dashboard' && dashboard && (
            <div>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                {[
                  { label: '本月營收 (TWD)', value: `$${(dashboard.total_revenue_twd || 0).toLocaleString()}`, icon: Target, color: 'blue' },
                  { label: '已確認收款', value: `$${(dashboard.confirmed_payments_twd || 0).toLocaleString()}`, icon: Target, color: 'green' },
                  { label: '活躍客戶', value: dashboard.active_customers, icon: UserCircle, color: 'purple' },
                  { label: '待完成任務', value: dashboard.pending_tasks, icon: ListTodo, color: 'orange' },
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
                  <p className="text-sm text-gray-500">本月新客戶</p>
                  <p className="text-2xl font-bold text-gray-800">{dashboard.new_customers}</p>
                </div>
                <div className="card p-4">
                  <p className="text-sm text-gray-500">本月拜訪次數</p>
                  <p className="text-2xl font-bold text-gray-800">{dashboard.activity_count}</p>
                </div>
              </div>
            </div>
          )}

          {/* 活動記錄 */}
          {tab === 'activities' && (
            <div className="space-y-3">
              {activities.length === 0 ? <p className="text-gray-400 text-center py-10">尚無活動記錄</p> : activities.map((a: any) => (
                <div key={a.id} className="card p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-mono text-sm text-gray-500">{a.activity_no}</span>
                      <span className={`ml-2 px-2 py-0.5 rounded-full text-xs font-medium ${
                        a.activity_type === 'visit' ? 'bg-blue-100 text-blue-700' :
                        a.activity_type === 'call' ? 'bg-green-100 text-green-700' :
                        a.activity_type === 'complaint' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>{a.activity_type}</span>
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
                      <Calendar size={12} /> 跟進：{a.follow_up_date} {a.follow_up_action || ''}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* 任務看板 */}
          {tab === 'tasks' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {['pending', 'in_progress', 'completed'].map(status => (
                <div key={status}>
                  <h3 className="text-sm font-semibold text-gray-500 mb-3 uppercase">
                    {status === 'pending' ? '待處理' : status === 'in_progress' ? '進行中' : '已完成'}
                    <span className="ml-1 text-gray-400">({tasks.filter((t: any) => t.status === status).length})</span>
                  </h3>
                  <div className="space-y-2">
                    {tasks.filter((t: any) => t.status === status).map((t: any) => (
                      <div key={t.id} className={`card p-3 border-l-4 ${
                        t.priority === 'urgent' ? 'border-red-500' :
                        t.priority === 'high' ? 'border-orange-500' :
                        t.priority === 'normal' ? 'border-blue-500' : 'border-gray-300'
                      }`}>
                        <p className="text-sm font-medium text-gray-800">{t.title}</p>
                        <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                          <span>{t.assignee_name}</span>
                          {t.customer_name && <span>· {t.customer_name}</span>}
                          {t.due_date && <span>· {t.due_date}</span>}
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
              <h3 className="font-semibold text-gray-800 mb-4">{ranking.month} 業務排行</h3>
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
              <h3 className="font-bold text-gray-800">新增活動</h3>
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
                setTab('activities'); // 刷新
                const { data } = await crmApi.listActivities({});
                setActivities(data);
                showToast('活動已建立', 'success');
              } catch { showToast('建立失敗', 'error'); }
            }} className="space-y-3">
              <select name="customer_id" required className="input w-full">
                <option value="">選擇客戶</option>
                {customers.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <select name="activity_type" className="input w-full">
                {['visit','call','email','meeting','sample','complaint'].map(t => (
                  <option key={t} value={t}>{t === 'visit' ? '拜訪' : t === 'call' ? '電話' : t === 'email' ? '郵件' : t === 'meeting' ? '會議' : t === 'sample' ? '送樣' : '客訴'}</option>
                ))}
              </select>
              <textarea name="summary" placeholder="活動摘要" className="input w-full h-20 resize-none" />
              <div className="flex gap-2">
                <button type="button" onClick={() => setShowActivityForm(false)} className="btn-secondary flex-1">取消</button>
                <button type="submit" className="btn-primary flex-1">建立</button>
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
              <h3 className="font-bold text-gray-800">指派任務</h3>
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
                showToast('任務已指派', 'success');
              } catch { showToast('指派失敗', 'error'); }
            }} className="space-y-3">
              <input name="assigned_to" placeholder="指派給（User ID）" required className="input w-full" />
              <input name="title" placeholder="任務標題 *" required className="input w-full" />
              <div className="grid grid-cols-2 gap-3">
                <select name="task_type" className="input">
                  {['follow_up','visit','collection','delivery','sample','other'].map(t => (
                    <option key={t} value={t}>{t === 'follow_up' ? '跟進' : t === 'visit' ? '拜訪' : t === 'collection' ? '收款' : t === 'delivery' ? '送貨' : t === 'sample' ? '送樣' : '其他'}</option>
                  ))}
                </select>
                <select name="priority" className="input">
                  {['urgent','high','normal','low'].map(p => (
                    <option key={p} value={p}>{p === 'urgent' ? '緊急' : p === 'high' ? '高' : p === 'normal' ? '一般' : '低'}</option>
                  ))}
                </select>
              </div>
              <select name="customer_id" className="input w-full">
                <option value="">關聯客戶（選填）</option>
                {customers.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <input name="due_date" type="date" className="input w-full" />
              <div className="flex gap-2">
                <button type="button" onClick={() => setShowTaskForm(false)} className="btn-secondary flex-1">取消</button>
                <button type="submit" className="btn-primary flex-1">指派</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
