/**
 * Metrics Dashboard Component for KS-LOS Phase 2
 * 
 * Main dashboard component displaying both Tier B (Business) and Tier A (Technical AI)
 * metrics. Provides tabbed navigation between different metric views with proper
 * authentication handling for admin-only content.
 * 
 * Features:
 * - Tabbed interface (Application, Portfolio, AI Quality)
 * - Real-time data refresh
 * - Admin authentication for Tier A metrics
 * - Responsive design
 * - Error handling and loading states
 * 
 * Usage:
 * ```tsx
 * <MetricsDashboard applicationId="APP-123" isAdmin={true} />
 * ```
 */

import React, { useState, useEffect, useCallback } from 'react';
import type {
  ApplicationMetrics,
  PortfolioMetrics,
  JourneyStageMetrics,
  AIMetrics,
  AggregateAIMetrics,
  ApplicationStatus as ApplicationStatusType,
  GradeLevel as GradeLevelType,
} from '../types/metrics';
import { ApplicationStatus, GradeLevel } from '../types/metrics';
import { getMetricsClient } from '../api/metricsClient';

// ─────────────────────────────────────────────────────────────────────────────
// Component Props
// ─────────────────────────────────────────────────────────────────────────────

interface MetricsDashboardProps {
  applicationId?: string;
  conversationId?: string;
  isAdmin?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab Types
// ─────────────────────────────────────────────────────────────────────────────

type TabType = 'application' | 'portfolio' | 'ai';

// ─────────────────────────────────────────────────────────────────────────────
// Component State
// ─────────────────────────────────────────────────────────────────────────────

interface DashboardState {
  // Data
  applicationMetrics: ApplicationMetrics | null;
  portfolioMetrics: PortfolioMetrics | null;
  journeyMetrics: JourneyStageMetrics[] | null;
  aiMetrics: AIMetrics | null;
  aggregateAIMetrics: AggregateAIMetrics | null;
  
  // UI State
  activeTab: TabType;
  isLoading: boolean;
  error: string | null;
  adminAuthenticated: boolean;
  adminPassword: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Metrics Dashboard Component
// ─────────────────────────────────────────────────────────────────────────────

export const MetricsDashboard: React.FC<MetricsDashboardProps> = ({
  applicationId,
  conversationId,
  isAdmin = false,
  autoRefresh = true,
  refreshInterval = 300000, // 5 minutes
}) => {
  // State
  const [state, setState] = useState<DashboardState>({
    applicationMetrics: null,
    portfolioMetrics: null,
    journeyMetrics: null,
    aiMetrics: null,
    aggregateAIMetrics: null,
    activeTab: 'application',
    isLoading: false,
    error: null,
    adminAuthenticated: false,
    adminPassword: '',
  });

  const metricsClient = getMetricsClient({ debug: false });
  const effectiveConversationId = conversationId || applicationId;

  // Keep UI auth state in sync with the singleton client (so auth done on /metrics
  // also enables AI metrics when the dashboard is embedded elsewhere).
  useEffect(() => {
    if (metricsClient.isAuthenticated() && !state.adminAuthenticated) {
      setState((prev) => ({ ...prev, adminAuthenticated: true }));
    }
  }, [metricsClient, state.adminAuthenticated]);

  // ───────────────────────────────────────────────────────────────────────────
  // Data Fetching Methods
  // ───────────────────────────────────────────────────────────────────────────

  const fetchApplicationMetrics = useCallback(async () => {
    if (!applicationId) return;

    try {
      const data = await metricsClient.getApplicationMetrics(applicationId);
      setState((prev) => ({ ...prev, applicationMetrics: data }));
    } catch (error) {
      console.error('Failed to fetch application metrics:', error);
    }
  }, [applicationId, metricsClient]);

  const fetchPortfolioMetrics = useCallback(async () => {
    try {
      const data = await metricsClient.getPortfolioMetrics({ period: 'today' });
      setState((prev) => ({ ...prev, portfolioMetrics: data }));
    } catch (error) {
      console.error('Failed to fetch portfolio metrics:', error);
    }
  }, [metricsClient]);

  const fetchJourneyMetrics = useCallback(async () => {
    try {
      const data = await metricsClient.getJourneyMetrics();
      setState((prev) => ({ ...prev, journeyMetrics: data }));
    } catch (error) {
      console.error('Failed to fetch journey metrics:', error);
    }
  }, [metricsClient]);

  const fetchAIMetrics = useCallback(async () => {
    if (!effectiveConversationId) return;

    try {
      const data = await metricsClient.getAIMetrics(effectiveConversationId);
      setState((prev) => ({ ...prev, aiMetrics: data }));
    } catch (error) {
      console.error('Failed to fetch AI metrics:', error);
    }
  }, [effectiveConversationId, metricsClient]);

  const fetchAggregateAIMetrics = useCallback(async () => {
    try {
      const data = await metricsClient.getAggregateAIMetrics({ period: 'today' });
      setState((prev) => ({ ...prev, aggregateAIMetrics: data }));
    } catch (error) {
      console.error('Failed to fetch aggregate AI metrics:', error);
    }
  }, [metricsClient]);

  // ───────────────────────────────────────────────────────────────────────────
  // Authentication Methods
  // ───────────────────────────────────────────────────────────────────────────

  const handleAdminAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      await metricsClient.authenticateAdmin(state.adminPassword);
      setState((prev) => ({
        ...prev,
        adminAuthenticated: true,
        adminPassword: '',
        error: null,
      }));
      
      // Fetch AI metrics after authentication
      await fetchAIMetrics();
      await fetchAggregateAIMetrics();
    } catch {
      setState((prev) => ({
        ...prev,
        error: 'Invalid admin password',
      }));
    }
  };

  // ───────────────────────────────────────────────────────────────────────────
  // Effects
  // ───────────────────────────────────────────────────────────────────────────

  // Initial data fetch
  useEffect(() => {
    const fetchData = async () => {
      setState((prev) => ({ ...prev, isLoading: true }));

      try {
        await Promise.all([
          fetchApplicationMetrics(),
          fetchPortfolioMetrics(),
          fetchJourneyMetrics(),
        ]);

        // Fetch AI metrics if already authenticated
        if (state.adminAuthenticated) {
          await fetchAIMetrics();
          await fetchAggregateAIMetrics();
        }
      } catch {
        setState((prev) => ({
          ...prev,
          error: 'Failed to load metrics',
        }));
      } finally {
        setState((prev) => ({ ...prev, isLoading: false }));
      }
    };

    fetchData();
  }, [
    applicationId,
    state.adminAuthenticated,
    fetchApplicationMetrics,
    fetchPortfolioMetrics,
    fetchJourneyMetrics,
    fetchAIMetrics,
    fetchAggregateAIMetrics,
  ]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchApplicationMetrics();
      fetchPortfolioMetrics();
      fetchJourneyMetrics();

      if (state.adminAuthenticated) {
        fetchAIMetrics();
        fetchAggregateAIMetrics();
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [
    autoRefresh,
    refreshInterval,
    state.adminAuthenticated,
    fetchApplicationMetrics,
    fetchPortfolioMetrics,
    fetchJourneyMetrics,
    fetchAIMetrics,
    fetchAggregateAIMetrics,
  ]);

  // ───────────────────────────────────────────────────────────────────────────
  // Render Helpers
  // ───────────────────────────────────────────────────────────────────────────

  const getStatusColor = (status: ApplicationStatusType): string => {
    switch (status) {
      case ApplicationStatus.APPROVED:
      case ApplicationStatus.DISBURSED:
        return 'text-green-600 bg-green-100';
      case ApplicationStatus.REJECTED:
        return 'text-red-600 bg-red-100';
      case ApplicationStatus.PROCESSING:
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getGradeColor = (grade: GradeLevelType | null): string => {
    switch (grade) {
      case GradeLevel.A:
        return 'text-green-600';
      case GradeLevel.B:
        return 'text-blue-600';
      case GradeLevel.C:
        return 'text-yellow-600';
      case GradeLevel.D:
        return 'text-orange-600';
      case GradeLevel.E:
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // ───────────────────────────────────────────────────────────────────────────
  // Render Methods
  // ───────────────────────────────────────────────────────────────────────────

  const renderApplicationTab = () => {
    if (!state.applicationMetrics) {
      return <div className="text-center py-8 text-gray-500">Loading...</div>;
    }

    const metrics = state.applicationMetrics;

    return (
      <div className="space-y-6">
        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
            <h3 className="text-sm font-medium text-gray-500">Status</h3>
            <p className={`mt-2 text-lg font-semibold ${getStatusColor(metrics.status)}`}>
              {metrics.status.replace('_', ' ').toUpperCase()}
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
            <h3 className="text-sm font-medium text-gray-500">Processing Time</h3>
            <p className="mt-2 text-lg font-semibold text-gray-900">
              {metrics.processing_time_seconds.toFixed(1)}s
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
            <h3 className="text-sm font-medium text-gray-500">Loan Amount</h3>
            <p className="mt-2 text-lg font-semibold text-gray-900">
              {formatCurrency(metrics.loan_amount)}
            </p>
          </div>
        </div>

        {/* Credit Metrics */}
        <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Credit Metrics</h3>
          <div className="space-y-4">
            {metrics.bureau_score && (
              <div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">Bureau Score</span>
                  <span className={`text-sm font-medium ${getGradeColor(metrics.bureau_grade)}`}>
                    {metrics.bureau_score} ({metrics.bureau_grade})
                  </span>
                </div>
                <div className="mt-2 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${(metrics.bureau_score / 900) * 100}%` }}
                  />
                </div>
              </div>
            )}

            {metrics.foir_ratio !== null && (
              <div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">FOIR Ratio</span>
                  <span className="text-sm font-medium text-gray-900">
                    {metrics.foir_ratio.toFixed(1)}%
                  </span>
                </div>
                <div className="mt-2 bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      metrics.foir_ratio < 40 ? 'bg-green-600' :
                      metrics.foir_ratio < 55 ? 'bg-yellow-600' : 'bg-red-600'
                    }`}
                    style={{ width: `${Math.min(metrics.foir_ratio, 100)}%` }}
                  />
                </div>
              </div>
            )}

            {metrics.ltv_ratio !== null && (
              <div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">LTV Ratio</span>
                  <span className="text-sm font-medium text-gray-900">
                    {metrics.ltv_ratio.toFixed(1)}%
                  </span>
                </div>
                <div className="mt-2 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-purple-600 h-2 rounded-full"
                    style={{ width: `${Math.min(metrics.ltv_ratio, 100)}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Journey Progress */}
        <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Journey Progress</h3>
          <div className="mb-4">
            <div className="flex justify-between mb-2">
              <span className="text-sm text-gray-500">Overall Progress</span>
              <span className="text-sm font-medium text-gray-900">
                {metrics.journey_progress.toFixed(0)}%
              </span>
            </div>
            <div className="bg-gray-200 rounded-full h-3">
              <div
                className="bg-blue-600 h-3 rounded-full transition-all duration-500"
                style={{ width: `${metrics.journey_progress}%` }}
              />
            </div>
          </div>

          {/* Stage Stepper */}
          <div className="flex items-center justify-between">
            {['advisory', 'application', 'stp', 'approval', 'disbursement'].map((stage, index) => {
              const isCompleted = metrics.journey_stages.includes(stage);
              const isCurrent = metrics.current_stage === stage;

              return (
                <div key={stage} className="flex flex-col items-center">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                      isCompleted
                        ? 'bg-green-600 text-white'
                        : isCurrent
                        ? 'bg-blue-600 text-white animate-pulse'
                        : 'bg-gray-200 text-gray-500'
                    }`}
                  >
                    {isCompleted ? '✓' : index + 1}
                  </div>
                  <span className="mt-1 text-xs text-gray-500 capitalize">
                    {stage.replace('_', ' ')}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Decision Reason */}
        {metrics.decision_reason && (
          <div className="bg-blue-50 p-4 rounded-lg">
            <p className="text-sm text-blue-800">
              <span className="font-medium">Decision:</span> {metrics.decision_reason}
            </p>
          </div>
        )}
      </div>
    );
  };

  const renderPortfolioTab = () => {
    if (!state.portfolioMetrics) {
      return <div className="text-center py-8 text-gray-500">Loading...</div>;
    }

    const metrics = state.portfolioMetrics;

    return (
      <div className="space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
            <h3 className="text-sm font-medium text-gray-500">Total Applications</h3>
            <p className="mt-2 text-2xl font-bold text-gray-900">{metrics.total_applications}</p>
          </div>

          <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
            <h3 className="text-sm font-medium text-gray-500">Approval Rate</h3>
            <p className="mt-2 text-2xl font-bold text-green-600">
              {metrics.approval_rate.toFixed(1)}%
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
            <h3 className="text-sm font-medium text-gray-500">Avg Processing Time</h3>
            <p className="mt-2 text-2xl font-bold text-gray-900">
              {metrics.average_processing_time.toFixed(1)}s
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
            <h3 className="text-sm font-medium text-gray-500">Avg Loan Amount</h3>
            <p className="mt-2 text-2xl font-bold text-gray-900">
              {formatCurrency(metrics.average_loan_amount)}
            </p>
          </div>
        </div>

        {/* Rejection Breakdown */}
        {Object.keys(metrics.rejection_reasons).length > 0 && (
          <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Rejection Breakdown</h3>
            <div className="space-y-2">
              {Object.entries(metrics.rejection_reasons).map(([reason, count]) => (
                <div key={reason} className="flex justify-between items-center">
                  <span className="text-sm text-gray-600 capitalize">
                    {reason.replace(/_/g, ' ')}
                  </span>
                  <span className="text-sm font-medium text-gray-900">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Risk Distribution */}
        <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Risk Distribution</h3>
          <div className="space-y-2">
            {Object.entries(metrics.risk_distribution).map(([risk, count]) => (
              <div key={risk} className="flex items-center">
                <span className="w-20 text-sm text-gray-600 capitalize">{risk}</span>
                <div className="flex-1 bg-gray-200 rounded-full h-2 ml-2">
                  <div
                    className={`h-2 rounded-full ${
                      risk === 'low' ? 'bg-green-600' :
                      risk === 'moderate' ? 'bg-blue-600' :
                      risk === 'elevated' ? 'bg-yellow-600' : 'bg-red-600'
                    }`}
                    style={{
                      width: `${(count / metrics.total_applications) * 100}%`,
                    }}
                  />
                </div>
                <span className="ml-2 text-sm font-medium text-gray-900">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderAITab = () => {
    if (!state.adminAuthenticated) {
      return (
        <div className="text-center py-8">
          <div className="max-w-md mx-auto">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              🔒 Admin Access Required
            </h3>
            <p className="text-gray-600 mb-4">
              AI quality metrics are restricted to administrators only.
            </p>
            <form onSubmit={handleAdminAuth} className="space-y-4">
              <input
                type="password"
                placeholder="Enter admin password"
                value={state.adminPassword}
                onChange={(e) =>
                  setState((prev) => ({ ...prev, adminPassword: e.target.value }))
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {state.error && (
                <p className="text-red-600 text-sm">{state.error}</p>
              )}
              <button
                type="submit"
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors"
              >
                Authenticate
              </button>
            </form>
          </div>
        </div>
      );
    }

    if (!state.aggregateAIMetrics) {
      return <div className="text-center py-8 text-gray-500">Loading...</div>;
    }

    const metrics = state.aggregateAIMetrics;

    return (
      <div className="space-y-6">
        {/* Quality Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
            <h3 className="text-sm font-medium text-gray-500">Hallucination Rate</h3>
            <p className={`mt-2 text-2xl font-bold ${
              metrics.average_hallucination_rate < 0.05 ? 'text-green-600' :
              metrics.average_hallucination_rate < 0.1 ? 'text-yellow-600' : 'text-red-600'
            }`}>
              {(metrics.average_hallucination_rate * 100).toFixed(1)}%
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
            <h3 className="text-sm font-medium text-gray-500">RAGAS Overall</h3>
            <p className="mt-2 text-2xl font-bold text-blue-600">
              {metrics.average_ragas_overall
                ? (metrics.average_ragas_overall * 100).toFixed(1)
                : 'N/A'}%
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
            <h3 className="text-sm font-medium text-gray-500">Avg Latency (p95)</h3>
            <p className="mt-2 text-2xl font-bold text-gray-900">
              {(metrics.average_latency_p95 / 1000).toFixed(2)}s
            </p>
          </div>
        </div>

        {/* Model Distribution */}
        <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Model Distribution</h3>
          <div className="space-y-2">
            {Object.entries(metrics.model_distribution).map(([model, percentage]) => (
              <div key={model} className="flex items-center">
                <span className="w-32 text-sm text-gray-600">{model}</span>
                <div className="flex-1 bg-gray-200 rounded-full h-2 ml-2">
                  <div
                    className="bg-indigo-600 h-2 rounded-full"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <span className="ml-2 text-sm font-medium text-gray-900">
                  {percentage.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Cost Summary */}
        <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] backdrop-blur-xl shadow-sm shadow-black/[0.04] dark:shadow-black/40 p-4">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Cost Summary</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Total Cost</p>
              <p className="text-lg font-semibold text-gray-900">
                {formatCurrency(metrics.total_cost_usd)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Cost per Conversation</p>
              <p className="text-lg font-semibold text-gray-900">
                {formatCurrency(metrics.cost_per_conversation)}
              </p>
            </div>
          </div>
        </div>

        {/* Quality Alerts */}
        {(metrics.low_quality_conversations > 0 ||
          metrics.high_hallucination_conversations > 0) && (
          <div className="bg-yellow-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-yellow-800 mb-2">Quality Alerts</h3>
            <ul className="space-y-1">
              {metrics.low_quality_conversations > 0 && (
                <li className="text-sm text-yellow-700">
                  • {metrics.low_quality_conversations} conversations with low RAGAS scores
                </li>
              )}
              {metrics.high_hallucination_conversations > 0 && (
                <li className="text-sm text-yellow-700">
                  • {metrics.high_hallucination_conversations} conversations with high hallucination rates
                </li>
              )}
            </ul>
          </div>
        )}
      </div>
    );
  };

  // ───────────────────────────────────────────────────────────────────────────
  // Main Render
  // ───────────────────────────────────────────────────────────────────────────

  return (
    <div className="metrics-dashboard rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 overflow-hidden">
      {/* Tab Navigation */}
      <div className="bg-white/70 dark:bg-white/[0.03] border-b border-slate-200/60 dark:border-white/[0.06]">
        <nav className="flex gap-2 px-4 md:px-6 py-2 overflow-x-auto scrollbar-hide" aria-label="Tabs">
          <button
            onClick={() => setState((prev) => ({ ...prev, activeTab: 'application' }))}
            className={`shrink-0 rounded-2xl px-3 py-2 text-xs font-semibold border transition-colors ${
              state.activeTab === 'application'
                ? 'bg-blue-50 dark:bg-blue-500/10 border-blue-200/70 dark:border-blue-500/20 text-blue-800 dark:text-blue-200'
                : 'bg-white/70 dark:bg-white/[0.04] border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 hover:bg-white/90 dark:hover:bg-white/[0.06]'
            }`}
          >
            Your Application
          </button>
          <button
            onClick={() => setState((prev) => ({ ...prev, activeTab: 'portfolio' }))}
            className={`shrink-0 rounded-2xl px-3 py-2 text-xs font-semibold border transition-colors ${
              state.activeTab === 'portfolio'
                ? 'bg-blue-50 dark:bg-blue-500/10 border-blue-200/70 dark:border-blue-500/20 text-blue-800 dark:text-blue-200'
                : 'bg-white/70 dark:bg-white/[0.04] border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 hover:bg-white/90 dark:hover:bg-white/[0.06]'
            }`}
          >
            Portfolio Insights
          </button>
          {isAdmin && (
            <button
              onClick={() => setState((prev) => ({ ...prev, activeTab: 'ai' }))}
              className={`shrink-0 rounded-2xl px-3 py-2 text-xs font-semibold border transition-colors ${
                state.activeTab === 'ai'
                  ? 'bg-blue-50 dark:bg-blue-500/10 border-blue-200/70 dark:border-blue-500/20 text-blue-800 dark:text-blue-200'
                  : 'bg-white/70 dark:bg-white/[0.04] border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 hover:bg-white/90 dark:hover:bg-white/[0.06]'
              }`}
            >
              AI Quality 🔒
            </button>
          )}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="p-4 md:p-6">
        {state.isLoading && !state.applicationMetrics ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
            <p className="mt-4 text-slate-500 dark:text-slate-400">Loading metrics...</p>
          </div>
        ) : (
          <>
            {state.activeTab === 'application' && renderApplicationTab()}
            {state.activeTab === 'portfolio' && renderPortfolioTab()}
            {state.activeTab === 'ai' && renderAITab()}
          </>
        )}
      </div>
    </div>
  );
};

export default MetricsDashboard;
