'use client';

import { useState, type FormEvent } from 'react';
import { Badge, Button, Card, CardTitle, Page, PageHeader, Stat, StatGrid } from '../../_ui/kit';
import { buildEntityGraphDraft, entityGraphDraftCsv, type EntityGraphDraft } from './entity-graph-model';
import styles from './entity-graph.module.css';

export default function KnowledgeGraphPage() {
  const [context, setContext] = useState('');
  const [entityInput, setEntityInput] = useState('');
  const [relationshipInput, setRelationshipInput] = useState('');
  const [draft, setDraft] = useState<EntityGraphDraft | null>(null);
  const [error, setError] = useState('');

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setDraft(null);
    try {
      setDraft(buildEntityGraphDraft(entityInput, relationshipInput));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not build this outline.');
    }
  }

  function exportDraft() {
    if (!draft || draft.relationships.length === 0) return;
    const blob = new Blob([entityGraphDraftCsv(draft)], { type: 'text/csv;charset=utf-8' });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = href;
    anchor.download = 'entity-relationship-outline.csv';
    anchor.click();
    URL.revokeObjectURL(href);
  }

  return (
    <Page>
      <PageHeader
        title="Entity Graph Planner"
        subtitle="Draft an entity and relationship outline from information you provide."
      />

      <Card className={styles.scopeNotice}>
        <Badge tone="brand">Local outline</Badge>
        <p>
          This page does not query Google, Wikidata, your site, or an external graph service. It does not infer facts, calculate live graph health, or publish structured data.
        </p>
      </Card>

      <Card>
        <CardTitle sub="List entities and optional relationships. Counts and unlinked status are calculated only from this draft.">
          Build your outline
        </CardTitle>
        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.field} htmlFor="entity-context">
            <span>Project or site label <em>Optional</em></span>
            <input
              id="entity-context"
              value={context}
              maxLength={200}
              onChange={(event) => setContext(event.target.value)}
              placeholder="A name to help identify this draft"
            />
          </label>
          <div className={styles.inputGrid}>
            <label className={styles.field} htmlFor="entity-list">
              <span>Entities <em>Required · one per line</em></span>
              <textarea
                id="entity-list"
                rows={8}
                value={entityInput}
                onChange={(event) => setEntityInput(event.target.value)}
                placeholder={'Organization\nProduct\nTopic or person'}
                required
              />
              <small>Up to 100 entries. Duplicate names are counted once, case-insensitively.</small>
            </label>
            <label className={styles.field} htmlFor="relationship-list">
              <span>Relationships <em>Optional · one per line</em></span>
              <textarea
                id="relationship-list"
                rows={8}
                className={styles.mono}
                value={relationshipInput}
                onChange={(event) => setRelationshipInput(event.target.value)}
                placeholder={'Organization | offers | Product\nProduct | relates to | Topic'}
              />
              <small>Format: source entity | relationship | target entity. Endpoints must match your entity list.</small>
            </label>
          </div>
          {error && <p role="alert" className={styles.error}>{error}</p>}
          <Button type="submit" variant="primary">Build local outline</Button>
        </form>
      </Card>

      {draft && (
        <section className={styles.results} aria-label="Entity outline results">
          <Card className={styles.resultHeader}>
            <div>
              <CardTitle sub={context.trim() ? `Draft: ${context.trim()}` : 'Draft based on the entities and relationships you entered.'}>
                Outline summary
              </CardTitle>
            </div>
            <Button type="button" onClick={exportDraft} disabled={draft.relationships.length === 0}>
              Export relationship list
            </Button>
          </Card>

          <StatGrid>
            <Stat label="Distinct entities" value={draft.entities.length} hint={`${draft.duplicateEntityCount} duplicate entries`} />
            <Stat label="Explicit relationships" value={draft.relationships.length} hint={`${draft.duplicateRelationshipCount} duplicate rows`} />
            <Stat label="Connected entities" value={draft.linkedEntityCount} hint="In this outline only" />
            <Stat label="Unlinked in draft" value={draft.unlinkedEntities.length} hint={`${draft.connectionCoveragePct}% connected within entered list`} />
          </StatGrid>

          <Card>
            <CardTitle sub="“Unlinked” means no relationship row was entered for this entity; it does not describe your live website or search graph.">
              Entities in this outline
            </CardTitle>
            <div className={styles.entityList}>
              {draft.entities.map((entity) => (
                <article className={styles.entity} key={entity.name}>
                  <div className={styles.entityHeader}>
                    <strong>{entity.name}</strong>
                    <Badge tone={entity.relationshipCount > 0 ? 'success' : 'neutral'}>
                      {entity.relationshipCount > 0 ? 'Linked in draft' : 'Unlinked in draft'}
                    </Badge>
                  </div>
                  <span className={styles.entityMeta}>{entity.relationshipCount} explicit relationship{entity.relationshipCount === 1 ? '' : 's'}</span>
                </article>
              ))}
            </div>
          </Card>

          <Card>
            <CardTitle sub="Only relationships you entered are shown; no links are inferred.">Relationship rows</CardTitle>
            {draft.relationships.length === 0 ? (
              <p className={styles.empty}>No relationships were entered. All listed entities are currently unlinked in this draft.</p>
            ) : (
              <ul className={styles.relationshipList}>
                {draft.relationships.map((relationship, index) => (
                  <li key={`${relationship.from}-${relationship.type}-${relationship.to}-${index}`}>
                    <span>{relationship.from}</span>
                    <b>{relationship.type}</b>
                    <span>{relationship.to}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <p className={styles.limitNote}>Local draft only. No page crawling, knowledge-graph lookup, rank measurement, or schema publishing occurs.</p>
        </section>
      )}
    </Page>
  );
}
