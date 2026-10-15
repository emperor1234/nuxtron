'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Badge, Button, Card, CardTitle, Field, Page, PageHeader } from '@/app/(dashboard)/_ui/kit';
import { resolveSessionTenant } from '@/app/lib/api-client';
import { apiSend } from '@/app/lib/platform-api';
import { parseSeoPlannerDraft, type SeoPlannerDraft } from './planner-model';
import styles from './seo-planner.module.css';

function formatCreatedAt(value: string | null): string | null {
  if (!value) return null;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

export default function SEOPlannerPage() {
  const [goal, setGoal] = useState('');
  const [domain, setDomain] = useState('');
  const [primaryKeyword, setPrimaryKeyword] = useState('');
  const [market, setMarket] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [draft, setDraft] = useState<SeoPlannerDraft | null>(null);
  const errorRef = useRef<HTMLDivElement>(null);
  const draftRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (error) errorRef.current?.focus();
  }, [error]);

  useEffect(() => {
    if (draft) draftRef.current?.focus();
  }, [draft]);

  async function createDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setDraft(null);

    const workspaceId = resolveSessionTenant();
    if (!workspaceId) {
      setError('A signed-in workspace is required to create a plan. Sign in or select a workspace, then try again.');
      return;
    }
    if (goal.trim().length < 5) {
      setError('Enter a goal of at least five characters before creating a draft.');
      return;
    }

    setLoading(true);
    try {
      const response = await apiSend<unknown>(
        '/seo-platform/planner/draft',
        'POST',
        {
          goal: goal.trim(),
          domain: domain.trim(),
          primary_keyword: primaryKeyword.trim(),
          market: market.trim(),
        },
        workspaceId,
        { cache: false },
      );
      const parsed = parseSeoPlannerDraft(response);
      if (!parsed) throw new Error('The planner returned an unsupported response.');
      setDraft(parsed);
    } catch {
      setError('The draft could not be created right now. Your brief did not trigger any SEO work; try again later.');
    } finally {
      setLoading(false);
    }
  }

  const createdAt = formatCreatedAt(draft?.createdAt ?? null);

  return (
    <Page className={styles.page}>
      <PageHeader
        title="SEO Workflow Planner"
        subtitle="Create a reviewable draft from your brief. This page does not inspect live site data or execute work."
      />

      <div className={styles.columns}>
        <Card className={styles.formCard}>
          <CardTitle
            sub="Describe the outcome you want. Optional context helps frame suggestions, but it is not verified against your site."
          >
            Start with your goal
          </CardTitle>
          <form className={styles.form} onSubmit={createDraft}>
            <div className={styles.goalField}>
              <label className={styles.label} htmlFor="planner-goal">
                Goal <span className={styles.required}>Required</span>
              </label>
              <textarea
                id="planner-goal"
                className={styles.textarea}
                value={goal}
                onChange={(event) => setGoal(event.target.value)}
                minLength={5}
                maxLength={1000}
                required
                rows={4}
                aria-describedby="planner-goal-help"
                placeholder="Describe the outcome you want to work toward"
              />
              <p className={styles.fieldHint} id="planner-goal-help">
                Keep it specific enough to review; do not include passwords, access tokens, or private customer data.
              </p>
            </div>

            <div className={styles.fieldGrid}>
              <Field
                id="planner-domain"
                label="Website or domain"
                value={domain}
                onChange={(event) => setDomain(event.target.value)}
                maxLength={200}
                placeholder="Optional"
                autoComplete="url"
              />
              <Field
                id="planner-keyword"
                label="Primary topic or keyword"
                value={primaryKeyword}
                onChange={(event) => setPrimaryKeyword(event.target.value)}
                maxLength={200}
                placeholder="Optional"
              />
              <Field
                id="planner-market"
                label="Market or location"
                value={market}
                onChange={(event) => setMarket(event.target.value)}
                maxLength={200}
                placeholder="Optional"
              />
            </div>

            <div className={styles.formFooter}>
              <p className={styles.scopeHint}>Workspace scope comes from your signed-in session; no tenant ID is entered here.</p>
              <Button type="submit" variant="primary" disabled={loading}>
                {loading ? 'Creating draft…' : 'Create draft plan'}
              </Button>
            </div>
          </form>
        </Card>

        <Card className={styles.guidanceCard}>
          <div className={styles.guidanceHeader}>
            <Badge tone="brand">Draft only</Badge>
            <h2>Review before acting</h2>
          </div>
          <p className={styles.guidanceLead}>
            The planner uses only the goal and optional context you provide. Recommendations are not findings about your site.
          </p>
          <ul className={styles.guidanceList}>
            <li>No rankings, analytics, crawl logs, or competitor sources are queried.</li>
            <li>Suggested steps link to separate tools for your review.</li>
            <li>No publishing, settings changes, campaign launches, or background jobs are triggered.</li>
          </ul>
        </Card>
      </div>

      <div className={styles.liveStatus} role="status" aria-live="polite" aria-atomic="true">
        {loading ? 'Creating a review-only draft from your brief.' : ''}
      </div>

      {error && (
        <div ref={errorRef} className={styles.error} role="alert" tabIndex={-1}>
          <strong>Draft not created</strong>
          <span>{error}</span>
        </div>
      )}

      {loading && (
        <Card className={styles.loadingCard}>
          <span className={styles.loadingMark} aria-hidden="true" />
          <span>Preparing a draft from your brief…</span>
        </Card>
      )}

      {!draft && !loading && !error && (
        <Card className={styles.emptyCard}>
          <p className={styles.eyebrow}>Your plan</p>
          <p>Your reviewable draft will appear here after you submit a goal.</p>
        </Card>
      )}

      {draft && (
        <section ref={draftRef} className={styles.results} aria-label="Draft plan" tabIndex={-1}>
          <Card className={styles.resultHeader}>
            <div className={styles.resultTitleBlock}>
              <p className={styles.eyebrow}>SEO workflow draft</p>
              <h2>{draft.goal}</h2>
              <div className={styles.badges}>
                <Badge tone="brand">Draft only</Badge>
                <Badge>{draft.analysisMode === 'llm' ? 'AI-assisted from brief' : 'Template suggestions'}</Badge>
                {draft.cached ? <Badge>Previously generated draft</Badge> : null}
              </div>
            </div>
            {createdAt ? <p className={styles.timestamp}>Created {createdAt}</p> : null}
          </Card>

          <Card className={styles.provenance}>
            <strong>What this draft is based on</strong>
            <p>
              {draft.analysisMode === 'llm'
                ? 'Generated from the information you submitted only. No live rankings, analytics, crawl data, or competitor sources were checked.'
                : 'Template suggestions based on your brief. No AI model or connected site data was used.'}
            </p>
            <p>Review each suggestion against current evidence. Nothing is executed from this page.</p>
            <p>
              Created drafts are saved to this workspace&apos;s SEO Analysis History. Open history to review the available persistence status.
            </p>
            <a href="/seo/history" className={styles.historyLink}>Open Analysis History</a>
          </Card>

          {(draft.domain || draft.primaryKeyword || draft.market) && (
            <Card className={styles.scopeCard}>
              <CardTitle>Brief context</CardTitle>
              <dl className={styles.scopeList}>
                {draft.domain ? <div><dt>Website or domain</dt><dd>{draft.domain}</dd></div> : null}
                {draft.primaryKeyword ? <div><dt>Primary topic or keyword</dt><dd>{draft.primaryKeyword}</dd></div> : null}
                {draft.market ? <div><dt>Market or location</dt><dd>{draft.market}</dd></div> : null}
              </dl>
            </Card>
          )}

          <div className={styles.resultGrid}>
            <Card className={styles.workflowCard}>
              <CardTitle sub="A generic sequence to review and adapt; these steps have not been run.">Suggested sequence</CardTitle>
              {draft.workflow.length ? (
                <ol className={styles.workflowList}>
                  {draft.workflow.map((step, index) => (
                    <li className={styles.workflowStep} key={`${step.phase}-${index}`}>
                      <span className={styles.stepNumber} aria-hidden="true">{index + 1}</span>
                      <div className={styles.stepBody}>
                        <p className={styles.stepPhase}>{step.phase}</p>
                        <h3>{step.module}</h3>
                        <p>{step.action}</p>
                        {step.path ? <a href={step.path} className={styles.stepLink}>Open tool</a> : null}
                      </div>
                    </li>
                  ))}
                </ol>
              ) : <p className={styles.noItems}>No sequence was returned for this draft.</p>}
            </Card>

            <div className={styles.insightColumn}>
              <Card>
                <CardTitle sub="Suggestions from the submitted brief—not verified priorities.">Draft priorities</CardTitle>
                {draft.priorities.length ? (
                  <ol className={styles.textList}>
                    {draft.priorities.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                  </ol>
                ) : <p className={styles.noItems}>No priorities were returned.</p>}
              </Card>
              <Card>
                <CardTitle sub="Potential issues to check against current evidence.">Potential risks</CardTitle>
                {draft.risks.length ? (
                  <ul className={styles.textList}>
                    {draft.risks.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                  </ul>
                ) : <p className={styles.noItems}>No potential risks were returned.</p>}
              </Card>
              <Card>
                <CardTitle sub="Human-owned follow-up; no action is started here.">Next actions</CardTitle>
                {draft.nextActions.length ? (
                  <ol className={styles.textList}>
                    {draft.nextActions.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                  </ol>
                ) : <p className={styles.noItems}>No next actions were returned.</p>}
              </Card>
            </div>
          </div>
        </section>
      )}
    </Page>
  );
}
