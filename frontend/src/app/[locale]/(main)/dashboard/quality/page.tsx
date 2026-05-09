'use client';

/**
 * O-03 品質儀表板
 */
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { apiClient } from '@/lib/api';
import { ShieldCheck, AlertTriangle, CheckCircle, ThumbsDown, Clock, FileText } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { clsx } from 'clsx';

export default function QualityDashboard() {
  const t = useTranslations('qualityDashboard');

  const { data: qcData } = useQuery({
    queryKey: ['qc-dash-records'],
    queryFn: async () => {
      const res = await apiClient.get('/qc/records', { params: { limit: 100 } });
      return res.data;
    },
  });

  const { data: inspData } = useQuery({
    queryKey: ['qc-dash-inspections'],
    queryFn: async () => {
      const res = await apiClient.get('/qc/inspections', { params: { limit: 50 } });
      return res.data;
    },
  });

  const { data: complaintData } = useQuery({
    queryKey: ['qc-dash-complaints'],
    queryFn: async () => {
      const res = await apiClient.get('/compliance/complaints', { params: { limit: 20 } });
      return res.data;
    },
  });

  const { data: certData } = useQuery({
    queryKey: ['qc-dash-certs'],
    queryFn: async () => {
      const res = await apiClient.get('/trade-documents/certifications', {
        params: { expiring_days: 90, limit: 10 },
      });
      return res.data;
    },
  });

  const { data: batchData } = useQuery({
    queryKey: ['qc-dash-batches'],
    queryFn: async () => {
      const res = await apiClient.get('/batches', { params: { limit: 100 } });
      return res.data;
    },
  });

  const qcRecords    = qcData?.items ?? qcData ?? [];
  const inspections  = inspData?.items ?? inspData ?? [];
  const complaints   = complaintData?.items ?? complaintData ?? [];
  const certs        = certData?.items ?? certData ?? [];
  const batches      = batchData?.items ?? batchData ?? [];

  // 通過率計算
  const totalQC = Array.isArray(qcRecords) ? qcRecords.length : 0;
  const passedQC = (Array.isArray(qcRecords) ? qcRecords : []).filter((r: any) => r.result === 'pass' || r.is_passed).length;
  const passRate = totalQC > 0 ? Math.round((passedQC / totalQC) * 100) : 0;

  // 未解決客訴
  const openComplaints = (Array.isArray(complaints) ? complaints : []).filter((c: any) => c.status !== 'closed' && c.status !== 'resolved').length;

  // 即將到期認證
  const today = new Date().toISOString().split('T')[0];
  const expiringSoon = (Array.isArray(certs) ? certs : []).filter((c: any) => c.expiry_date && c.expiry_date <= new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0]);

  // 鮮度狀態
  const fresh = { ok: 0, warning: 0, critical: 0, expired: 0 };
  (Array.isArray(batches) ? batches : []).forEach((b: any) => {
    if (b.freshness_status === 'ok' || !b.freshness_status) fresh.ok++;
    else if (b.freshness_status === 'warning') fresh.warning++;
    else if (b.freshness_status === 'critical') fresh.critical++;
    else if (b.freshness_status === 'expired') fresh.expired++;
  });

  // QC 按月通過率趨勢
  const monthPass: Record<string, { pass: number; total: number }> = {};
  (Array.isArray(qcRecords) ? qcRecords : []).forEach((r: any) => {
    const mo = (r.check_date || r.created_at || '').slice(0, 7);
    if (!mo) return;
    if (!monthPass[mo]) monthPass[mo] = { pass: 0, total: 0 };
    monthPass[mo].total++;
    if (r.result === 'pass' || r.is_passed) monthPass[mo].pass++;
  });
  const passTrend = Object.entries(monthPass).sort().slice(-6).map(([m, v]) => ({
    month: m.slice(5),
    rate: v.total > 0 ? Math.round((v.pass / v.total) * 100) : 0,
  }));

  // 檢驗結果分布
  const resultCount: Record<string, number> = {};
  (Array.isArray(inspections) ? inspections : []).forEach((r: any) => {
    const k = r.overall_result || r.result || 'unknown';
    resultCount[k] = (resultCount[k] || 0) + 1;
  });

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <ShieldCheck className="text-teal-600" size={24} />
          {t('title')}
        </h1>
        <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
      </div>

      {/* 核心指標 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <QualCard icon={<CheckCircle size={20} />} color="green"  label={t('passRate')} value={`${passRate}%`} sub={`${passedQC}/${totalQC}`} good={passRate >= 90} />
        <QualCard icon={<ThumbsDown size={20} />}  color={openComplaints > 0 ? 'red' : 'gray'} label={t('openComplaints')} value={openComplaints} sub={t('cases')} alert={openComplaints > 0} />
        <QualCard icon={<FileText size={20} />}    color={expiringSoon.length > 0 ? 'orange' : 'green'} label={t('expiringCerts')} value={expiringSoon.length} sub={t('within30Days')} alert={expiringSoon.length > 0} />
        <QualCard icon={<AlertTriangle size={20} />} color={fresh.critical + fresh.expired > 0 ? 'red' : fresh.warning > 0 ? 'orange' : 'green'} label={t('freshnessAlert')} value={fresh.critical + fresh.expired + fresh.warning} sub={t('batchUnit')} alert={fresh.critical + fresh.expired > 0} />
      </div>

      {/* QC 通過率趨勢 + 鮮度分布 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('monthlyTrend')}</h2>
          {passTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={passTrend}>
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: any) => [`${v}%`, t('tooltipPassRate')]} />
                <Line type="monotone" dataKey="rate" stroke="#14b8a6" strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-300 text-sm">{t('noTrendData')}</div>
          )}
        </div>

        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('freshnessDistribution')}</h2>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <FreshBox label={t('fresh.ok')}       count={fresh.ok}       color="green" />
            <FreshBox label={t('fresh.warning')}  count={fresh.warning}  color="yellow" />
            <FreshBox label={t('fresh.critical')} count={fresh.critical} color="orange" />
            <FreshBox label={t('fresh.expired')}  count={fresh.expired}  color="red" urgent={fresh.expired > 0} />
          </div>
          {Object.keys(resultCount).length > 0 && (
            <div className="border-t pt-3">
              <p className="text-xs text-gray-400 mb-2">{t('resultDistribution')}</p>
              <div className="space-y-1">
                {Object.entries(resultCount).map(([r, c]) => (
                  <div key={r} className="flex items-center gap-2 text-xs">
                    <span className="text-gray-500 w-20 flex-shrink-0">{r}</span>
                    <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full bg-teal-500" style={{ width: `${Math.min(100, (c / (Array.isArray(inspections) ? inspections.length : 1)) * 100)}%` }} />
                    </div>
                    <span className="text-gray-700 font-bold w-6">{c}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 認證到期 + 客訴列表 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('certReminder')}</h2>
          {expiringSoon.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle size={28} className="text-green-400 mx-auto mb-2" />
              <p className="text-sm text-gray-400">{t('noCertsExpiring')}</p>
            </div>
          ) : (
            <div className="space-y-2">
              {expiringSoon.slice(0, 5).map((c: any, i: number) => {
                const days = Math.ceil((new Date(c.expiry_date).getTime() - Date.now()) / 86400000);
                return (
                  <div key={i} className={clsx('flex items-center justify-between p-3 rounded-lg border',
                    days <= 30 ? 'border-red-200 bg-red-50' : 'border-yellow-100 bg-yellow-50'
                  )}>
                    <div>
                      <p className="text-sm font-medium text-gray-800">{c.certification_type}</p>
                      <p className="text-xs text-gray-500">{c.certified_entity_name || c.issuing_body}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-gray-800">{c.expiry_date}</p>
                      <p className={clsx('text-xs font-medium', days <= 30 ? 'text-red-600' : 'text-yellow-600')}>
                        {t('daysLeft', { days })}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('complaintsStatus')}</h2>
          {(Array.isArray(complaints) ? complaints : []).length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle size={28} className="text-green-400 mx-auto mb-2" />
              <p className="text-sm text-gray-400">{t('noComplaints')}</p>
            </div>
          ) : (
            <div className="space-y-2">
              {(Array.isArray(complaints) ? complaints : []).slice(0, 5).map((c: any) => (
                <div key={c.id} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-800 truncate max-w-[200px]">{c.complaint_title || c.title || c.complaint_no}</p>
                    <p className="text-xs text-gray-400">{c.customer_name || '—'} · {c.created_at?.split('T')[0]}</p>
                  </div>
                  <span className={clsx('px-2 py-0.5 rounded text-xs font-medium',
                    c.status === 'open' ? 'bg-red-100 text-red-700' :
                    c.status === 'in_progress' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-green-100 text-green-700'
                  )}>
                    {t(`status.${c.status}` as any) || c.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function QualCard({ icon, color, label, value, sub, good, alert }: {
  icon: React.ReactNode; color: string; label: string; value: any; sub: string; good?: boolean; alert?: boolean;
}) {
  const colors: Record<string, string> = {
    green: 'bg-green-50 text-green-600', red: 'bg-red-50 text-red-600',
    orange: 'bg-orange-50 text-orange-600', gray: 'bg-gray-50 text-gray-400',
  };
  return (
    <div className={`bg-white rounded-xl border p-4 ${alert ? 'border-red-200' : ''}`}>
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center mb-3 ${colors[color] || 'bg-gray-50 text-gray-400'}`}>{icon}</div>
      <p className="text-2xl font-bold text-gray-900">{value}<span className="text-sm font-normal text-gray-400 ml-1">{sub}</span></p>
      <p className="text-xs font-medium text-gray-600 mt-0.5">{label}</p>
    </div>
  );
}

function FreshBox({ label, count, color, urgent }: { label: string; count: number; color: string; urgent?: boolean }) {
  const colors: Record<string, string> = {
    green: 'bg-green-100 text-green-700', yellow: 'bg-yellow-100 text-yellow-700',
    orange: 'bg-orange-100 text-orange-700', red: 'bg-red-100 text-red-700',
  };
  return (
    <div className={clsx('text-center py-3 rounded-lg', colors[color], urgent && 'ring-1 ring-red-400')}>
      <p className="text-2xl font-bold">{count}</p>
      <p className="text-xs opacity-70">{label}</p>
    </div>
  );
}
