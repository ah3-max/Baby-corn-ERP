'use client';

/**
 * QC 品質中心 — 儀表板頁面
 * 顯示：QC 趨勢、供應商品質排名、缺陷頻率、最近檢驗列表
 */
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { ClipboardCheck, TrendingUp, AlertTriangle, Award, Plus, X } from 'lucide-react';
import { qcEnhancedApi, batchesApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';

export default function QCCenterPage() {
  const t  = useTranslations('qcCenter');
  const tc = useTranslations('common');
  const { showToast } = useToast();
  const [showCreate, setShowCreate] = useState(false);
  const [trend, setTrend] = useState<any>(null);
  const [supplierQuality, setSupplierQuality] = useState<any[]>([]);
  const [defects, setDefects] = useState<any>(null);
  const [inspections, setInspections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [trendRes, sqRes, defectRes, inspRes] = await Promise.all([
          qcEnhancedApi.analyticsTrend({}),
          qcEnhancedApi.analyticsSupplierQuality(),
          qcEnhancedApi.analyticsDefectFrequency({}),
          qcEnhancedApi.listInspections({}),
        ]);
        setTrend(trendRes.data);
        setSupplierQuality(sqRes.data);
        setDefects(defectRes.data);
        setInspections(inspRes.data.slice(0, 10));
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return <div className="text-center py-16 text-gray-400">{tc('loading')}</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> {t('addInspection')}
        </button>
      </div>

      {/* KPI 卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <ClipboardCheck size={20} className="text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">{t('totalInspections')}</p>
              <p className="text-xl font-bold text-gray-800">{trend?.total_inspections || 0}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <TrendingUp size={20} className="text-green-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">{t('avgScore')}</p>
              <p className="text-xl font-bold text-gray-800">{trend?.avg_score || 0}</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
              <Award size={20} className="text-emerald-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">{t('passRate')}</p>
              <p className="text-xl font-bold text-gray-800">{trend?.pass_rate_pct || 0}%</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              <AlertTriangle size={20} className="text-red-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">{t('defectTypes')}</p>
              <p className="text-xl font-bold text-gray-800">{defects ? Object.keys(defects.defects || {}).length : 0}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 等級分佈 */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-4">{t('gradeDistribution')}</h3>
          {trend?.grade_distribution && Object.keys(trend.grade_distribution).length > 0 ? (
            <div className="space-y-2">
              {Object.entries(trend.grade_distribution).map(([grade, count]: [string, any]) => (
                <div key={grade} className="flex items-center gap-3">
                  <span className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold ${
                    grade === 'A' ? 'bg-green-100 text-green-700' :
                    grade === 'B' ? 'bg-blue-100 text-blue-700' :
                    grade === 'C' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-red-100 text-red-700'
                  }`}>{grade}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-4">
                    <div className={`h-4 rounded-full ${
                      grade === 'A' ? 'bg-green-500' :
                      grade === 'B' ? 'bg-blue-500' :
                      grade === 'C' ? 'bg-yellow-500' : 'bg-red-500'
                    }`} style={{ width: `${Math.min(100, (count / Math.max(trend.total_inspections, 1)) * 100)}%` }} />
                  </div>
                  <span className="text-sm text-gray-600 w-8 text-right">{count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">{tc('noData')}</p>
          )}
        </div>

        {/* 供應商品質排名 */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-4">{t('supplierRanking')}</h3>
          {supplierQuality.length > 0 ? (
            <div className="space-y-2">
              {supplierQuality.map((sq: any, idx: number) => (
                <div key={sq.supplier_id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-600">{idx + 1}</span>
                    <span className="text-sm font-medium text-gray-700">{sq.supplier_name}</span>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-gray-500">{sq.inspection_count} {t('times')}</span>
                    <span className="font-semibold text-gray-800">{sq.avg_score || '-'} {t('scoreUnit')}</span>
                    <span className={`font-medium ${sq.pass_rate_pct >= 80 ? 'text-green-600' : sq.pass_rate_pct >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
                      {sq.pass_rate_pct}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">{tc('noData')}</p>
          )}
        </div>

        {/* 缺陷頻率 */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-4">{t('defectFrequency')}</h3>
          {defects?.defects && Object.keys(defects.defects).length > 0 ? (
            <div className="space-y-2">
              {Object.entries(defects.defects).slice(0, 10).map(([defect, count]: [string, any]) => (
                <div key={defect} className="flex items-center justify-between py-1.5">
                  <span className="text-sm text-gray-700">{defect}</span>
                  <span className="text-sm font-semibold text-red-600">{count} {t('times')}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">{t('noDefects')}</p>
          )}
        </div>

        {/* 最近檢驗 */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-4">{t('recentInspections')}</h3>
          {inspections.length > 0 ? (
            <div className="space-y-2">
              {inspections.map((insp: any) => (
                <div key={insp.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div>
                    <span className="text-sm font-mono text-gray-600">{insp.inspection_no}</span>
                    <span className="text-xs text-gray-400 ml-2">
                      {t(`stages.${insp.inspection_stage}` as any) || insp.inspection_stage}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {insp.overall_score && <span className="text-xs text-gray-500">{insp.overall_score} {t('scoreUnit')}</span>}
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      insp.overall_result === 'pass' ? 'bg-green-100 text-green-700' :
                      insp.overall_result === 'fail' ? 'bg-red-100 text-red-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>{t(`results.${insp.overall_result}` as any) || insp.overall_result}</span>
                    {insp.overall_grade && (
                      <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-gray-100 text-gray-600">{insp.overall_grade}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">{t('noInspections')}</p>
          )}
        </div>
      </div>

      {/* 新增檢驗 Modal */}
      {showCreate && <CreateInspectionModal onClose={(ok) => { setShowCreate(false); if (ok) location.reload(); }} />}
    </div>
  );
}

function CreateInspectionModal({ onClose }: { onClose: (refresh?: boolean) => void }) {
  const t  = useTranslations('qcCenter');
  const tc = useTranslations('common');
  const [batches, setBatches] = useState<any[]>([]);
  const [form, setForm] = useState({
    batch_id: '', inspection_stage: 'factory_incoming', inspector_name: '',
    overall_result: 'pass', overall_grade: 'A', overall_score: '',
    recommendation: '', environment_temp_c: '',
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    batchesApi.list({}).then(r => setBatches(r.data)).catch(console.error);
  }, []);

  const submit = async () => {
    if (!form.batch_id || !form.inspector_name) return;
    setSaving(true);
    try {
      await qcEnhancedApi.createInspection({
        ...form,
        overall_score: form.overall_score ? Number(form.overall_score) : null,
        environment_temp_c: form.environment_temp_c ? Number(form.environment_temp_c) : null,
      });
      onClose(true);
    } catch (e) { console.error(e); }
    finally { setSaving(false); }
  };

  const STAGES = [
    'factory_incoming',
    'factory_processing',
    'pre_packing',
    'pre_export',
    'tw_arrival',
    'tw_pre_delivery',
  ];

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-gray-800 text-lg">{t('createInspectionTitle')}</h3>
          <button onClick={() => onClose()}><X size={18} className="text-gray-400" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('batchLabel')} *</label>
            <select value={form.batch_id} onChange={e => setForm({...form, batch_id: e.target.value})} className="input w-full">
              <option value="">{t('selectBatch')}</option>
              {batches.map((b: any) => <option key={b.id} value={b.id}>{b.batch_no} ({b.status})</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('inspectionStage')}</label>
            <select value={form.inspection_stage} onChange={e => setForm({...form, inspection_stage: e.target.value})} className="input w-full">
              {STAGES.map(s => (
                <option key={s} value={s}>{t(`stages.${s}` as any)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('inspectorLabel')} *</label>
            <input value={form.inspector_name} onChange={e => setForm({...form, inspector_name: e.target.value})} className="input w-full" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('resultLabel')}</label>
              <select value={form.overall_result} onChange={e => setForm({...form, overall_result: e.target.value})} className="input w-full">
                <option value="pass">{t('results.pass')}</option>
                <option value="conditional_pass">{t('results.conditional_pass')}</option>
                <option value="fail">{t('results.fail')}</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('gradeLabel')}</label>
              <select value={form.overall_grade} onChange={e => setForm({...form, overall_grade: e.target.value})} className="input w-full">
                {['A','B','C','D','reject'].map(g => <option key={g} value={g}>{g}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('overallScore')}</label>
              <input type="number" min="0" max="100" value={form.overall_score} onChange={e => setForm({...form, overall_score: e.target.value})} className="input w-full" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('envTemp')}</label>
              <input type="number" step="0.1" value={form.environment_temp_c} onChange={e => setForm({...form, environment_temp_c: e.target.value})} className="input w-full" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('recommendation')}</label>
            <textarea value={form.recommendation} onChange={e => setForm({...form, recommendation: e.target.value})} className="input w-full h-16 resize-none" />
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button onClick={() => onClose()} className="btn-secondary flex-1">{tc('cancel')}</button>
          <button onClick={submit} disabled={saving || !form.batch_id || !form.inspector_name} className="btn-primary flex-1">
            {saving ? tc('loading') : t('createBtn')}
          </button>
        </div>
      </div>
    </div>
  );
}
