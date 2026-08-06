'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiGet, apiPatch, apiPost, resolveSessionTenant } from '@/app/lib/api-client';

type Workflow = {
  id: number;
  name: string;
  status: string;
  trigger?: { trigger_type?: string };
  step_count?: number;
};

type ApprovalPolicy = {
  id: number;
  workflow_id: number;
  enabled: boolean;
  required_approvals: number;
  enforce_for_high_risk_only: boolean;
};

type ApprovalRequest = {
  id: number;
  workflow_id: number;
  contact_id: string;
  status: string;
  approved_by?: string[];
};

type Connector = {
  id: number;
  name: string;
  vendor: string;
  status: string;
  last_checked_at?: string | null;
  reliability_policy?: {
    max_retries?: number;
    base_backoff_ms?: number;
    slo_availability_target_pct?: number;
    slo_latency_p95_target_ms?: number;
    replay_enabled?: boolean;
  };
};

type ReplayQueueItem = {
  id: number;
  connector_id: number;
  operation_ref: string;
  status: string;
  failure_type: string;
  next_retry_at?: string | null;
};

type SlaAlert = {
  id: number;
  connector_id: number;
  type: string;
  status: string;
};

type ConnectorTemplate = {
  id: number;
  name: string;
};

type MaintenanceWindow = {
  id: number;
  name: string;
  start_hour_utc: number;
  end_hour_utc: number;
  enabled: boolean;
};

type EscalationRule = {
  id: number;
  name: string;
  min_breach_count: number;
};

type EscalationEvent = {
  id: number;
  connector_id: number;
  rule_name: string;
  status: string;
};

type Runbook = {
  id: number;
  name: string;
};

type RunbookAssignment = {
  id: number;
  runbook_id: number;
  operator: string;
  status: string;
};

type IncidentTimelineItem = {
  type: string;
  ref_id: number;
  status: string;
  occurred_at?: string;
};

type SliTrendPoint = {
  bucket_start: string;
  availability_pct: number;
  latency_p95_ms: number;
};

type Postmortem = {
  id: number;
  connector_id: number;
  title: string;
  status?: string;
};

type PostmortemTemplate = {
  id: number;
  name: string;
};

type PostmortemActionItem = {
  id: number;
  title: string;
  status: string;
};

type PostmortemClosureRequest = {
  id: number;
  status: string;
};

type ActionItemEscalation = {
  id: number;
  postmortem_id: number;
  action_item_id: number;
  status: string;
  tier?: string;
};

type ComplianceRollup = {
  week_start: string;
  postmortems_created: number;
  postmortems_closed: number;
  sla_compliance_pct: number;
};

type EscalationRoutingPolicy = {
  enabled: boolean;
  medium_threshold_hours: number;
  high_threshold_hours: number;
  critical_threshold_hours: number;
  in_window_channel: string;
  off_window_channel: string;
};

type EscalationCadencePolicy = {
  enabled: boolean;
  l2_after_minutes: number;
  l3_after_minutes: number;
  repage_interval_minutes: number;
  max_repages: number;
  suppression_ttl_minutes?: number;
  reopen_on_reoverdue?: boolean;
};

type EscalationAgingDashboard = {
  total_escalations: number;
  open_escalations: number;
  ack_slo_compliance_pct: number;
};

type BreachForecast = {
  at_risk_total: number;
  breached_count: number;
};

type EscalationPriorityQueue = {
  count: number;
  total_candidates: number;
};

type OwnerWorkloadDashboard = {
  total_owners: number;
  total_open_action_items: number;
  total_open_escalations: number;
};

type RebalanceSuggestions = {
  count: number;
};

type WorkloadHotspots = {
  count: number;
};

type SurgeAlerts = {
  count: number;
};

type BalanceIndex = {
  balance_index: number;
  overloaded_owner_count: number;
};

type CoverageGaps = {
  count: number;
  unassigned_open_items: number;
};

type HandoffReadiness = {
  count: number;
};

type ContinuityRisks = {
  count: number;
};

type OwnershipChurn = {
  count: number;
};

type StabilityScore = {
  stability_score: number;
  stability_band: string;
};

type HandoffPlan = {
  count: number;
};

type ResilienceSnapshot = {
  resilience_score: number;
  resilience_band: string;
};

type RemediationQueue = {
  count: number;
};

type ReadinessForecast = {
  readiness_forecast_score: number;
  forecast_band: string;
};

type RemediationThroughput = {
  required_daily_remediations: number;
  throughput_band: string;
};

type RiskBurndown = {
  risk_burndown_index: number;
  burndown_band: string;
};

type CapacityScenarios = {
  count: number;
};

type RemediationSla = {
  remediation_sla_score: number;
  sla_band: string;
};

type OwnerReliefPlan = {
  count: number;
};

type EscalationClearanceEta = {
  clearance_eta_days: number;
  eta_band: string;
};

type MitigationReadiness = {
  mitigation_readiness_score: number;
  readiness_band: string;
};

type OwnerCoverageForecast = {
  owner_coverage_score: number;
  coverage_band: string;
};

type HandoffPressure = {
  handoff_pressure_score: number;
  pressure_band: string;
};

type RemediationMomentum = {
  remediation_momentum_score: number;
  momentum_band: string;
};

type OwnershipStabilityForecast = {
  ownership_stability_score: number;
  stability_band: string;
};

type EscalationBurnRate = {
  target_daily_burn: number;
  burn_band: string;
};

type HandoffResilienceForecast = {
  handoff_resilience_score: number;
  resilience_band: string;
};

type BacklogClearanceConfidence = {
  backlog_clearance_confidence: number;
  confidence_band: string;
};

type RemediationVelocityForecast = {
  remediation_velocity_score: number;
  velocity_band: string;
};

type EscalationRecoveryReadiness = {
  escalation_recovery_score: number;
  recovery_band: string;
};

type ContinuityReadinessIndex = {
  continuity_readiness_index: number;
  continuity_band: string;
};

type EscalationDrainForecast = {
  required_daily_drain: number;
  drain_band: string;
};

type RemediationConfidenceForecast = {
  remediation_confidence_score: number;
  confidence_band: string;
};

type EscalationStabilizationIndex = {
  escalation_stabilization_index: number;
  stabilization_band: string;
};

type RemediationPostureScore = {
  remediation_posture_score: number;
  posture_band: string;
};

type EscalationRunwayForecast = {
  required_daily_runway_actions: number;
  runway_band: string;
};

type RemediationBalanceIndex = {
  remediation_balance_index: number;
  balance_band: string;
};

type EscalationPressureForecast = {
  required_daily_pressure_actions: number;
  pressure_band: string;
};

type RemediationConcentrationForecast = {
  remediation_concentration_score: number;
  concentration_band: string;
};

type EscalationContainmentIndex = {
  escalation_containment_index: number;
  containment_band: string;
};

type RemediationReadinessBalance = {
  remediation_readiness_balance: number;
  readiness_band: string;
};

type EscalationLoadSheddingForecast = {
  required_daily_load_shedding: number;
  shedding_band: string;
};

type RemediationPressureIndex = {
  remediation_pressure_index: number;
  pressure_band: string;
};

type EscalationReliefForecast = {
  required_daily_relief_actions: number;
  relief_band: string;
};

type RemediationRecoveryIndex = {
  remediation_recovery_index: number;
  recovery_band: string;
};

type EscalationRecoveryIndex = {
  required_daily_recovery_actions: number;
  recovery_band: string;
};

type RemediationResilienceForecast = {
  remediation_resilience_score: number;
  resilience_band: string;
};

type EscalationStabilityIndex = {
  escalation_stability_index: number;
  stability_band: string;
};

type RemediationDurabilityForecast = {
  remediation_durability_score: number;
  durability_band: string;
};

type EscalationDurabilityIndex = {
  escalation_durability_index: number;
  durability_band: string;
};

type RemediationStabilityForecast = {
  remediation_stability_score: number;
  stability_band: string;
};

type EscalationStabilityForecast = {
  escalation_stability_forecast: number;
  stability_band: string;
};

type RemediationConsistencyForecast = {
  remediation_consistency_score: number;
  consistency_band: string;
};

type EscalationConsistencyIndex = {
  escalation_consistency_index: number;
  consistency_band: string;
};

type RemediationAlignmentForecast = {
  remediation_alignment_score: number;
  alignment_band: string;
};

type EscalationAlignmentIndex = {
  escalation_alignment_index: number;
  alignment_band: string;
};

type RemediationClarityForecast = {
  remediation_clarity_score: number;
  clarity_band: string;
};

type EscalationClarityIndex = {
  escalation_clarity_index: number;
  clarity_band: string;
};

type RemediationComposureForecast = {
  remediation_composure_score: number;
  composure_band: string;
};

type EscalationComposureIndex = {
  escalation_composure_index: number;
  composure_band: string;
};

type RemediationFocusForecast = {
  remediation_focus_score: number;
  focus_band: string;
};

type EscalationFocusIndex = {
  escalation_focus_index: number;
  focus_band: string;
};

type RemediationAttentionForecast = {
  remediation_attention_score: number;
  attention_band: string;
};

type EscalationAttentionIndex = {
  escalation_attention_index: number;
  attention_band: string;
};

type RemediationCoordinationForecast = {
  remediation_coordination_score: number;
  coordination_band: string;
};

type EscalationCoordinationIndex = {
  escalation_coordination_index: number;
  coordination_band: string;
};

type RemediationOrchestrationForecast = {
  remediation_orchestration_score: number;
  orchestration_band: string;
};

type EscalationOrchestrationIndex = {
  escalation_orchestration_index: number;
  orchestration_band: string;
};

type RemediationSynchronizationForecast = {
  remediation_synchronization_score: number;
  synchronization_band: string;
};

type EscalationSynchronizationIndex = {
  escalation_synchronization_index: number;
  synchronization_band: string;
};

type RemediationHarmonyForecast = {
  remediation_harmony_score: number;
  harmony_band: string;
};

type EscalationHarmonyIndex = {
  escalation_harmony_index: number;
  harmony_band: string;
};

type RemediationRhythmForecast = {
  remediation_rhythm_score: number;
  rhythm_band: string;
};

type EscalationRhythmIndex = {
  escalation_rhythm_index: number;
  rhythm_band: string;
};

type RemediationTempoForecast = {
  remediation_tempo_score: number;
  tempo_band: string;
};

type EscalationTempoIndex = {
  escalation_tempo_index: number;
  tempo_band: string;
};

type RemediationCadenceForecast = {
  remediation_cadence_score: number;
  cadence_band: string;
};

type EscalationCadenceIndex = {
  escalation_cadence_index: number;
  cadence_band: string;
};

type RemediationSteadinessForecast = {
  remediation_steadiness_score: number;
  steadiness_band: string;
};

type EscalationSteadinessIndex = {
  escalation_steadiness_index: number;
  steadiness_band: string;
};

type JsonObject = Record<string, unknown>;

function safeArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

export default function WorkflowOrchestratorPage() {
  const [tenantId] = useState(() => resolveSessionTenant() || 'tenant-demo');
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [policies, setPolicies] = useState<ApprovalPolicy[]>([]);
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [replayQueue, setReplayQueue] = useState<ReplayQueueItem[]>([]);
  const [slaAlerts, setSlaAlerts] = useState<SlaAlert[]>([]);
  const [templates, setTemplates] = useState<ConnectorTemplate[]>([]);
  const [maintenanceWindows, setMaintenanceWindows] = useState<MaintenanceWindow[]>([]);
  const [escalationRules, setEscalationRules] = useState<EscalationRule[]>([]);
  const [escalationEvents, setEscalationEvents] = useState<EscalationEvent[]>([]);
  const [runbooks, setRunbooks] = useState<Runbook[]>([]);
  const [runbookAssignments, setRunbookAssignments] = useState<RunbookAssignment[]>([]);
  const [incidentTimeline, setIncidentTimeline] = useState<IncidentTimelineItem[]>([]);
  const [sliTrendPoints, setSliTrendPoints] = useState<SliTrendPoint[]>([]);
  const [postmortems, setPostmortems] = useState<Postmortem[]>([]);
  const [postmortemTemplates, setPostmortemTemplates] = useState<PostmortemTemplate[]>([]);
  const [postmortemActionItems, setPostmortemActionItems] = useState<PostmortemActionItem[]>([]);
  const [postmortemClosureRequests, setPostmortemClosureRequests] = useState<PostmortemClosureRequest[]>([]);
  const [actionItemEscalations, setActionItemEscalations] = useState<ActionItemEscalation[]>([]);
  const [complianceRollups, setComplianceRollups] = useState<ComplianceRollup[]>([]);
  const [escalationRoutingPolicy, setEscalationRoutingPolicy] = useState<EscalationRoutingPolicy | null>(null);
  const [escalationCadencePolicy, setEscalationCadencePolicy] = useState<EscalationCadencePolicy | null>(null);
  const [escalationAgingDashboard, setEscalationAgingDashboard] = useState<EscalationAgingDashboard | null>(null);
  const [breachForecast, setBreachForecast] = useState<BreachForecast | null>(null);
  const [escalationPriorityQueue, setEscalationPriorityQueue] = useState<EscalationPriorityQueue | null>(null);
  const [ownerWorkloadDashboard, setOwnerWorkloadDashboard] = useState<OwnerWorkloadDashboard | null>(null);
  const [rebalanceSuggestions, setRebalanceSuggestions] = useState<RebalanceSuggestions | null>(null);
  const [workloadHotspots, setWorkloadHotspots] = useState<WorkloadHotspots | null>(null);
  const [surgeAlerts, setSurgeAlerts] = useState<SurgeAlerts | null>(null);
  const [balanceIndex, setBalanceIndex] = useState<BalanceIndex | null>(null);
  const [coverageGaps, setCoverageGaps] = useState<CoverageGaps | null>(null);
  const [handoffReadiness, setHandoffReadiness] = useState<HandoffReadiness | null>(null);
  const [continuityRisks, setContinuityRisks] = useState<ContinuityRisks | null>(null);
  const [ownershipChurn, setOwnershipChurn] = useState<OwnershipChurn | null>(null);
  const [stabilityScore, setStabilityScore] = useState<StabilityScore | null>(null);
  const [handoffPlan, setHandoffPlan] = useState<HandoffPlan | null>(null);
  const [resilienceSnapshot, setResilienceSnapshot] = useState<ResilienceSnapshot | null>(null);
  const [remediationQueue, setRemediationQueue] = useState<RemediationQueue | null>(null);
  const [readinessForecast, setReadinessForecast] = useState<ReadinessForecast | null>(null);
  const [remediationThroughput, setRemediationThroughput] = useState<RemediationThroughput | null>(null);
  const [riskBurndown, setRiskBurndown] = useState<RiskBurndown | null>(null);
  const [capacityScenarios, setCapacityScenarios] = useState<CapacityScenarios | null>(null);
  const [remediationSla, setRemediationSla] = useState<RemediationSla | null>(null);
  const [ownerReliefPlan, setOwnerReliefPlan] = useState<OwnerReliefPlan | null>(null);
  const [escalationClearanceEta, setEscalationClearanceEta] = useState<EscalationClearanceEta | null>(null);
  const [mitigationReadiness, setMitigationReadiness] = useState<MitigationReadiness | null>(null);
  const [ownerCoverageForecast, setOwnerCoverageForecast] = useState<OwnerCoverageForecast | null>(null);
  const [handoffPressure, setHandoffPressure] = useState<HandoffPressure | null>(null);
  const [remediationMomentum, setRemediationMomentum] = useState<RemediationMomentum | null>(null);
  const [ownershipStabilityForecast, setOwnershipStabilityForecast] = useState<OwnershipStabilityForecast | null>(null);
  const [escalationBurnRate, setEscalationBurnRate] = useState<EscalationBurnRate | null>(null);
  const [handoffResilienceForecast, setHandoffResilienceForecast] = useState<HandoffResilienceForecast | null>(null);
  const [backlogClearanceConfidence, setBacklogClearanceConfidence] = useState<BacklogClearanceConfidence | null>(null);
  const [remediationVelocityForecast, setRemediationVelocityForecast] = useState<RemediationVelocityForecast | null>(
    null
  );
  const [escalationRecoveryReadiness, setEscalationRecoveryReadiness] = useState<EscalationRecoveryReadiness | null>(
    null
  );
  const [continuityReadinessIndex, setContinuityReadinessIndex] = useState<ContinuityReadinessIndex | null>(null);
  const [escalationDrainForecast, setEscalationDrainForecast] = useState<EscalationDrainForecast | null>(null);
  const [remediationConfidenceForecast, setRemediationConfidenceForecast] =
    useState<RemediationConfidenceForecast | null>(null);
  const [escalationStabilizationIndex, setEscalationStabilizationIndex] = useState<EscalationStabilizationIndex | null>(
    null
  );
  const [remediationPostureScore, setRemediationPostureScore] = useState<RemediationPostureScore | null>(null);
  const [escalationRunwayForecast, setEscalationRunwayForecast] = useState<EscalationRunwayForecast | null>(null);
  const [remediationBalanceIndex, setRemediationBalanceIndex] = useState<RemediationBalanceIndex | null>(null);
  const [escalationPressureForecast, setEscalationPressureForecast] = useState<EscalationPressureForecast | null>(null);
  const [remediationConcentrationForecast, setRemediationConcentrationForecast] =
    useState<RemediationConcentrationForecast | null>(null);
  const [escalationContainmentIndex, setEscalationContainmentIndex] = useState<EscalationContainmentIndex | null>(null);
  const [remediationReadinessBalance, setRemediationReadinessBalance] = useState<RemediationReadinessBalance | null>(
    null
  );
  const [escalationLoadSheddingForecast, setEscalationLoadSheddingForecast] =
    useState<EscalationLoadSheddingForecast | null>(null);
  const [remediationPressureIndex, setRemediationPressureIndex] = useState<RemediationPressureIndex | null>(null);
  const [escalationReliefForecast, setEscalationReliefForecast] = useState<EscalationReliefForecast | null>(null);
  const [remediationRecoveryIndex, setRemediationRecoveryIndex] = useState<RemediationRecoveryIndex | null>(null);
  const [escalationRecoveryIndex, setEscalationRecoveryIndex] = useState<EscalationRecoveryIndex | null>(null);
  const [remediationResilienceForecast, setRemediationResilienceForecast] =
    useState<RemediationResilienceForecast | null>(null);
  const [escalationStabilityIndex, setEscalationStabilityIndex] = useState<EscalationStabilityIndex | null>(null);
  const [remediationSteadinessForecast, setRemediationSteadinessForecast] =
    useState<RemediationSteadinessForecast | null>(null);
  const [escalationSteadinessIndex, setEscalationSteadinessIndex] = useState<EscalationSteadinessIndex | null>(null);
  const [remediationDurabilityForecast, setRemediationDurabilityForecast] =
    useState<RemediationDurabilityForecast | null>(null);
  const [escalationDurabilityIndex, setEscalationDurabilityIndex] = useState<EscalationDurabilityIndex | null>(null);
  const [remediationStabilityForecast, setRemediationStabilityForecast] = useState<RemediationStabilityForecast | null>(
    null
  );
  const [escalationStabilityForecast, setEscalationStabilityForecast] = useState<EscalationStabilityForecast | null>(
    null
  );
  const [remediationConsistencyForecast, setRemediationConsistencyForecast] =
    useState<RemediationConsistencyForecast | null>(null);
  const [escalationConsistencyIndex, setEscalationConsistencyIndex] = useState<EscalationConsistencyIndex | null>(null);
  const [remediationAlignmentForecast, setRemediationAlignmentForecast] = useState<RemediationAlignmentForecast | null>(
    null
  );
  const [escalationAlignmentIndex, setEscalationAlignmentIndex] = useState<EscalationAlignmentIndex | null>(null);
  const [remediationClarityForecast, setRemediationClarityForecast] = useState<RemediationClarityForecast | null>(null);
  const [escalationClarityIndex, setEscalationClarityIndex] = useState<EscalationClarityIndex | null>(null);
  const [remediationComposureForecast, setRemediationComposureForecast] = useState<RemediationComposureForecast | null>(
    null
  );
  const [escalationComposureIndex, setEscalationComposureIndex] = useState<EscalationComposureIndex | null>(null);
  const [remediationFocusForecast, setRemediationFocusForecast] = useState<RemediationFocusForecast | null>(null);
  const [escalationFocusIndex, setEscalationFocusIndex] = useState<EscalationFocusIndex | null>(null);
  const [remediationAttentionForecast, setRemediationAttentionForecast] = useState<RemediationAttentionForecast | null>(
    null
  );
  const [escalationAttentionIndex, setEscalationAttentionIndex] = useState<EscalationAttentionIndex | null>(null);
  const [remediationCoordinationForecast, setRemediationCoordinationForecast] =
    useState<RemediationCoordinationForecast | null>(null);
  const [escalationCoordinationIndex, setEscalationCoordinationIndex] = useState<EscalationCoordinationIndex | null>(
    null
  );
  const [remediationOrchestrationForecast, setRemediationOrchestrationForecast] =
    useState<RemediationOrchestrationForecast | null>(null);
  const [escalationOrchestrationIndex, setEscalationOrchestrationIndex] = useState<EscalationOrchestrationIndex | null>(
    null
  );
  const [remediationSynchronizationForecast, setRemediationSynchronizationForecast] =
    useState<RemediationSynchronizationForecast | null>(null);
  const [escalationSynchronizationIndex, setEscalationSynchronizationIndex] =
    useState<EscalationSynchronizationIndex | null>(null);
  const [remediationHarmonyForecast, setRemediationHarmonyForecast] = useState<RemediationHarmonyForecast | null>(null);
  const [escalationHarmonyIndex, setEscalationHarmonyIndex] = useState<EscalationHarmonyIndex | null>(null);
  const [remediationRhythmForecast, setRemediationRhythmForecast] = useState<RemediationRhythmForecast | null>(null);
  const [escalationRhythmIndex, setEscalationRhythmIndex] = useState<EscalationRhythmIndex | null>(null);
  const [remediationTempoForecast, setRemediationTempoForecast] = useState<RemediationTempoForecast | null>(null);
  const [escalationTempoIndex, setEscalationTempoIndex] = useState<EscalationTempoIndex | null>(null);
  const [remediationCadenceForecast, setRemediationCadenceForecast] = useState<RemediationCadenceForecast | null>(null);
  const [escalationCadenceIndex, setEscalationCadenceIndex] = useState<EscalationCadenceIndex | null>(null);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<number>(0);
  const [selectedRequestId, setSelectedRequestId] = useState<number>(0);
  const [selectedConnectorId, setSelectedConnectorId] = useState<number>(0);

  const [workflowName, setWorkflowName] = useState('High-Risk Publish Guardrail');
  const [requiredApprovals, setRequiredApprovals] = useState(2);
  const [contactId, setContactId] = useState('contact-001');
  const [reviewer, setReviewer] = useState('ops.lead@nuxtron.local');
  const [connectorName, setConnectorName] = useState('hubspot-marketing');
  const [connectorVendor, setConnectorVendor] = useState('HubSpot');
  const [failureType, setFailureType] = useState('timeout');
  const [maxRetries, setMaxRetries] = useState(3);
  const [backoffMs, setBackoffMs] = useState(250);
  const [availabilityTarget, setAvailabilityTarget] = useState(99.9);
  const [latencyTarget, setLatencyTarget] = useState(500);
  const [templateName, setTemplateName] = useState('Default Reliability Template');
  const [maintenanceStartHour, setMaintenanceStartHour] = useState(new Date().getUTCHours());
  const [maintenanceEndHour, setMaintenanceEndHour] = useState((new Date().getUTCHours() + 1) % 24);
  const [escalationRuleName, setEscalationRuleName] = useState('On-call escalation');
  const [runbookName, setRunbookName] = useState('Connector incident runbook');
  const [runbookOperator, setRunbookOperator] = useState('operator@nuxtron.local');
  const [postmortemTitle, setPostmortemTitle] = useState('Connector Incident Postmortem');
  const [postmortemSummary, setPostmortemSummary] = useState(
    'Initial summary of incident impact, root cause, and remediation.'
  );
  const [postmortemTemplateName, setPostmortemTemplateName] = useState('Standard RCA Template');
  const [postmortemActionItemTitle, setPostmortemActionItemTitle] = useState('Validate vendor retry behavior');
  const [closureRequiredApprovals, setClosureRequiredApprovals] = useState(1);
  const [mediumThresholdHours, setMediumThresholdHours] = useState(1);
  const [highThresholdHours, setHighThresholdHours] = useState(24);
  const [criticalThresholdHours, setCriticalThresholdHours] = useState(72);
  const [l2AfterMinutes, setL2AfterMinutes] = useState(30);
  const [l3AfterMinutes, setL3AfterMinutes] = useState(90);
  const [repageIntervalMinutes, setRepageIntervalMinutes] = useState(30);
  const [suppressionTtlMinutes, setSuppressionTtlMinutes] = useState(240);

  const selectedConnector = useMemo(
    () => connectors.find((item) => item.id === selectedConnectorId) || null,
    [connectors, selectedConnectorId]
  );

  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<JsonObject>({});

  const selectedWorkflow = useMemo(
    () => workflows.find((item) => item.id === selectedWorkflowId) || null,
    [workflows, selectedWorkflowId]
  );

  async function refreshData(): Promise<JsonObject> {
    const [wf, pol, req, conn] = await Promise.all([
      apiGet('/workflows', tenantId),
      apiGet('/workflows/approval-policies', tenantId),
      apiGet('/workflows/approval-requests', tenantId),
      apiGet('/workflow-connectors', tenantId),
    ]);
    const replay = await apiGet('/workflow-connectors/replay-queue', tenantId);
    const alerts = await apiGet('/workflow-connectors/sla-alerts', tenantId);
    const templatesResponse = await apiGet('/workflow-connector-templates', tenantId);
    const maintenanceResponse = await apiGet('/workflow-connector-maintenance-windows', tenantId);
    const escalationRulesResponse = await apiGet('/workflow-connector-escalation-rules', tenantId);
    const escalationEventsResponse = await apiGet('/workflow-connector-escalation-events', tenantId);
    const runbooksResponse = await apiGet('/workflow-connector-runbooks', tenantId);
    const postmortemTemplatesResponse = await apiGet('/workflow-connectors/postmortem-templates', tenantId);

    const wfItems = safeArray<Workflow>((wf as JsonObject).workflows);
    const policyItems = safeArray<ApprovalPolicy>((pol as JsonObject).policies);
    const requestItems = safeArray<ApprovalRequest>((req as JsonObject).approval_requests);
    const connectorItems = safeArray<Connector>((conn as JsonObject).connectors);
    const replayItems = safeArray<ReplayQueueItem>((replay as JsonObject).items);
    const alertItems = safeArray<SlaAlert>((alerts as JsonObject).alerts);
    const templateItems = safeArray<ConnectorTemplate>((templatesResponse as JsonObject).templates);
    const maintenanceItems = safeArray<MaintenanceWindow>((maintenanceResponse as JsonObject).windows);
    const escalationRuleItems = safeArray<EscalationRule>((escalationRulesResponse as JsonObject).rules);
    const escalationEventItems = safeArray<EscalationEvent>((escalationEventsResponse as JsonObject).events);
    const runbookItems = safeArray<Runbook>((runbooksResponse as JsonObject).runbooks);
    const postmortemTemplateItems = safeArray<PostmortemTemplate>(
      (postmortemTemplatesResponse as JsonObject).templates
    );

    setWorkflows(wfItems);
    setPolicies(policyItems);
    setRequests(requestItems);
    setConnectors(connectorItems);
    setReplayQueue(replayItems);
    setSlaAlerts(alertItems);
    setTemplates(templateItems);
    setMaintenanceWindows(maintenanceItems);
    setEscalationRules(escalationRuleItems);
    setEscalationEvents(escalationEventItems);
    setRunbooks(runbookItems);
    setPostmortemTemplates(postmortemTemplateItems);

    if (!selectedWorkflowId && wfItems[0]?.id) setSelectedWorkflowId(wfItems[0].id);
    if (!selectedRequestId && requestItems[0]?.id) setSelectedRequestId(requestItems[0].id);
    if (!selectedConnectorId && connectorItems[0]?.id) setSelectedConnectorId(connectorItems[0].id);
    return {};
  }

  useEffect(() => {
    void refreshData().catch(() => {
      // Surface fetch errors only when user runs actions to avoid noisy first render.
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  async function runAction(fn: () => Promise<JsonObject>): Promise<void> {
    setRunning(true);
    setError('');
    try {
      const response = await fn();
      setResult(response);
      await refreshData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setRunning(false);
    }
  }

  async function createHighRiskWorkflow(): Promise<void> {
    await runAction(async () => {
      return (await apiPost(
        '/workflows',
        {
          name: workflowName,
          description: 'Production approval gate for high-impact automation.',
          trigger: { trigger_type: 'manual' },
          steps: [
            {
              step_id: 'notify-owner',
              action_type: 'notify_rep',
              config: { channel: 'slack', message: 'Workflow started' },
            },
            {
              step_id: 'push-webhook',
              action_type: 'send_webhook',
              config: { target: 'https://example.invalid/webhook/publish' },
            },
          ],
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function upsertApprovalPolicy(): Promise<void> {
    if (!selectedWorkflowId) {
      setError('Create or select a workflow first.');
      return;
    }

    await runAction(async () => {
      return (await apiPost(
        '/workflows/approval-policies',
        {
          workflow_id: selectedWorkflowId,
          enabled: true,
          required_approvals: Math.max(1, Math.min(5, requiredApprovals)),
          approver_roles: ['ops_lead', 'legal_reviewer'],
          enforce_for_high_risk_only: true,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function createApprovalRequest(): Promise<void> {
    if (!selectedWorkflowId) {
      setError('Create or select a workflow first.');
      return;
    }

    await runAction(async () => {
      return (await apiPost(
        '/workflows/approval-requests',
        {
          workflow_id: selectedWorkflowId,
          contact_id: contactId,
          reason: 'High-risk workflow enrollment request.',
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function approveSelectedRequest(): Promise<void> {
    if (!selectedRequestId) {
      setError('Create or select an approval request first.');
      return;
    }

    await runAction(async () => {
      return (await apiPost(
        `/workflows/approval-requests/${selectedRequestId}/decision`,
        {
          decision: 'approve',
          reviewer,
          note: 'Approved after governance review.',
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function enrollWithApproval(): Promise<void> {
    if (!selectedWorkflowId) {
      setError('Create or select a workflow first.');
      return;
    }

    await runAction(async () => {
      return (await apiPost(
        `/workflows/${selectedWorkflowId}/enroll`,
        {
          contact_id: contactId,
          contact_email: `${contactId}@example.local`,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function upsertConnector(): Promise<void> {
    await runAction(async () => {
      return (await apiPost(
        '/workflow-connectors',
        {
          name: connectorName,
          vendor: connectorVendor,
          auth_type: 'oauth2',
          capabilities: ['contacts_sync', 'campaign_enroll', 'webhook_dispatch'],
          rate_limit_per_minute: 300,
          error_budget_pct: 1.0,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function healthCheckConnector(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Create or select a connector first.');
      return;
    }

    await runAction(async () => {
      return (await apiPost(`/workflow-connectors/${selectedConnectorId}/health-check`, {}, tenantId)) as JsonObject;
    });
  }

  async function updateReliabilityPolicy(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Create or select a connector first.');
      return;
    }

    await runAction(async () => {
      return (await apiPatch(
        `/workflow-connectors/${selectedConnectorId}/reliability-policy`,
        {
          max_retries: Math.max(0, Math.min(10, maxRetries)),
          base_backoff_ms: Math.max(50, Math.min(30000, backoffMs)),
          circuit_failure_threshold: 3,
          circuit_cooldown_seconds: 120,
          slo_availability_target_pct: Math.max(50, Math.min(100, availabilityTarget)),
          slo_latency_p95_target_ms: Math.max(50, Math.min(60000, latencyTarget)),
          replay_enabled: true,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function simulateFailure(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Create or select a connector first.');
      return;
    }

    await runAction(async () => {
      return (await apiPost(
        `/workflow-connectors/${selectedConnectorId}/simulate-failure`,
        {
          failure_type: failureType,
          operation_ref: `workflow-${selectedWorkflowId || 'x'}-contact-${contactId}`,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function fetchReliability(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Create or select a connector first.');
      return;
    }

    await runAction(async () => {
      return (await apiGet(`/workflow-connectors/${selectedConnectorId}/reliability`, tenantId)) as JsonObject;
    });
  }

  async function replayFirstPending(forceSuccess: boolean): Promise<void> {
    if (!selectedConnectorId) {
      setError('Create or select a connector first.');
      return;
    }
    const item = replayQueue.find(
      (candidate) => candidate.connector_id === selectedConnectorId && candidate.status === 'pending'
    );
    if (!item) {
      setError('No pending replay item for selected connector.');
      return;
    }

    await runAction(async () => {
      return (await apiPost(
        `/workflow-connectors/${selectedConnectorId}/replay-queue/${item.id}/replay`,
        { force_success: forceSuccess },
        tenantId
      )) as JsonObject;
    });
  }

  async function processReplayQueue(forceSuccess: boolean): Promise<void> {
    await runAction(async () => {
      return (await apiPost(
        '/workflow-connectors/replay-queue/process',
        {
          connector_id: selectedConnectorId || undefined,
          limit: 25,
          force_success: forceSuccess,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function reconcileCircuits(): Promise<void> {
    await runAction(async () => {
      return (await apiPost('/workflow-connectors/reconcile-circuits', {}, tenantId)) as JsonObject;
    });
  }

  async function fetchSlaAlerts(): Promise<void> {
    await runAction(async () => {
      return (await apiGet('/workflow-connectors/sla-alerts', tenantId)) as JsonObject;
    });
  }

  async function createTemplate(): Promise<void> {
    await runAction(async () => {
      return (await apiPost(
        '/workflow-connector-templates',
        {
          name: templateName,
          description: 'Tenant baseline reliability policy template.',
          max_retries: Math.max(0, Math.min(10, maxRetries)),
          base_backoff_ms: Math.max(50, Math.min(30000, backoffMs)),
          circuit_failure_threshold: 3,
          circuit_cooldown_seconds: 120,
          slo_availability_target_pct: Math.max(50, Math.min(100, availabilityTarget)),
          slo_latency_p95_target_ms: Math.max(50, Math.min(60000, latencyTarget)),
          replay_enabled: true,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function applyFirstTemplateToSelectedConnector(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Select a connector first.');
      return;
    }
    const template = templates[0];
    if (!template?.id) {
      setError('Create a template first.');
      return;
    }
    await runAction(async () => {
      return (await apiPost(
        `/workflow-connector-templates/${template.id}/apply`,
        { connector_ids: [selectedConnectorId] },
        tenantId
      )) as JsonObject;
    });
  }

  async function createMaintenanceWindow(): Promise<void> {
    await runAction(async () => {
      return (await apiPost(
        '/workflow-connector-maintenance-windows',
        {
          name: `Maintenance ${maintenanceStartHour}-${maintenanceEndHour} UTC`,
          start_hour_utc: Math.max(0, Math.min(23, maintenanceStartHour)),
          end_hour_utc: Math.max(0, Math.min(23, maintenanceEndHour)),
          connector_ids: selectedConnectorId ? [selectedConnectorId] : [],
          enabled: true,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function createEscalationRule(): Promise<void> {
    await runAction(async () => {
      return (await apiPost(
        '/workflow-connector-escalation-rules',
        {
          name: escalationRuleName,
          min_breach_count: 1,
          channels: ['email', 'slack'],
          notify_recipients: ['oncall@nuxtron.local'],
          enabled: true,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function fetchEscalationEvents(): Promise<void> {
    await runAction(async () => {
      return (await apiGet('/workflow-connector-escalation-events', tenantId)) as JsonObject;
    });
  }

  async function acknowledgeFirstEscalationEvent(): Promise<void> {
    const event = escalationEvents.find((candidate) => candidate.status === 'triggered');
    if (!event?.id) {
      setError('No triggered escalation event to acknowledge.');
      return;
    }
    await runAction(async () => {
      return (await apiPost(
        `/workflow-connector-escalation-events/${event.id}/acknowledge`,
        {
          acknowledged_by: reviewer,
          note: 'Acknowledged by workflow operator.',
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function autoResolveEscalations(): Promise<void> {
    await runAction(async () => {
      return (await apiPost('/workflow-connector-escalation-events/auto-resolve', {}, tenantId)) as JsonObject;
    });
  }

  async function createRunbook(): Promise<void> {
    await runAction(async () => {
      return (await apiPost(
        '/workflow-connector-runbooks',
        {
          name: runbookName,
          description: 'Operator playbook for connector incidents and escalations.',
          connector_ids: selectedConnectorId ? [selectedConnectorId] : [],
          steps: ['Check connector health', 'Review replay queue', 'Escalate to on-call if needed'],
          enabled: true,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function assignFirstRunbook(): Promise<void> {
    const runbook = runbooks[0];
    if (!runbook?.id) {
      setError('Create a runbook first.');
      return;
    }
    await runAction(async () => {
      return (await apiPost(
        `/workflow-connector-runbooks/${runbook.id}/assignments`,
        {
          operator: runbookOperator,
          role: 'incident_lead',
          note: 'Primary operator assignment.',
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function fetchFirstRunbookAssignments(): Promise<void> {
    const runbook = runbooks[0];
    if (!runbook?.id) {
      setError('Create a runbook first.');
      return;
    }
    await runAction(async () => {
      const response = (await apiGet(`/workflow-connector-runbooks/${runbook.id}/assignments`, tenantId)) as JsonObject;
      setRunbookAssignments(safeArray<RunbookAssignment>((response as JsonObject).assignments));
      return response;
    });
  }

  async function fetchIncidentTimeline(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Select a connector first.');
      return;
    }
    await runAction(async () => {
      const response = (await apiGet(
        `/workflow-connectors/${selectedConnectorId}/incident-timeline`,
        tenantId
      )) as JsonObject;
      setIncidentTimeline(safeArray<IncidentTimelineItem>((response as JsonObject).timeline));
      return response;
    });
  }

  async function fetchSliTrends(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Select a connector first.');
      return;
    }
    await runAction(async () => {
      const response = (await apiGet(
        `/workflow-connectors/${selectedConnectorId}/sli-trends?buckets=12`,
        tenantId
      )) as JsonObject;
      setSliTrendPoints(safeArray<SliTrendPoint>((response as JsonObject).points));
      return response;
    });
  }

  async function createPostmortem(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Select a connector first.');
      return;
    }
    const connectorEventIds = escalationEvents
      .filter((event) => event.connector_id === selectedConnectorId)
      .slice(0, 5)
      .map((event) => event.id);

    await runAction(async () => {
      return (await apiPost(
        `/workflow-connectors/${selectedConnectorId}/postmortems`,
        {
          title: postmortemTitle,
          summary: postmortemSummary,
          incident_event_ids: connectorEventIds,
          action_items: ['Tune retry policy', 'Add vendor-side alerting', 'Run weekly replay drill'],
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function fetchPostmortems(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Select a connector first.');
      return;
    }
    await runAction(async () => {
      const response = (await apiGet(
        `/workflow-connectors/${selectedConnectorId}/postmortems`,
        tenantId
      )) as JsonObject;
      setPostmortems(safeArray<Postmortem>((response as JsonObject).postmortems));
      return response;
    });
  }

  async function createPostmortemTemplate(): Promise<void> {
    await runAction(async () => {
      return (await apiPost(
        '/workflow-connectors/postmortem-templates',
        {
          name: postmortemTemplateName,
          summary_template: 'Template summary: impact, root cause, timeline, and remediation.',
          default_action_items: ['Confirm root cause', 'Publish customer-facing incident note'],
          closure_sla_hours: 24,
          enabled: true,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function applyFirstPostmortemTemplate(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Select a connector first.');
      return;
    }
    const template = postmortemTemplates[0];
    if (!template?.id) {
      setError('Create a postmortem template first.');
      return;
    }

    const connectorEventIds = escalationEvents
      .filter((event) => event.connector_id === selectedConnectorId)
      .slice(0, 3)
      .map((event) => event.id);

    await runAction(async () => {
      return (await apiPost(
        `/workflow-connectors/postmortem-templates/${template.id}/apply`,
        {
          connector_id: selectedConnectorId,
          title: `${postmortemTitle} (Template Applied)`,
          incident_event_ids: connectorEventIds,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function fetchFirstPostmortemActionItems(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Select a connector first.');
      return;
    }
    const postmortem = postmortems[0];
    if (!postmortem?.id) {
      setError('Create or fetch postmortems first.');
      return;
    }
    await runAction(async () => {
      const response = (await apiGet(
        `/workflow-connectors/${selectedConnectorId}/postmortems/${postmortem.id}/action-items`,
        tenantId
      )) as JsonObject;
      setPostmortemActionItems(safeArray<PostmortemActionItem>((response as JsonObject).action_items));
      return response;
    });
  }

  async function addFirstPostmortemActionItem(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Select a connector first.');
      return;
    }
    const postmortem = postmortems[0];
    if (!postmortem?.id) {
      setError('Create or fetch postmortems first.');
      return;
    }
    await runAction(async () => {
      return (await apiPost(
        `/workflow-connectors/${selectedConnectorId}/postmortems/${postmortem.id}/action-items`,
        {
          title: postmortemActionItemTitle,
          owner: runbookOperator,
          due_in_hours: 24,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function completeFirstPostmortemActionItem(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Select a connector first.');
      return;
    }
    const postmortem = postmortems[0];
    if (!postmortem?.id) {
      setError('Create or fetch postmortems first.');
      return;
    }
    const item = postmortemActionItems[0];
    if (!item?.id) {
      setError('Fetch action items first.');
      return;
    }
    await runAction(async () => {
      return (await apiPatch(
        `/workflow-connectors/${selectedConnectorId}/postmortems/${postmortem.id}/action-items/${item.id}`,
        {
          status: 'done',
          note: 'Completed by incident owner.',
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function closeFirstPostmortem(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Select a connector first.');
      return;
    }
    const postmortem = postmortems[0];
    if (!postmortem?.id) {
      setError('Create or fetch postmortems first.');
      return;
    }
    await runAction(async () => {
      return (await apiPost(
        `/workflow-connectors/${selectedConnectorId}/postmortems/${postmortem.id}/close`,
        {
          closed_by: reviewer,
          note: 'Closure verified after action item completion.',
          require_action_items_resolved: true,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function upsertPostmortemClosurePolicy(): Promise<void> {
    await runAction(async () => {
      return (await apiPost(
        '/workflow-connectors/postmortems/closure-policy',
        {
          enabled: true,
          required_approvals: Math.max(1, Math.min(5, closureRequiredApprovals)),
          approver_roles: ['ops_lead', 'incident_manager'],
          enforce_for_breached_sla_only: false,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function createFirstPostmortemClosureRequest(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Select a connector first.');
      return;
    }
    const postmortem = postmortems[0];
    if (!postmortem?.id) {
      setError('Create or fetch postmortems first.');
      return;
    }
    await runAction(async () => {
      const response = (await apiPost(
        `/workflow-connectors/${selectedConnectorId}/postmortems/${postmortem.id}/closure-requests`,
        {},
        tenantId
      )) as JsonObject;
      const closureRequest = (response as JsonObject).closure_request as PostmortemClosureRequest | undefined;
      if (closureRequest?.id) {
        setPostmortemClosureRequests((prev) => {
          const deduped = prev.filter((item) => item.id !== closureRequest.id);
          return [closureRequest, ...deduped];
        });
      }
      return response;
    });
  }

  async function approveFirstClosureRequest(): Promise<void> {
    if (!selectedConnectorId) {
      setError('Select a connector first.');
      return;
    }
    const postmortem = postmortems[0];
    const closureRequest = postmortemClosureRequests[0];
    if (!postmortem?.id || !closureRequest?.id) {
      setError('Create a closure request first.');
      return;
    }
    await runAction(async () => {
      const response = (await apiPost(
        `/workflow-connectors/${selectedConnectorId}/postmortems/${postmortem.id}/closure-requests/${closureRequest.id}/decision`,
        {
          decision: 'approve',
          reviewer,
          note: 'Closure approval granted.',
        },
        tenantId
      )) as JsonObject;
      const updatedRequest = (response as JsonObject).closure_request as PostmortemClosureRequest | undefined;
      if (updatedRequest?.id) {
        setPostmortemClosureRequests((prev) => {
          const deduped = prev.filter((item) => item.id !== updatedRequest.id);
          return [updatedRequest, ...deduped];
        });
      }
      return response;
    });
  }

  async function processOverdueActionItems(): Promise<void> {
    await runAction(async () => {
      return (await apiPost(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        {
          connector_id: selectedConnectorId || undefined,
          limit: 50,
          include_not_due: false,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function processOverdueActionItemsIncludingNotDue(): Promise<void> {
    await runAction(async () => {
      return (await apiPost(
        '/workflow-connectors/postmortems/action-items/process-overdue',
        {
          connector_id: selectedConnectorId || undefined,
          limit: 50,
          include_not_due: true,
        },
        tenantId
      )) as JsonObject;
    });
  }

  async function fetchOverdueEscalations(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalations?limit=100',
        tenantId
      )) as JsonObject;
      setActionItemEscalations(safeArray<ActionItemEscalation>((response as JsonObject).escalations));
      return response;
    });
  }

  async function fetchComplianceRollups(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/compliance-rollups?weeks=4',
        tenantId
      )) as JsonObject;
      setComplianceRollups(safeArray<ComplianceRollup>((response as JsonObject).rollups));
      return response;
    });
  }

  async function upsertEscalationRoutingPolicy(): Promise<void> {
    await runAction(async () => {
      const response = (await apiPost(
        '/workflow-connectors/postmortems/escalation-routing-policy',
        {
          enabled: true,
          paging_start_hour_utc: 8,
          paging_end_hour_utc: 20,
          in_window_channel: 'pagerduty',
          off_window_channel: 'email',
          medium_threshold_hours: Math.max(1, Math.min(720, mediumThresholdHours)),
          high_threshold_hours: Math.max(1, Math.min(720, highThresholdHours)),
          critical_threshold_hours: Math.max(1, Math.min(720, criticalThresholdHours)),
          medium_recipients: ['ops@nuxtron.local'],
          high_recipients: ['incident@nuxtron.local'],
          critical_recipients: ['sre@nuxtron.local', 'cto@nuxtron.local'],
        },
        tenantId
      )) as JsonObject;
      const policy = (response as JsonObject).policy as EscalationRoutingPolicy | undefined;
      if (policy) setEscalationRoutingPolicy(policy);
      return response;
    });
  }

  async function fetchEscalationRoutingPolicy(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/escalation-routing-policy',
        tenantId
      )) as JsonObject;
      const policy = (response as JsonObject).policy as EscalationRoutingPolicy | undefined;
      if (policy) setEscalationRoutingPolicy(policy);
      return response;
    });
  }

  async function upsertEscalationCadencePolicy(): Promise<void> {
    await runAction(async () => {
      const response = (await apiPost(
        '/workflow-connectors/postmortems/escalation-cadence-policy',
        {
          enabled: true,
          l2_after_minutes: Math.max(0, Math.min(10080, l2AfterMinutes)),
          l3_after_minutes: Math.max(0, Math.min(10080, l3AfterMinutes)),
          repage_interval_minutes: Math.max(0, Math.min(1440, repageIntervalMinutes)),
          max_repages: 8,
          suppression_ttl_minutes: Math.max(0, Math.min(10080, suppressionTtlMinutes)),
          reopen_on_reoverdue: true,
          l1_recipients: ['ops@nuxtron.local'],
          l2_recipients: ['incident@nuxtron.local'],
          l3_recipients: ['sre@nuxtron.local', 'cto@nuxtron.local'],
        },
        tenantId
      )) as JsonObject;
      const policy = (response as JsonObject).policy as EscalationCadencePolicy | undefined;
      if (policy) setEscalationCadencePolicy(policy);
      return response;
    });
  }

  async function fetchEscalationCadencePolicy(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/escalation-cadence-policy',
        tenantId
      )) as JsonObject;
      const policy = (response as JsonObject).policy as EscalationCadencePolicy | undefined;
      if (policy) setEscalationCadencePolicy(policy);
      return response;
    });
  }

  async function processEscalationCadence(): Promise<void> {
    await runAction(async () => {
      return (await apiPost(
        '/workflow-connectors/postmortems/action-items/escalations/process-cadence',
        { limit: 100 },
        tenantId
      )) as JsonObject;
    });
  }

  async function processEscalationSuppression(): Promise<void> {
    await runAction(async () => {
      return (await apiPost(
        '/workflow-connectors/postmortems/action-items/escalations/process-suppression',
        { limit: 100 },
        tenantId
      )) as JsonObject;
    });
  }

  async function fetchEscalationAgingDashboard(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalations/aging-dashboard?ack_slo_minutes=60&lookback_hours=168',
        tenantId
      )) as JsonObject;
      setEscalationAgingDashboard(response as unknown as EscalationAgingDashboard);
      return response;
    });
  }

  async function fetchActionItemBreachForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/breach-forecast?window_hours=24&limit=100',
        tenantId
      )) as JsonObject;
      setBreachForecast(response as unknown as BreachForecast);
      return response;
    });
  }

  async function fetchEscalationPriorityQueue(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalations/priority-queue?limit=100&include_suppressed=true',
        tenantId
      )) as JsonObject;
      setEscalationPriorityQueue(response as unknown as EscalationPriorityQueue);
      return response;
    });
  }

  async function fetchOwnerWorkloadDashboard(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/owner-workload?include_done=false',
        tenantId
      )) as JsonObject;
      setOwnerWorkloadDashboard(response as unknown as OwnerWorkloadDashboard);
      return response;
    });
  }

  async function fetchRebalanceSuggestions(): Promise<void> {
    await runAction(async () => {
      const response = (await apiPost(
        '/workflow-connectors/postmortems/action-items/rebalance-suggestions',
        {
          max_open_items_per_owner: 2,
          include_unassigned: true,
          limit: 25,
        },
        tenantId
      )) as JsonObject;
      setRebalanceSuggestions(response as unknown as RebalanceSuggestions);
      return response;
    });
  }

  async function fetchWorkloadHotspots(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/workload-hotspots?max_open_items_per_owner=3&max_overdue_items_per_owner=1',
        tenantId
      )) as JsonObject;
      setWorkloadHotspots(response as unknown as WorkloadHotspots);
      return response;
    });
  }

  async function fetchSurgeAlerts(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/surge-alerts?lookback_hours=24&min_new_open_escalations=1',
        tenantId
      )) as JsonObject;
      setSurgeAlerts(response as unknown as SurgeAlerts);
      return response;
    });
  }

  async function fetchBalanceIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/balance-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setBalanceIndex(response as unknown as BalanceIndex);
      return response;
    });
  }

  async function fetchCoverageGaps(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/coverage-gaps?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setCoverageGaps(response as unknown as CoverageGaps);
      return response;
    });
  }

  async function fetchHandoffReadiness(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/handoff-readiness?max_open_items_per_owner=3&critical_open_escalations_threshold=1',
        tenantId
      )) as JsonObject;
      setHandoffReadiness(response as unknown as HandoffReadiness);
      return response;
    });
  }

  async function fetchContinuityRisks(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/continuity-risks?min_single_owner_items=2',
        tenantId
      )) as JsonObject;
      setContinuityRisks(response as unknown as ContinuityRisks);
      return response;
    });
  }

  async function fetchOwnershipChurn(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/ownership-churn?min_owner_switch_risk_items=2',
        tenantId
      )) as JsonObject;
      setOwnershipChurn(response as unknown as OwnershipChurn);
      return response;
    });
  }

  async function fetchStabilityScore(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/stability-score?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setStabilityScore(response as unknown as StabilityScore);
      return response;
    });
  }

  async function fetchHandoffPlan(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/handoff-plan?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setHandoffPlan(response as unknown as HandoffPlan);
      return response;
    });
  }

  async function fetchResilienceSnapshot(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/resilience-snapshot?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setResilienceSnapshot(response as unknown as ResilienceSnapshot);
      return response;
    });
  }

  async function fetchRemediationQueue(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-queue?max_open_items_per_owner=3&limit=50',
        tenantId
      )) as JsonObject;
      setRemediationQueue(response as unknown as RemediationQueue);
      return response;
    });
  }

  async function fetchReadinessForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/readiness-forecast?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setReadinessForecast(response as unknown as ReadinessForecast);
      return response;
    });
  }

  async function fetchRemediationThroughput(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-throughput?max_open_items_per_owner=3&days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationThroughput(response as unknown as RemediationThroughput);
      return response;
    });
  }

  async function fetchRiskBurndown(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/risk-burndown?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRiskBurndown(response as unknown as RiskBurndown);
      return response;
    });
  }

  async function fetchCapacityScenarios(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/capacity-scenarios?max_open_items_per_owner=3&days_horizon=7',
        tenantId
      )) as JsonObject;
      setCapacityScenarios(response as unknown as CapacityScenarios);
      return response;
    });
  }

  async function fetchRemediationSla(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-sla?sla_hours=24',
        tenantId
      )) as JsonObject;
      setRemediationSla(response as unknown as RemediationSla);
      return response;
    });
  }

  async function fetchOwnerReliefPlan(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/owner-relief-plan?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setOwnerReliefPlan(response as unknown as OwnerReliefPlan);
      return response;
    });
  }

  async function fetchEscalationClearanceEta(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-clearance-eta?days_horizon=7',
        tenantId
      )) as JsonObject;
      setEscalationClearanceEta(response as unknown as EscalationClearanceEta);
      return response;
    });
  }

  async function fetchMitigationReadiness(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/mitigation-readiness?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setMitigationReadiness(response as unknown as MitigationReadiness);
      return response;
    });
  }

  async function fetchOwnerCoverageForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/owner-coverage-forecast?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setOwnerCoverageForecast(response as unknown as OwnerCoverageForecast);
      return response;
    });
  }

  async function fetchHandoffPressure(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/handoff-pressure?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setHandoffPressure(response as unknown as HandoffPressure);
      return response;
    });
  }

  async function fetchRemediationMomentum(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-momentum?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationMomentum(response as unknown as RemediationMomentum);
      return response;
    });
  }

  async function fetchOwnershipStabilityForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/ownership-stability-forecast?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setOwnershipStabilityForecast(response as unknown as OwnershipStabilityForecast);
      return response;
    });
  }

  async function fetchEscalationBurnRate(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-burn-rate?days_horizon=7',
        tenantId
      )) as JsonObject;
      setEscalationBurnRate(response as unknown as EscalationBurnRate);
      return response;
    });
  }

  async function fetchHandoffResilienceForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/handoff-resilience-forecast?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setHandoffResilienceForecast(response as unknown as HandoffResilienceForecast);
      return response;
    });
  }

  async function fetchBacklogClearanceConfidence(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/backlog-clearance-confidence?days_horizon=7',
        tenantId
      )) as JsonObject;
      setBacklogClearanceConfidence(response as unknown as BacklogClearanceConfidence);
      return response;
    });
  }

  async function fetchRemediationVelocityForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-velocity-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationVelocityForecast(response as unknown as RemediationVelocityForecast);
      return response;
    });
  }

  async function fetchEscalationRecoveryReadiness(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-recovery-readiness?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationRecoveryReadiness(response as unknown as EscalationRecoveryReadiness);
      return response;
    });
  }

  async function fetchContinuityReadinessIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/continuity-readiness-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setContinuityReadinessIndex(response as unknown as ContinuityReadinessIndex);
      return response;
    });
  }

  async function fetchEscalationDrainForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-drain-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setEscalationDrainForecast(response as unknown as EscalationDrainForecast);
      return response;
    });
  }

  async function fetchRemediationConfidenceForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-confidence-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationConfidenceForecast(response as unknown as RemediationConfidenceForecast);
      return response;
    });
  }

  async function fetchEscalationStabilizationIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-stabilization-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationStabilizationIndex(response as unknown as EscalationStabilizationIndex);
      return response;
    });
  }

  async function fetchRemediationPostureScore(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-posture-score?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setRemediationPostureScore(response as unknown as RemediationPostureScore);
      return response;
    });
  }

  async function fetchEscalationRunwayForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-runway-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setEscalationRunwayForecast(response as unknown as EscalationRunwayForecast);
      return response;
    });
  }

  async function fetchRemediationBalanceIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-balance-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setRemediationBalanceIndex(response as unknown as RemediationBalanceIndex);
      return response;
    });
  }

  async function fetchEscalationPressureForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-pressure-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setEscalationPressureForecast(response as unknown as EscalationPressureForecast);
      return response;
    });
  }

  async function fetchRemediationConcentrationForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-concentration-forecast?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setRemediationConcentrationForecast(response as unknown as RemediationConcentrationForecast);
      return response;
    });
  }

  async function fetchEscalationContainmentIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-containment-index?days_horizon=7',
        tenantId
      )) as JsonObject;
      setEscalationContainmentIndex(response as unknown as EscalationContainmentIndex);
      return response;
    });
  }

  async function fetchRemediationReadinessBalance(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-readiness-balance?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setRemediationReadinessBalance(response as unknown as RemediationReadinessBalance);
      return response;
    });
  }

  async function fetchEscalationLoadSheddingForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-load-shedding-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setEscalationLoadSheddingForecast(response as unknown as EscalationLoadSheddingForecast);
      return response;
    });
  }

  async function fetchRemediationPressureIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-pressure-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setRemediationPressureIndex(response as unknown as RemediationPressureIndex);
      return response;
    });
  }

  async function fetchEscalationReliefForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-relief-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setEscalationReliefForecast(response as unknown as EscalationReliefForecast);
      return response;
    });
  }

  async function fetchRemediationRecoveryIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-recovery-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setRemediationRecoveryIndex(response as unknown as RemediationRecoveryIndex);
      return response;
    });
  }

  async function fetchEscalationRecoveryIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-recovery-index?days_horizon=7',
        tenantId
      )) as JsonObject;
      setEscalationRecoveryIndex(response as unknown as EscalationRecoveryIndex);
      return response;
    });
  }

  async function fetchRemediationResilienceForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-resilience-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationResilienceForecast(response as unknown as RemediationResilienceForecast);
      return response;
    });
  }

  async function fetchEscalationStabilityIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-stability-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationStabilityIndex(response as unknown as EscalationStabilityIndex);
      return response;
    });
  }

  async function fetchRemediationSteadinessForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-steadiness-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationSteadinessForecast(response as unknown as RemediationSteadinessForecast);
      return response;
    });
  }

  async function fetchEscalationSteadinessIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-steadiness-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationSteadinessIndex(response as unknown as EscalationSteadinessIndex);
      return response;
    });
  }

  async function fetchRemediationDurabilityForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-durability-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationDurabilityForecast(response as unknown as RemediationDurabilityForecast);
      return response;
    });
  }

  async function fetchEscalationDurabilityIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-durability-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationDurabilityIndex(response as unknown as EscalationDurabilityIndex);
      return response;
    });
  }

  async function fetchRemediationStabilityForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-stability-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationStabilityForecast(response as unknown as RemediationStabilityForecast);
      return response;
    });
  }

  async function fetchEscalationStabilityForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-stability-forecast?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationStabilityForecast(response as unknown as EscalationStabilityForecast);
      return response;
    });
  }

  async function fetchRemediationConsistencyForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-consistency-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationConsistencyForecast(response as unknown as RemediationConsistencyForecast);
      return response;
    });
  }

  async function fetchEscalationConsistencyIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-consistency-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationConsistencyIndex(response as unknown as EscalationConsistencyIndex);
      return response;
    });
  }

  async function fetchRemediationAlignmentForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-alignment-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationAlignmentForecast(response as unknown as RemediationAlignmentForecast);
      return response;
    });
  }

  async function fetchEscalationAlignmentIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-alignment-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationAlignmentIndex(response as unknown as EscalationAlignmentIndex);
      return response;
    });
  }

  async function fetchRemediationClarityForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-clarity-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationClarityForecast(response as unknown as RemediationClarityForecast);
      return response;
    });
  }

  async function fetchEscalationClarityIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-clarity-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationClarityIndex(response as unknown as EscalationClarityIndex);
      return response;
    });
  }

  async function fetchRemediationComposureForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-composure-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationComposureForecast(response as unknown as RemediationComposureForecast);
      return response;
    });
  }

  async function fetchEscalationComposureIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-composure-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationComposureIndex(response as unknown as EscalationComposureIndex);
      return response;
    });
  }

  async function fetchRemediationFocusForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-focus-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationFocusForecast(response as unknown as RemediationFocusForecast);
      return response;
    });
  }

  async function fetchEscalationFocusIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-focus-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationFocusIndex(response as unknown as EscalationFocusIndex);
      return response;
    });
  }

  async function fetchRemediationAttentionForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-attention-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationAttentionForecast(response as unknown as RemediationAttentionForecast);
      return response;
    });
  }

  async function fetchEscalationAttentionIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-attention-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationAttentionIndex(response as unknown as EscalationAttentionIndex);
      return response;
    });
  }

  async function fetchRemediationCoordinationForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-coordination-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationCoordinationForecast(response as unknown as RemediationCoordinationForecast);
      return response;
    });
  }

  async function fetchEscalationCoordinationIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-coordination-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationCoordinationIndex(response as unknown as EscalationCoordinationIndex);
      return response;
    });
  }

  async function fetchRemediationOrchestrationForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-orchestration-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationOrchestrationForecast(response as unknown as RemediationOrchestrationForecast);
      return response;
    });
  }

  async function fetchEscalationOrchestrationIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-orchestration-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationOrchestrationIndex(response as unknown as EscalationOrchestrationIndex);
      return response;
    });
  }

  async function fetchRemediationSynchronizationForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-synchronization-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationSynchronizationForecast(response as unknown as RemediationSynchronizationForecast);
      return response;
    });
  }

  async function fetchEscalationSynchronizationIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-synchronization-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationSynchronizationIndex(response as unknown as EscalationSynchronizationIndex);
      return response;
    });
  }

  async function fetchRemediationHarmonyForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-harmony-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationHarmonyForecast(response as unknown as RemediationHarmonyForecast);
      return response;
    });
  }

  async function fetchEscalationHarmonyIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-harmony-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationHarmonyIndex(response as unknown as EscalationHarmonyIndex);
      return response;
    });
  }

  async function fetchRemediationRhythmForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-rhythm-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationRhythmForecast(response as unknown as RemediationRhythmForecast);
      return response;
    });
  }

  async function fetchEscalationRhythmIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-rhythm-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationRhythmIndex(response as unknown as EscalationRhythmIndex);
      return response;
    });
  }

  async function fetchRemediationTempoForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-tempo-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationTempoForecast(response as unknown as RemediationTempoForecast);
      return response;
    });
  }

  async function fetchEscalationTempoIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-tempo-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationTempoIndex(response as unknown as EscalationTempoIndex);
      return response;
    });
  }

  async function fetchRemediationCadenceForecast(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/remediation-cadence-forecast?days_horizon=7',
        tenantId
      )) as JsonObject;
      setRemediationCadenceForecast(response as unknown as RemediationCadenceForecast);
      return response;
    });
  }

  async function fetchEscalationCadenceIndex(): Promise<void> {
    await runAction(async () => {
      const response = (await apiGet(
        '/workflow-connectors/postmortems/action-items/escalation-cadence-index?max_open_items_per_owner=3',
        tenantId
      )) as JsonObject;
      setEscalationCadenceIndex(response as unknown as EscalationCadenceIndex);
      return response;
    });
  }

  async function acknowledgeFirstEscalation(): Promise<void> {
    const escalation = actionItemEscalations[0];
    if (!escalation?.id) {
      setError('Fetch escalations first.');
      return;
    }
    await runAction(async () => {
      return (await apiPost(
        `/workflow-connectors/postmortems/action-items/escalations/${escalation.id}/acknowledge`,
        {
          acknowledged_by: reviewer,
          note: 'Acknowledged and taken over by incident owner.',
        },
        tenantId
      )) as JsonObject;
    });
  }

  return (
    <main style={{ maxWidth: 1200, margin: '0 auto', padding: '28px 18px', display: 'grid', gap: 16 }}>
      <section>
        <h1 style={{ marginBottom: 6 }}>Workflow Orchestrator</h1>
        <p style={{ margin: 0, color: 'var(--muted)' }}>
          End-to-end governance for automation: high-risk approval chains, explicit reviewer decisions, connector
          registry, and live health checks.
        </p>
      </section>

      <section style={{ border: '1px solid var(--line)', borderRadius: 12, padding: 14, background: 'var(--panel)' }}>
        <label htmlFor="tenant">Tenant ID</label>
        <input
          id="tenant"
          value={tenantId}
          readOnly
          style={{ marginLeft: 10, minWidth: 260 }}
        />
        <button type="button" onClick={() => void runAction(refreshData)} disabled={running} style={{ marginLeft: 10 }}>
          Refresh
        </button>
      </section>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))', gap: 12 }}>
        <article
          style={{
            border: '1px solid var(--line)',
            borderRadius: 12,
            padding: 12,
            background: 'var(--panel)',
            display: 'grid',
            gap: 8,
          }}
        >
          <h2 style={{ fontSize: 18, margin: 0 }}>1) Create Workflow</h2>
          <input
            value={workflowName}
            onChange={(event) => setWorkflowName(event.target.value)}
            placeholder="Workflow name"
          />
          <button type="button" disabled={running} onClick={() => void createHighRiskWorkflow()}>
            Create High-Risk Workflow
          </button>
          <select
            value={selectedWorkflowId}
            onChange={(event) => setSelectedWorkflowId(Number.parseInt(event.target.value, 10))}
          >
            <option value={0}>Select workflow</option>
            {workflows.map((item) => (
              <option value={item.id} key={item.id}>
                #{item.id} {item.name} ({item.status})
              </option>
            ))}
          </select>
          <small style={{ color: 'var(--muted)' }}>
            {selectedWorkflow
              ? `Selected trigger: ${selectedWorkflow.trigger?.trigger_type || 'n/a'} | steps: ${selectedWorkflow.step_count || 0}`
              : 'No workflow selected'}
          </small>
        </article>

        <article
          style={{
            border: '1px solid var(--line)',
            borderRadius: 12,
            padding: 12,
            background: 'var(--panel)',
            display: 'grid',
            gap: 8,
          }}
        >
          <h2 style={{ fontSize: 18, margin: 0 }}>2) Approval Policy</h2>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Required approvals</span>
            <input
              type="number"
              min={1}
              max={5}
              value={requiredApprovals}
              onChange={(event) => setRequiredApprovals(Number.parseInt(event.target.value || '1', 10))}
            />
          </label>
          <button type="button" disabled={running} onClick={() => void upsertApprovalPolicy()}>
            Upsert Policy
          </button>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Policies: {policies.length}</div>
        </article>

        <article
          style={{
            border: '1px solid var(--line)',
            borderRadius: 12,
            padding: 12,
            background: 'var(--panel)',
            display: 'grid',
            gap: 8,
          }}
        >
          <h2 style={{ fontSize: 18, margin: 0 }}>3) Approval Requests</h2>
          <input value={contactId} onChange={(event) => setContactId(event.target.value)} placeholder="contact-id" />
          <button type="button" disabled={running} onClick={() => void createApprovalRequest()}>
            Create Approval Request
          </button>
          <select
            value={selectedRequestId}
            onChange={(event) => setSelectedRequestId(Number.parseInt(event.target.value, 10))}
          >
            <option value={0}>Select request</option>
            {requests.map((item) => (
              <option value={item.id} key={item.id}>
                #{item.id} workflow {item.workflow_id} {item.contact_id} ({item.status})
              </option>
            ))}
          </select>
          <input value={reviewer} onChange={(event) => setReviewer(event.target.value)} placeholder="reviewer" />
          <button type="button" disabled={running} onClick={() => void approveSelectedRequest()}>
            Approve Selected Request
          </button>
          <button type="button" disabled={running} onClick={() => void enrollWithApproval()}>
            Enroll Contact (Policy Enforced)
          </button>
        </article>

        <article
          style={{
            border: '1px solid var(--line)',
            borderRadius: 12,
            padding: 12,
            background: 'var(--panel)',
            display: 'grid',
            gap: 8,
          }}
        >
          <h2 style={{ fontSize: 18, margin: 0 }}>4) Connector Governance</h2>
          <input
            value={connectorName}
            onChange={(event) => setConnectorName(event.target.value)}
            placeholder="connector name"
          />
          <input
            value={connectorVendor}
            onChange={(event) => setConnectorVendor(event.target.value)}
            placeholder="vendor"
          />
          <button type="button" disabled={running} onClick={() => void upsertConnector()}>
            Register Connector
          </button>
          <select
            value={selectedConnectorId}
            onChange={(event) => setSelectedConnectorId(Number.parseInt(event.target.value, 10))}
          >
            <option value={0}>Select connector</option>
            {connectors.map((item) => (
              <option value={item.id} key={item.id}>
                #{item.id} {item.name} ({item.status})
              </option>
            ))}
          </select>
          <button type="button" disabled={running} onClick={() => void healthCheckConnector()}>
            Run Health Check
          </button>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Failure type</span>
            <select value={failureType} onChange={(event) => setFailureType(event.target.value)}>
              <option value="timeout">timeout</option>
              <option value="http_5xx">http_5xx</option>
              <option value="network">network</option>
              <option value="auth">auth</option>
            </select>
          </label>
          <button type="button" disabled={running} onClick={() => void simulateFailure()}>
            Simulate Failure
          </button>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Max retries</span>
            <input
              type="number"
              min={0}
              max={10}
              value={maxRetries}
              onChange={(event) => setMaxRetries(Number.parseInt(event.target.value || '0', 10))}
            />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Base backoff (ms)</span>
            <input
              type="number"
              min={50}
              max={30000}
              value={backoffMs}
              onChange={(event) => setBackoffMs(Number.parseInt(event.target.value || '250', 10))}
            />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Availability target (%)</span>
            <input
              type="number"
              min={50}
              max={100}
              step={0.1}
              value={availabilityTarget}
              onChange={(event) => setAvailabilityTarget(Number.parseFloat(event.target.value || '99.9'))}
            />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Latency p95 target (ms)</span>
            <input
              type="number"
              min={50}
              max={60000}
              value={latencyTarget}
              onChange={(event) => setLatencyTarget(Number.parseInt(event.target.value || '500', 10))}
            />
          </label>
          <button type="button" disabled={running} onClick={() => void updateReliabilityPolicy()}>
            Update Reliability Policy
          </button>
          <button type="button" disabled={running} onClick={() => void fetchReliability()}>
            Fetch Reliability + SLO
          </button>
          <button type="button" disabled={running} onClick={() => void replayFirstPending(true)}>
            Replay First Pending (Force Success)
          </button>
          <button type="button" disabled={running} onClick={() => void processReplayQueue(false)}>
            Process Replay Queue (Due Items)
          </button>
          <button type="button" disabled={running} onClick={() => void processReplayQueue(true)}>
            Process Replay Queue (Force Success)
          </button>
          <button type="button" disabled={running} onClick={() => void reconcileCircuits()}>
            Reconcile Circuits (Cooldown)
          </button>
          <button type="button" disabled={running} onClick={() => void fetchSlaAlerts()}>
            Fetch SLA Alerts
          </button>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Template name</span>
            <input value={templateName} onChange={(event) => setTemplateName(event.target.value)} />
          </label>
          <button type="button" disabled={running} onClick={() => void createTemplate()}>
            Create Policy Template
          </button>
          <button type="button" disabled={running} onClick={() => void applyFirstTemplateToSelectedConnector()}>
            Apply First Template To Selected Connector
          </button>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Maintenance start hour (UTC)</span>
            <input
              type="number"
              min={0}
              max={23}
              value={maintenanceStartHour}
              onChange={(event) => setMaintenanceStartHour(Number.parseInt(event.target.value || '0', 10))}
            />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Maintenance end hour (UTC)</span>
            <input
              type="number"
              min={0}
              max={23}
              value={maintenanceEndHour}
              onChange={(event) => setMaintenanceEndHour(Number.parseInt(event.target.value || '1', 10))}
            />
          </label>
          <button type="button" disabled={running} onClick={() => void createMaintenanceWindow()}>
            Create Maintenance Window
          </button>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Escalation rule name</span>
            <input value={escalationRuleName} onChange={(event) => setEscalationRuleName(event.target.value)} />
          </label>
          <button type="button" disabled={running} onClick={() => void createEscalationRule()}>
            Create Escalation Rule
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationEvents()}>
            Fetch Escalation Events
          </button>
          <button type="button" disabled={running} onClick={() => void acknowledgeFirstEscalationEvent()}>
            Acknowledge First Triggered Escalation
          </button>
          <button type="button" disabled={running} onClick={() => void autoResolveEscalations()}>
            Auto-Resolve Escalations
          </button>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Runbook name</span>
            <input value={runbookName} onChange={(event) => setRunbookName(event.target.value)} />
          </label>
          <button type="button" disabled={running} onClick={() => void createRunbook()}>
            Create Runbook
          </button>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Runbook operator</span>
            <input value={runbookOperator} onChange={(event) => setRunbookOperator(event.target.value)} />
          </label>
          <button type="button" disabled={running} onClick={() => void assignFirstRunbook()}>
            Assign First Runbook
          </button>
          <button type="button" disabled={running} onClick={() => void fetchFirstRunbookAssignments()}>
            Fetch First Runbook Assignments
          </button>
          <button type="button" disabled={running} onClick={() => void fetchIncidentTimeline()}>
            Fetch Incident Timeline
          </button>
          <button type="button" disabled={running} onClick={() => void fetchSliTrends()}>
            Fetch SLI Trends
          </button>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Postmortem title</span>
            <input value={postmortemTitle} onChange={(event) => setPostmortemTitle(event.target.value)} />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Postmortem summary</span>
            <textarea
              value={postmortemSummary}
              onChange={(event) => setPostmortemSummary(event.target.value)}
              rows={3}
            />
          </label>
          <button type="button" disabled={running} onClick={() => void createPostmortem()}>
            Create Postmortem
          </button>
          <button type="button" disabled={running} onClick={() => void fetchPostmortems()}>
            Fetch Postmortems
          </button>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Postmortem template name</span>
            <input value={postmortemTemplateName} onChange={(event) => setPostmortemTemplateName(event.target.value)} />
          </label>
          <button type="button" disabled={running} onClick={() => void createPostmortemTemplate()}>
            Create Postmortem Template
          </button>
          <button type="button" disabled={running} onClick={() => void applyFirstPostmortemTemplate()}>
            Apply First Postmortem Template
          </button>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Postmortem action item title</span>
            <input
              value={postmortemActionItemTitle}
              onChange={(event) => setPostmortemActionItemTitle(event.target.value)}
            />
          </label>
          <button type="button" disabled={running} onClick={() => void addFirstPostmortemActionItem()}>
            Add Action Item To First Postmortem
          </button>
          <button type="button" disabled={running} onClick={() => void fetchFirstPostmortemActionItems()}>
            Fetch First Postmortem Action Items
          </button>
          <button type="button" disabled={running} onClick={() => void completeFirstPostmortemActionItem()}>
            Complete First Postmortem Action Item
          </button>
          <button type="button" disabled={running} onClick={() => void closeFirstPostmortem()}>
            Close First Postmortem
          </button>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Closure required approvals</span>
            <input
              type="number"
              min={1}
              max={5}
              value={closureRequiredApprovals}
              onChange={(event) => setClosureRequiredApprovals(Number.parseInt(event.target.value || '1', 10))}
            />
          </label>
          <button type="button" disabled={running} onClick={() => void upsertPostmortemClosurePolicy()}>
            Upsert Closure Approval Policy
          </button>
          <button type="button" disabled={running} onClick={() => void createFirstPostmortemClosureRequest()}>
            Create First Postmortem Closure Request
          </button>
          <button type="button" disabled={running} onClick={() => void approveFirstClosureRequest()}>
            Approve First Closure Request
          </button>
          <button type="button" disabled={running} onClick={() => void processOverdueActionItems()}>
            Process Overdue Action Items
          </button>
          <button type="button" disabled={running} onClick={() => void processOverdueActionItemsIncludingNotDue()}>
            Process Overdue Action Items (Include Not Due)
          </button>
          <button type="button" disabled={running} onClick={() => void fetchOverdueEscalations()}>
            Fetch Overdue Escalations
          </button>
          <button type="button" disabled={running} onClick={() => void fetchComplianceRollups()}>
            Fetch Compliance Rollups
          </button>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Medium threshold hours</span>
            <input
              type="number"
              min={1}
              max={720}
              value={mediumThresholdHours}
              onChange={(event) => setMediumThresholdHours(Number.parseInt(event.target.value || '1', 10))}
            />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>High threshold hours</span>
            <input
              type="number"
              min={1}
              max={720}
              value={highThresholdHours}
              onChange={(event) => setHighThresholdHours(Number.parseInt(event.target.value || '24', 10))}
            />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Critical threshold hours</span>
            <input
              type="number"
              min={1}
              max={720}
              value={criticalThresholdHours}
              onChange={(event) => setCriticalThresholdHours(Number.parseInt(event.target.value || '72', 10))}
            />
          </label>
          <button type="button" disabled={running} onClick={() => void upsertEscalationRoutingPolicy()}>
            Upsert Escalation Routing Policy
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationRoutingPolicy()}>
            Fetch Escalation Routing Policy
          </button>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>L2 after minutes</span>
            <input
              type="number"
              min={0}
              max={10080}
              value={l2AfterMinutes}
              onChange={(event) => setL2AfterMinutes(Number.parseInt(event.target.value || '30', 10))}
            />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>L3 after minutes</span>
            <input
              type="number"
              min={0}
              max={10080}
              value={l3AfterMinutes}
              onChange={(event) => setL3AfterMinutes(Number.parseInt(event.target.value || '90', 10))}
            />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Re-page interval minutes</span>
            <input
              type="number"
              min={0}
              max={1440}
              value={repageIntervalMinutes}
              onChange={(event) => setRepageIntervalMinutes(Number.parseInt(event.target.value || '30', 10))}
            />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>Suppression TTL minutes</span>
            <input
              type="number"
              min={0}
              max={10080}
              value={suppressionTtlMinutes}
              onChange={(event) => setSuppressionTtlMinutes(Number.parseInt(event.target.value || '240', 10))}
            />
          </label>
          <button type="button" disabled={running} onClick={() => void upsertEscalationCadencePolicy()}>
            Upsert Escalation Cadence Policy
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationCadencePolicy()}>
            Fetch Escalation Cadence Policy
          </button>
          <button type="button" disabled={running} onClick={() => void processEscalationCadence()}>
            Process Escalation Cadence
          </button>
          <button type="button" disabled={running} onClick={() => void processEscalationSuppression()}>
            Process Escalation Suppression
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationAgingDashboard()}>
            Fetch Escalation Aging Dashboard
          </button>
          <button type="button" disabled={running} onClick={() => void fetchActionItemBreachForecast()}>
            Fetch Breach Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationPriorityQueue()}>
            Fetch Escalation Priority Queue
          </button>
          <button type="button" disabled={running} onClick={() => void fetchOwnerWorkloadDashboard()}>
            Fetch Owner Workload Dashboard
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRebalanceSuggestions()}>
            Fetch Rebalance Suggestions
          </button>
          <button type="button" disabled={running} onClick={() => void fetchWorkloadHotspots()}>
            Fetch Workload Hotspots
          </button>
          <button type="button" disabled={running} onClick={() => void fetchSurgeAlerts()}>
            Fetch Surge Alerts
          </button>
          <button type="button" disabled={running} onClick={() => void fetchBalanceIndex()}>
            Fetch Balance Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchCoverageGaps()}>
            Fetch Coverage Gaps
          </button>
          <button type="button" disabled={running} onClick={() => void fetchHandoffReadiness()}>
            Fetch Handoff Readiness
          </button>
          <button type="button" disabled={running} onClick={() => void fetchContinuityRisks()}>
            Fetch Continuity Risks
          </button>
          <button type="button" disabled={running} onClick={() => void fetchOwnershipChurn()}>
            Fetch Ownership Churn
          </button>
          <button type="button" disabled={running} onClick={() => void fetchStabilityScore()}>
            Fetch Stability Score
          </button>
          <button type="button" disabled={running} onClick={() => void fetchHandoffPlan()}>
            Fetch Handoff Plan
          </button>
          <button type="button" disabled={running} onClick={() => void fetchResilienceSnapshot()}>
            Fetch Resilience Snapshot
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationQueue()}>
            Fetch Remediation Queue
          </button>
          <button type="button" disabled={running} onClick={() => void fetchReadinessForecast()}>
            Fetch Readiness Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationThroughput()}>
            Fetch Remediation Throughput
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRiskBurndown()}>
            Fetch Risk Burndown
          </button>
          <button type="button" disabled={running} onClick={() => void fetchCapacityScenarios()}>
            Fetch Capacity Scenarios
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationSla()}>
            Fetch Remediation SLA
          </button>
          <button type="button" disabled={running} onClick={() => void fetchOwnerReliefPlan()}>
            Fetch Owner Relief Plan
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationClearanceEta()}>
            Fetch Escalation Clearance ETA
          </button>
          <button type="button" disabled={running} onClick={() => void fetchMitigationReadiness()}>
            Fetch Mitigation Readiness
          </button>
          <button type="button" disabled={running} onClick={() => void fetchOwnerCoverageForecast()}>
            Fetch Owner Coverage Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchHandoffPressure()}>
            Fetch Handoff Pressure
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationMomentum()}>
            Fetch Remediation Momentum
          </button>
          <button type="button" disabled={running} onClick={() => void fetchOwnershipStabilityForecast()}>
            Fetch Ownership Stability Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationBurnRate()}>
            Fetch Escalation Burn Rate
          </button>
          <button type="button" disabled={running} onClick={() => void fetchHandoffResilienceForecast()}>
            Fetch Handoff Resilience Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchBacklogClearanceConfidence()}>
            Fetch Backlog Clearance Confidence
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationVelocityForecast()}>
            Fetch Remediation Velocity Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationRecoveryReadiness()}>
            Fetch Escalation Recovery Readiness
          </button>
          <button type="button" disabled={running} onClick={() => void fetchContinuityReadinessIndex()}>
            Fetch Continuity Readiness Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationDrainForecast()}>
            Fetch Escalation Drain Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationConfidenceForecast()}>
            Fetch Remediation Confidence Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationStabilizationIndex()}>
            Fetch Escalation Stabilization Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationPostureScore()}>
            Fetch Remediation Posture Score
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationRunwayForecast()}>
            Fetch Escalation Runway Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationBalanceIndex()}>
            Fetch Remediation Balance Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationPressureForecast()}>
            Fetch Escalation Pressure Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationConcentrationForecast()}>
            Fetch Remediation Concentration Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationContainmentIndex()}>
            Fetch Escalation Containment Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationReadinessBalance()}>
            Fetch Remediation Readiness Balance
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationLoadSheddingForecast()}>
            Fetch Escalation Load Shedding Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationPressureIndex()}>
            Fetch Remediation Pressure Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationReliefForecast()}>
            Fetch Escalation Relief Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationRecoveryIndex()}>
            Fetch Remediation Recovery Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationRecoveryIndex()}>
            Fetch Escalation Recovery Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationResilienceForecast()}>
            Fetch Remediation Resilience Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationStabilityIndex()}>
            Fetch Escalation Stability Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationSteadinessForecast()}>
            Fetch Remediation Steadiness Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationSteadinessIndex()}>
            Fetch Escalation Steadiness Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationDurabilityForecast()}>
            Fetch Remediation Durability Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationDurabilityIndex()}>
            Fetch Escalation Durability Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationStabilityForecast()}>
            Fetch Remediation Stability Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationStabilityForecast()}>
            Fetch Escalation Stability Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationConsistencyForecast()}>
            Fetch Remediation Consistency Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationConsistencyIndex()}>
            Fetch Escalation Consistency Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationAlignmentForecast()}>
            Fetch Remediation Alignment Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationAlignmentIndex()}>
            Fetch Escalation Alignment Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationClarityForecast()}>
            Fetch Remediation Clarity Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationClarityIndex()}>
            Fetch Escalation Clarity Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationComposureForecast()}>
            Fetch Remediation Composure Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationComposureIndex()}>
            Fetch Escalation Composure Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationFocusForecast()}>
            Fetch Remediation Focus Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationFocusIndex()}>
            Fetch Escalation Focus Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationAttentionForecast()}>
            Fetch Remediation Attention Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationAttentionIndex()}>
            Fetch Escalation Attention Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationCoordinationForecast()}>
            Fetch Remediation Coordination Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationCoordinationIndex()}>
            Fetch Escalation Coordination Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationOrchestrationForecast()}>
            Fetch Remediation Orchestration Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationOrchestrationIndex()}>
            Fetch Escalation Orchestration Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationSynchronizationForecast()}>
            Fetch Remediation Synchronization Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationSynchronizationIndex()}>
            Fetch Escalation Synchronization Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationHarmonyForecast()}>
            Fetch Remediation Harmony Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationHarmonyIndex()}>
            Fetch Escalation Harmony Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationRhythmForecast()}>
            Fetch Remediation Rhythm Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationRhythmIndex()}>
            Fetch Escalation Rhythm Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationTempoForecast()}>
            Fetch Remediation Tempo Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationTempoIndex()}>
            Fetch Escalation Tempo Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationCadenceForecast()}>
            Fetch Remediation Cadence Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationCadenceIndex()}>
            Fetch Escalation Cadence Index
          </button>
          <button type="button" disabled={running} onClick={() => void fetchRemediationStabilityForecast()}>
            Fetch Remediation Stability Forecast
          </button>
          <button type="button" disabled={running} onClick={() => void fetchEscalationStabilityIndex()}>
            Fetch Escalation Stability Index
          </button>
          <button type="button" disabled={running} onClick={() => void acknowledgeFirstEscalation()}>
            Acknowledge First Overdue Escalation
          </button>
          <small style={{ color: 'var(--muted)' }}>
            Pending replay items for selected connector:{' '}
            {
              replayQueue.filter((item) => item.connector_id === selectedConnectorId && item.status === 'pending')
                .length
            }
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Open SLA alerts for selected connector:{' '}
            {slaAlerts.filter((alert) => alert.connector_id === selectedConnectorId && alert.status === 'open').length}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Templates: {templates.length} | Maintenance windows: {maintenanceWindows.length}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation rules: {escalationRules.length} | Escalation events: {escalationEvents.length}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Runbooks: {runbooks.length} | Runbook assignments: {runbookAssignments.length}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Incident timeline entries: {incidentTimeline.length} | SLI points: {sliTrendPoints.length}
          </small>
          <small style={{ color: 'var(--muted)' }}>Postmortems: {postmortems.length}</small>
          <small style={{ color: 'var(--muted)' }}>
            Postmortem templates: {postmortemTemplates.length} | Postmortem action items: {postmortemActionItems.length}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Closure requests: {postmortemClosureRequests.length} | Overdue escalations: {actionItemEscalations.length}
          </small>
          <small style={{ color: 'var(--muted)' }}>Weekly compliance rollups: {complianceRollups.length}</small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation routing policy:{' '}
            {escalationRoutingPolicy
              ? `${escalationRoutingPolicy.in_window_channel}/${escalationRoutingPolicy.off_window_channel}`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation cadence policy:{' '}
            {escalationCadencePolicy
              ? `L2 ${escalationCadencePolicy.l2_after_minutes}m, L3 ${escalationCadencePolicy.l3_after_minutes}m`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation aging dashboard:{' '}
            {escalationAgingDashboard
              ? `open ${escalationAgingDashboard.open_escalations}, ack SLO ${escalationAgingDashboard.ack_slo_compliance_pct}%`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Breach forecast:{' '}
            {breachForecast
              ? `at risk ${breachForecast.at_risk_total}, breached ${breachForecast.breached_count}`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation priority queue:{' '}
            {escalationPriorityQueue
              ? `ranked ${escalationPriorityQueue.count}/${escalationPriorityQueue.total_candidates}`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Owner workload:{' '}
            {ownerWorkloadDashboard
              ? `${ownerWorkloadDashboard.total_owners} owners, ${ownerWorkloadDashboard.total_open_action_items} open items`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Rebalance suggestions:{' '}
            {rebalanceSuggestions ? `${rebalanceSuggestions.count} suggested moves` : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Workload hotspots: {workloadHotspots ? `${workloadHotspots.count} active owners` : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Surge alerts: {surgeAlerts ? `${surgeAlerts.count} owners in surge` : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Balance index:{' '}
            {balanceIndex
              ? `${balanceIndex.balance_index} (overloaded owners ${balanceIndex.overloaded_owner_count})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Coverage gaps:{' '}
            {coverageGaps
              ? `${coverageGaps.count} gaps, ${coverageGaps.unassigned_open_items} unassigned`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Handoff readiness: {handoffReadiness ? `${handoffReadiness.count} owners scored` : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Continuity risks: {continuityRisks ? `${continuityRisks.count} risks identified` : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Ownership churn: {ownershipChurn ? `${ownershipChurn.count} connectors scored` : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Stability score:{' '}
            {stabilityScore ? `${stabilityScore.stability_score} (${stabilityScore.stability_band})` : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Handoff plan: {handoffPlan ? `${handoffPlan.count} owner plans` : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Resilience snapshot:{' '}
            {resilienceSnapshot
              ? `${resilienceSnapshot.resilience_score} (${resilienceSnapshot.resilience_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation queue: {remediationQueue ? `${remediationQueue.count} prioritized actions` : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Readiness forecast:{' '}
            {readinessForecast
              ? `${readinessForecast.readiness_forecast_score} (${readinessForecast.forecast_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation throughput:{' '}
            {remediationThroughput
              ? `${remediationThroughput.required_daily_remediations}/day (${remediationThroughput.throughput_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Risk burndown:{' '}
            {riskBurndown ? `${riskBurndown.risk_burndown_index} (${riskBurndown.burndown_band})` : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Capacity scenarios: {capacityScenarios ? `${capacityScenarios.count} modeled` : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation SLA:{' '}
            {remediationSla ? `${remediationSla.remediation_sla_score} (${remediationSla.sla_band})` : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Owner relief plan: {ownerReliefPlan ? `${ownerReliefPlan.count} owner plans` : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation clearance ETA:{' '}
            {escalationClearanceEta
              ? `${escalationClearanceEta.clearance_eta_days}d (${escalationClearanceEta.eta_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Mitigation readiness:{' '}
            {mitigationReadiness
              ? `${mitigationReadiness.mitigation_readiness_score} (${mitigationReadiness.readiness_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Owner coverage forecast:{' '}
            {ownerCoverageForecast
              ? `${ownerCoverageForecast.owner_coverage_score} (${ownerCoverageForecast.coverage_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Handoff pressure:{' '}
            {handoffPressure
              ? `${handoffPressure.handoff_pressure_score} (${handoffPressure.pressure_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation momentum:{' '}
            {remediationMomentum
              ? `${remediationMomentum.remediation_momentum_score} (${remediationMomentum.momentum_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Ownership stability forecast:{' '}
            {ownershipStabilityForecast
              ? `${ownershipStabilityForecast.ownership_stability_score} (${ownershipStabilityForecast.stability_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation burn rate:{' '}
            {escalationBurnRate
              ? `${escalationBurnRate.target_daily_burn}/day (${escalationBurnRate.burn_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Handoff resilience forecast:{' '}
            {handoffResilienceForecast
              ? `${handoffResilienceForecast.handoff_resilience_score} (${handoffResilienceForecast.resilience_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Backlog clearance confidence:{' '}
            {backlogClearanceConfidence
              ? `${backlogClearanceConfidence.backlog_clearance_confidence} (${backlogClearanceConfidence.confidence_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation velocity forecast:{' '}
            {remediationVelocityForecast
              ? `${remediationVelocityForecast.remediation_velocity_score} (${remediationVelocityForecast.velocity_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation recovery readiness:{' '}
            {escalationRecoveryReadiness
              ? `${escalationRecoveryReadiness.escalation_recovery_score} (${escalationRecoveryReadiness.recovery_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Continuity readiness index:{' '}
            {continuityReadinessIndex
              ? `${continuityReadinessIndex.continuity_readiness_index} (${continuityReadinessIndex.continuity_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation drain forecast:{' '}
            {escalationDrainForecast
              ? `${escalationDrainForecast.required_daily_drain}/day (${escalationDrainForecast.drain_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation confidence forecast:{' '}
            {remediationConfidenceForecast
              ? `${remediationConfidenceForecast.remediation_confidence_score} (${remediationConfidenceForecast.confidence_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation stabilization index:{' '}
            {escalationStabilizationIndex
              ? `${escalationStabilizationIndex.escalation_stabilization_index} (${escalationStabilizationIndex.stabilization_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation posture score:{' '}
            {remediationPostureScore
              ? `${remediationPostureScore.remediation_posture_score} (${remediationPostureScore.posture_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation runway forecast:{' '}
            {escalationRunwayForecast
              ? `${escalationRunwayForecast.required_daily_runway_actions}/day (${escalationRunwayForecast.runway_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation balance index:{' '}
            {remediationBalanceIndex
              ? `${remediationBalanceIndex.remediation_balance_index} (${remediationBalanceIndex.balance_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation pressure forecast:{' '}
            {escalationPressureForecast
              ? `${escalationPressureForecast.required_daily_pressure_actions}/day (${escalationPressureForecast.pressure_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation concentration forecast:{' '}
            {remediationConcentrationForecast
              ? `${remediationConcentrationForecast.remediation_concentration_score} (${remediationConcentrationForecast.concentration_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation containment index:{' '}
            {escalationContainmentIndex
              ? `${escalationContainmentIndex.escalation_containment_index} (${escalationContainmentIndex.containment_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation readiness balance:{' '}
            {remediationReadinessBalance
              ? `${remediationReadinessBalance.remediation_readiness_balance} (${remediationReadinessBalance.readiness_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation load shedding forecast:{' '}
            {escalationLoadSheddingForecast
              ? `${escalationLoadSheddingForecast.required_daily_load_shedding}/day (${escalationLoadSheddingForecast.shedding_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation pressure index:{' '}
            {remediationPressureIndex
              ? `${remediationPressureIndex.remediation_pressure_index} (${remediationPressureIndex.pressure_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation relief forecast:{' '}
            {escalationReliefForecast
              ? `${escalationReliefForecast.required_daily_relief_actions}/day (${escalationReliefForecast.relief_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation recovery index:{' '}
            {remediationRecoveryIndex
              ? `${remediationRecoveryIndex.remediation_recovery_index} (${remediationRecoveryIndex.recovery_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation recovery index:{' '}
            {escalationRecoveryIndex
              ? `${escalationRecoveryIndex.required_daily_recovery_actions}/day (${escalationRecoveryIndex.recovery_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation resilience forecast:{' '}
            {remediationResilienceForecast
              ? `${remediationResilienceForecast.remediation_resilience_score} (${remediationResilienceForecast.resilience_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation stability index:{' '}
            {escalationStabilityIndex
              ? `${escalationStabilityIndex.escalation_stability_index} (${escalationStabilityIndex.stability_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation steadiness forecast:{' '}
            {remediationSteadinessForecast
              ? `${remediationSteadinessForecast.remediation_steadiness_score} (${remediationSteadinessForecast.steadiness_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation steadiness index:{' '}
            {escalationSteadinessIndex
              ? `${escalationSteadinessIndex.escalation_steadiness_index} (${escalationSteadinessIndex.steadiness_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation durability forecast:{' '}
            {remediationDurabilityForecast
              ? `${remediationDurabilityForecast.remediation_durability_score} (${remediationDurabilityForecast.durability_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation durability index:{' '}
            {escalationDurabilityIndex
              ? `${escalationDurabilityIndex.escalation_durability_index} (${escalationDurabilityIndex.durability_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation stability forecast:{' '}
            {remediationStabilityForecast
              ? `${remediationStabilityForecast.remediation_stability_score} (${remediationStabilityForecast.stability_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation stability forecast:{' '}
            {escalationStabilityForecast
              ? `${escalationStabilityForecast.escalation_stability_forecast} (${escalationStabilityForecast.stability_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation consistency forecast:{' '}
            {remediationConsistencyForecast
              ? `${remediationConsistencyForecast.remediation_consistency_score} (${remediationConsistencyForecast.consistency_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation consistency index:{' '}
            {escalationConsistencyIndex
              ? `${escalationConsistencyIndex.escalation_consistency_index} (${escalationConsistencyIndex.consistency_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation alignment forecast:{' '}
            {remediationAlignmentForecast
              ? `${remediationAlignmentForecast.remediation_alignment_score} (${remediationAlignmentForecast.alignment_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation alignment index:{' '}
            {escalationAlignmentIndex
              ? `${escalationAlignmentIndex.escalation_alignment_index} (${escalationAlignmentIndex.alignment_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation clarity forecast:{' '}
            {remediationClarityForecast
              ? `${remediationClarityForecast.remediation_clarity_score} (${remediationClarityForecast.clarity_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation clarity index:{' '}
            {escalationClarityIndex
              ? `${escalationClarityIndex.escalation_clarity_index} (${escalationClarityIndex.clarity_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation composure forecast:{' '}
            {remediationComposureForecast
              ? `${remediationComposureForecast.remediation_composure_score} (${remediationComposureForecast.composure_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation composure index:{' '}
            {escalationComposureIndex
              ? `${escalationComposureIndex.escalation_composure_index} (${escalationComposureIndex.composure_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation focus forecast:{' '}
            {remediationFocusForecast
              ? `${remediationFocusForecast.remediation_focus_score} (${remediationFocusForecast.focus_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation focus index:{' '}
            {escalationFocusIndex
              ? `${escalationFocusIndex.escalation_focus_index} (${escalationFocusIndex.focus_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation attention forecast:{' '}
            {remediationAttentionForecast
              ? `${remediationAttentionForecast.remediation_attention_score} (${remediationAttentionForecast.attention_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation attention index:{' '}
            {escalationAttentionIndex
              ? `${escalationAttentionIndex.escalation_attention_index} (${escalationAttentionIndex.attention_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation coordination forecast:{' '}
            {remediationCoordinationForecast
              ? `${remediationCoordinationForecast.remediation_coordination_score} (${remediationCoordinationForecast.coordination_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation coordination index:{' '}
            {escalationCoordinationIndex
              ? `${escalationCoordinationIndex.escalation_coordination_index} (${escalationCoordinationIndex.coordination_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation orchestration forecast:{' '}
            {remediationOrchestrationForecast
              ? `${remediationOrchestrationForecast.remediation_orchestration_score} (${remediationOrchestrationForecast.orchestration_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation orchestration index:{' '}
            {escalationOrchestrationIndex
              ? `${escalationOrchestrationIndex.escalation_orchestration_index} (${escalationOrchestrationIndex.orchestration_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation synchronization forecast:{' '}
            {remediationSynchronizationForecast
              ? `${remediationSynchronizationForecast.remediation_synchronization_score} (${remediationSynchronizationForecast.synchronization_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation synchronization index:{' '}
            {escalationSynchronizationIndex
              ? `${escalationSynchronizationIndex.escalation_synchronization_index} (${escalationSynchronizationIndex.synchronization_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation harmony forecast:{' '}
            {remediationHarmonyForecast
              ? `${remediationHarmonyForecast.remediation_harmony_score} (${remediationHarmonyForecast.harmony_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation harmony index:{' '}
            {escalationHarmonyIndex
              ? `${escalationHarmonyIndex.escalation_harmony_index} (${escalationHarmonyIndex.harmony_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation rhythm forecast:{' '}
            {remediationRhythmForecast
              ? `${remediationRhythmForecast.remediation_rhythm_score} (${remediationRhythmForecast.rhythm_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation rhythm index:{' '}
            {escalationRhythmIndex
              ? `${escalationRhythmIndex.escalation_rhythm_index} (${escalationRhythmIndex.rhythm_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation tempo forecast:{' '}
            {remediationTempoForecast
              ? `${remediationTempoForecast.remediation_tempo_score} (${remediationTempoForecast.tempo_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation tempo index:{' '}
            {escalationTempoIndex
              ? `${escalationTempoIndex.escalation_tempo_index} (${escalationTempoIndex.tempo_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation cadence forecast:{' '}
            {remediationCadenceForecast
              ? `${remediationCadenceForecast.remediation_cadence_score} (${remediationCadenceForecast.cadence_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation cadence index:{' '}
            {escalationCadenceIndex
              ? `${escalationCadenceIndex.escalation_cadence_index} (${escalationCadenceIndex.cadence_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Remediation stability forecast:{' '}
            {remediationStabilityForecast
              ? `${remediationStabilityForecast.remediation_stability_score} (${remediationStabilityForecast.stability_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Escalation stability index:{' '}
            {escalationStabilityIndex
              ? `${escalationStabilityIndex.escalation_stability_index} (${escalationStabilityIndex.stability_band})`
              : 'not loaded'}
          </small>
          <small style={{ color: 'var(--muted)' }}>
            Active policy: retries {selectedConnector?.reliability_policy?.max_retries ?? 'n/a'}, backoff{' '}
            {selectedConnector?.reliability_policy?.base_backoff_ms ?? 'n/a'}ms
          </small>
        </article>
      </section>

      {error ? <p style={{ margin: 0, color: '#ef4444' }}>{error}</p> : null}

      <section style={{ border: '1px solid var(--line)', borderRadius: 12, padding: 12, background: 'var(--panel)' }}>
        <h2 style={{ marginTop: 0, fontSize: 18 }}>Last API Result</h2>
        <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(result, null, 2)}</pre>
      </section>
    </main>
  );
}
