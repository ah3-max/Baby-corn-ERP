'use client';

/**
 * P-05 商機管理頁面（看板 + 列表視圖）
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { apiClient } from '@/lib/api';
import { Target, Plus, DollarSign, Calendar } from 'lucide-react';
import { clsx } from 'clsx';

type StageId = 'lead' | 'qualified' | 'proposal' | 'negotiation' | 'won' | 'lost';

const STAGE_COLORS: Record<StageId, string> = {
  lead:        'bg-gray-100 text-gray-700',
  qualified:   'bg-blue-100 text-blue-700',
  proposal:    'bg-purple-100 text-purple-700',
  negotiation: 'bg-yellow-100 text-yellow-700',
  won:         'bg-green-100 text-green-700',
  lost:        'bg-red-100 text-red-700',
};

export default function OpportunitiesPage() {
  const t  = useTranslations('crmOpportunities');
  const tc = useTranslations('common');
  const [view, setView] = useState<'kanban' | 'list'>('kanban');
  const [showForm, setShowForm] = useState(false);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['crm-opportunities'],
    queryFn: async () => {
      const res = await apiClient.get('/crm/opportunities');
      return res.data;
    },
  });

  const opportunities = data?.items || [];

  const updateStage = useMutation({
    mutationFn: ({ id, stage }: { id: string; stage: string }) =>
      apiClient.patch(`/crm/opportunities/${id}`, { stage }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['crm-opportunities'] }),
  });

  const STAGE_IDS: StageId[] = ['lead', 'qualified', 'proposal', 'negotiation', 'won', 'lost'];

  const stageStats = STAGE_IDS.map(id => ({
    id,
    label: t(`stages.${id}`),
    color: STAGE_COLORS[id],
    count: opportunities.filter((o: any) => o.stage === id).length,
    amount: opportunities
      .filter((o: any) => o.stage === id)
      .reduce((sum: number, o: any) => sum + (o.expected_amount || 0), 0),
  }));

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Target className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border overflow-hidden text-sm">
            <button
              onClick={() => setView('kanban')}
              className={clsx('px-3 py-1.5', view === 'kanban' ? 'bg-primary-50 text-primary-700' : 'text-gray-500 hover:bg-gray-50')}
            >
              {t('viewKanban')}
            </button>
            <button
              onClick={() => setView('list')}
              className={clsx('px-3 py-1.5 border-l', view === 'list' ? 'bg-primary-50 text-primary-700' : 'text-gray-500 hover:bg-gray-50')}
            >
              {t('viewList')}
            </button>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700"
          >
            <Plus size={15} />
            {t('addOpportunity')}
          </button>
        </div>
      </div>

      {/* 概覽統計 */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border p-4">
          <p className="text-sm text-gray-500">{t('activeOpportunities')}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">
            {opportunities.filter((o: any) => !['won', 'lost'].includes(o.stage)).length}
          </p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-sm text-gray-500">{t('pipelineAmount')}</p>
          <p className="text-3xl font-bold text-primary-600 mt-1">
            {(opportunities
              .filter((o: any) => !['lost'].includes(o.stage))
              .reduce((s: number, o: any) => s + (o.expected_amount || 0), 0) / 1000
            ).toFixed(0)}K
          </p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-sm text-gray-500">{t('closedThisMonth')}</p>
          <p className="text-3xl font-bold text-green-600 mt-1">
            {opportunities.filter((o: any) => o.stage === 'won').length}
          </p>
        </div>
      </div>

      {/* 看板視圖 */}
      {view === 'kanban' && (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {stageStats.map(stage => (
            <div key={stage.id} className="flex-shrink-0 w-64 bg-gray-50 rounded-xl p-3">
              <div className="flex items-center justify-between mb-3">
                <span className={clsx('px-2 py-0.5 rounded text-xs font-medium', stage.color)}>
                  {stage.label}
                </span>
                <span className="text-xs text-gray-500">{stage.count} {t('countUnit')}</span>
              </div>
              {stage.amount > 0 && (
                <p className="text-xs text-gray-400 mb-2 flex items-center gap-1">
                  <DollarSign size={11} />
                  {(stage.amount / 1000).toFixed(0)}K TWD
                </p>
              )}
              <div className="space-y-2">
                {opportunities
                  .filter((o: any) => o.stage === stage.id)
                  .map((opp: any) => (
                    <div key={opp.id} className="bg-white rounded-lg border p-3 text-sm shadow-sm">
                      <p className="font-medium text-gray-900 truncate">{opp.opportunity_name}</p>
                      {opp.customer_name && (
                        <p className="text-xs text-gray-500 mt-0.5">{opp.customer_name}</p>
                      )}
                      <div className="flex items-center justify-between mt-2">
                        {opp.expected_amount && (
                          <span className="text-xs text-primary-600 font-medium">
                            {(opp.expected_amount / 1000).toFixed(0)}K
                          </span>
                        )}
                        {opp.expected_close_date && (
                          <span className="text-xs text-gray-400 flex items-center gap-1">
                            <Calendar size={10} />
                            {opp.expected_close_date}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 列表視圖 */}
      {view === 'list' && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-3 text-left">{t('col.name')}</th>
                <th className="px-4 py-3 text-left">{t('col.customer')}</th>
                <th className="px-4 py-3 text-left">{t('col.stage')}</th>
                <th className="px-4 py-3 text-right">{t('col.expectedAmount')}</th>
                <th className="px-4 py-3 text-right">{t('col.probability')}</th>
                <th className="px-4 py-3 text-left">{t('col.expectedCloseDate')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">{tc('loading')}</td></tr>
              ) : opportunities.map((opp: any) => {
                const stageId = opp.stage as StageId;
                return (
                  <tr key={opp.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{opp.opportunity_name}</td>
                    <td className="px-4 py-3 text-gray-600">{opp.customer_name || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={clsx('px-2 py-0.5 rounded text-xs font-medium', STAGE_COLORS[stageId])}>
                        {t(`stages.${stageId}` as any)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {opp.expected_amount ? `$${Number(opp.expected_amount).toLocaleString()}` : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary-500 rounded-full"
                            style={{ width: `${opp.probability_pct || 0}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-500">{opp.probability_pct || 0}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{opp.expected_close_date || '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
