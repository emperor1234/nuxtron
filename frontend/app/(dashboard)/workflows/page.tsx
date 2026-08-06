'use client';

import { useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type Workflow = {
  id: number;
  name: string;
  status: string;
  trigger: { trigger_type: string };
  step_count: number;
  enrollment_count: number;
  execution_count: number;
};

type Execution = {
  id: number;
  contact_id: string;
  contact_email: string;
  status: string;
  steps_executed: number;
  completed_at: string;
};

type WorkflowTemplate = {
  id: number;
  name: string;
  category: string;
  trigger_type: string;
  tags: string[];
};

type CompletionFeature = {
  feature: string;
  implemented: boolean;
};

type CompletionChartPayload = {
  completion_pct: number;
  implemented_count: number;
  total_count: number;
  chart?: {
    features?: CompletionFeature[];
  };
  vendors?: Array<{ name: string; usage: string; integration: string }>;
};

export default function WorkflowsPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [name, setName] = useState('');
  const [triggerType, setTriggerType] = useState('manual');
  const [contactId, setContactId] = useState('demo-contact');
  const [contactEmail, setContactEmail] = useState('demo@example.com');
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [templateName, setTemplateName] = useState('Webhook Qualification Template');
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [graphStartStepId, setGraphStartStepId] = useState('s1');
  const [externalEventId, setExternalEventId] = useState('evt-demo-001');
  const [completion, setCompletion] = useState<CompletionChartPayload | null>(null);
  const [lastAction, setLastAction] = useState('');
  const [error, setError] = useState('');

  const defaultTemplateSteps = [
    {
      step_id: 's1',
      action_type: 'branch_condition',
      config: { field: 'plan', equals: 'pro' },
      branch_yes: 's2',
      branch_no: 's3',
    },
    {
      step_id: 's2',
      action_type: 'send_webhook',
      config: { url: 'https://example.invalid/hooks/pro' },
      branch_yes: '',
      branch_no: '',
    },
    {
      step_id: 's3',
      action_type: 'notify_rep',
      config: { channel: 'slack' },
      branch_yes: '',
      branch_no: '',
    },
  ];

  async function load() {
    try {
      setError('');
      const [res, templatesRes, completionRes] = await Promise.all([
        apiGet<{ workflows: Workflow[] }>('/workflows', tenantId),
        apiGet<{ templates: WorkflowTemplate[] }>('/workflows/templates', tenantId),
        apiGet<CompletionChartPayload>('/workflow-platform/completion-chart', tenantId),
      ]);
      setWorkflows(res.workflows ?? []);
      const templateItems = templatesRes.templates ?? [];
      setTemplates(templateItems);
      setCompletion(completionRes);
      if (selectedTemplateId === null && templateItems[0]?.id) {
        setSelectedTemplateId(templateItems[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load workflows');
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createWorkflow() {
    try {
      await apiSend(
        '/workflows',
        'POST',
        {
          name,
          description: 'Created from platform UI',
          trigger: { trigger_type: triggerType, conditions: [] },
          steps: [{ step_id: 'step-1', action_type: 'send_email', config: { template: 'welcome' } }],
        },
        tenantId
      );
      setName('');
      setLastAction('workflow_created');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  async function validateGraph() {
    try {
      setError('');
      const response = await apiSend<{ valid: boolean; step_count: number }>(
        '/workflows/validate-graph',
        'POST',
        {
          start_step_id: graphStartStepId,
          steps: defaultTemplateSteps,
        },
        tenantId
      );
      setLastAction(`graph_valid:${response.valid ? 'yes' : 'no'}:${response.step_count}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Graph validation failed');
    }
  }

  async function createTemplate() {
    try {
      setError('');
      const response = await apiSend<{ template: WorkflowTemplate }>(
        '/workflows/templates',
        'POST',
        {
          name: templateName,
          description: 'Created from Workflows UI template builder',
          category: 'lead_qualification',
          trigger_type: 'webhook',
          tags: ['workflow-ui', 'end-to-end'],
          steps: defaultTemplateSteps,
        },
        tenantId
      );
      setSelectedTemplateId(response.template.id);
      setLastAction(`template_created:${response.template.id}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Template create failed');
    }
  }

  async function instantiateTemplate() {
    if (selectedTemplateId === null) {
      setError('Select or create a template first.');
      return;
    }
    try {
      setError('');
      const response = await apiSend<{ workflow: Workflow }>(
        `/workflows/templates/${selectedTemplateId}/instantiate`,
        'POST',
        {
          name: `${templateName} Instance`,
          description: 'Instantiated from template via Workflows UI',
          trigger_conditions: [{ field: 'source', value: 'landing_page' }],
          re_enrollment: true,
          re_enrollment_days: 14,
        },
        tenantId
      );
      setLastAction(`template_instantiated:${response.workflow.id}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Template instantiate failed');
    }
  }

  async function triggerWebhook() {
    try {
      setError('');
      const response = await apiSend<{ executed: number; duplicate?: boolean }>(
        '/workflows/triggers/webhook',
        'POST',
        {
          event_type: 'webhook',
          external_event_id: externalEventId,
          payload: {
            source: 'landing_page',
            plan: 'pro',
            contact_id: contactId,
            contact_email: contactEmail,
          },
        },
        tenantId
      );
      setLastAction(`webhook_executed:${response.executed}:duplicate:${response.duplicate ? 'yes' : 'no'}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Webhook trigger failed');
    }
  }

  async function toggleWorkflow(id: number, active: boolean) {
    try {
      await apiSend(`/workflows/${id}/toggle?active=${active ? 'true' : 'false'}`, 'PATCH', undefined, tenantId);
      setLastAction(`workflow_toggled:${id}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Toggle failed');
    }
  }

  async function enroll(id: number) {
    try {
      await apiSend(
        `/workflows/${id}/enroll`,
        'POST',
        { contact_id: contactId, contact_email: contactEmail },
        tenantId
      );
      await loadExecutions(id);
      setLastAction(`workflow_enrolled:${id}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Enroll failed');
    }
  }

  async function loadExecutions(id: number) {
    try {
      setSelectedId(id);
      const res = await apiGet<{ executions: Execution[] }>(`/workflows/${id}/executions`, tenantId);
      setExecutions(res.executions ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Execution load failed');
    }
  }

  const card = { background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 };
  const input = {
    width: '100%',
    padding: '8px 10px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    marginBottom: 8,
  };

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <h1 style={{ marginTop: 0 }}>Workflows Automation</h1>
        <p style={{ color: 'var(--muted)' }}>
          Create and execute multi-step automations with trigger-based enrollment.
        </p>
        {error && <div style={{ ...card, color: '#f87171', marginBottom: 10 }}>{error}</div>}
        {lastAction && (
          <div style={{ ...card, color: 'var(--muted)', marginBottom: 10 }}>Last action: {lastAction}</div>
        )}

        <section style={{ ...card, marginBottom: 10 }}>
          <h3 style={{ marginTop: 0 }}>Production Completion Chart</h3>
          <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 8 }}>
            Implemented {completion?.implemented_count ?? 0}/{completion?.total_count ?? 0} features (
            {completion?.completion_pct ?? 0}%)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 8 }}>
            {(completion?.chart?.features ?? []).map((item) => (
              <div key={item.feature} style={{ border: '1px solid var(--line)', borderRadius: 8, padding: '6px 8px' }}>
                <strong>{item.implemented ? 'Done' : 'Pending'}</strong> · {item.feature}
              </div>
            ))}
          </div>
          <div style={{ marginTop: 8, color: 'var(--muted)', fontSize: 12 }}>
            Vendors: {(completion?.vendors ?? []).map((vendor) => vendor.name).join(', ')}
          </div>
        </section>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 10 }}>
          <section style={card}>
            <h3 style={{ marginTop: 0 }}>Create Workflow</h3>
            <input style={input} value={name} onChange={(e) => setName(e.target.value)} placeholder="Workflow name" />
            <select style={input} value={triggerType} onChange={(e) => setTriggerType(e.target.value)}>
              <option value="manual">manual</option>
              <option value="contact_created">contact_created</option>
              <option value="deal_stage_changed">deal_stage_changed</option>
              <option value="form_submitted">form_submitted</option>
            </select>
            <button
              onClick={() => void createWorkflow()}
              style={{
                padding: '8px 12px',
                border: 'none',
                borderRadius: 8,
                background: 'var(--brand)',
                color: '#00101e',
                fontWeight: 700,
              }}
            >
              Create
            </button>

            <h4 style={{ marginBottom: 6 }}>Template + Validation + Webhook</h4>
            <input
              style={input}
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              placeholder="template name"
            />
            <input
              style={input}
              value={graphStartStepId}
              onChange={(e) => setGraphStartStepId(e.target.value)}
              placeholder="graph start step id"
            />
            <select
              style={input}
              value={selectedTemplateId === null ? '' : String(selectedTemplateId)}
              onChange={(e) => setSelectedTemplateId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Select template</option>
              {templates.map((template) => (
                <option key={template.id} value={template.id}>
                  #{template.id} {template.name}
                </option>
              ))}
            </select>
            <input
              style={input}
              value={externalEventId}
              onChange={(e) => setExternalEventId(e.target.value)}
              placeholder="external event id"
            />
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
              <button
                onClick={() => void validateGraph()}
                style={{
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  background: 'transparent',
                  color: 'var(--text)',
                  padding: '4px 8px',
                }}
              >
                Validate Graph
              </button>
              <button
                onClick={() => void createTemplate()}
                style={{
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  background: 'transparent',
                  color: 'var(--text)',
                  padding: '4px 8px',
                }}
              >
                Create Template
              </button>
              <button
                onClick={() => void instantiateTemplate()}
                style={{
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  background: 'transparent',
                  color: 'var(--text)',
                  padding: '4px 8px',
                }}
              >
                Instantiate
              </button>
              <button
                onClick={() => void triggerWebhook()}
                style={{
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  background: 'transparent',
                  color: 'var(--text)',
                  padding: '4px 8px',
                }}
              >
                Trigger Webhook
              </button>
            </div>

            <h4 style={{ marginBottom: 6 }}>Manual Enrollment</h4>
            <input
              style={input}
              value={contactId}
              onChange={(e) => setContactId(e.target.value)}
              placeholder="contact id"
            />
            <input
              style={input}
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              placeholder="contact email"
            />
          </section>

          <section style={card}>
            <h3 style={{ marginTop: 0 }}>Workflows ({workflows.length})</h3>
            {workflows.map((w) => (
              <div key={w.id} style={{ borderBottom: '1px solid var(--line)', padding: '8px 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{w.name}</div>
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                      Trigger: {w.trigger?.trigger_type} · Steps: {w.step_count}
                    </div>
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                      Enrollments: {w.enrollment_count} · Executions: {w.execution_count}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'start' }}>
                    <button
                      onClick={() => void toggleWorkflow(w.id, w.status !== 'active')}
                      style={{
                        border: '1px solid var(--line)',
                        borderRadius: 8,
                        background: 'transparent',
                        color: 'var(--text)',
                        padding: '4px 8px',
                      }}
                    >
                      {w.status === 'active' ? 'Pause' : 'Activate'}
                    </button>
                    <button
                      onClick={() => void enroll(w.id)}
                      style={{
                        border: 'none',
                        borderRadius: 8,
                        background: 'var(--brand)',
                        color: '#00101e',
                        padding: '4px 8px',
                        fontWeight: 700,
                      }}
                    >
                      Enroll
                    </button>
                    <button
                      onClick={() => void loadExecutions(w.id)}
                      style={{
                        border: '1px solid var(--line)',
                        borderRadius: 8,
                        background: 'transparent',
                        color: 'var(--text)',
                        padding: '4px 8px',
                      }}
                    >
                      Executions
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </section>
        </div>

        {selectedId !== null && (
          <section style={{ ...card, marginTop: 10 }}>
            <h3 style={{ marginTop: 0 }}>Executions for Workflow #{selectedId}</h3>
            {executions.map((ex) => (
              <div key={ex.id} style={{ borderBottom: '1px solid var(--line)', padding: '8px 0' }}>
                <div style={{ fontWeight: 700 }}>
                  {ex.contact_email || ex.contact_id} · {ex.status}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                  Steps: {ex.steps_executed} · Completed: {new Date(ex.completed_at).toLocaleString()}
                </div>
              </div>
            ))}
          </section>
        )}
      </div>
    </main>
  );
}
