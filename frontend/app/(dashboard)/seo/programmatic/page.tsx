'use client';

import { useMemo, useRef, useState, type FormEvent } from 'react';
import { Badge, Button, Card, CardTitle, Field, Page, PageHeader, TableWrap, tableClass } from '@/app/(dashboard)/_ui/kit';
import {
  buildProgrammaticPreview,
  PROGRAMMATIC_LIMITS,
  serializeProgrammaticCsv,
  validateProgrammaticDraft,
  type ProgrammaticDraftInput,
  type ProgrammaticPreviewResult,
} from './programmatic-model';
import styles from './programmatic.module.css';

type VariableRow = { id: string; key: string; valuesText: string };

type SuccessfulPreview = Extract<ProgrammaticPreviewResult, { ok: true }>;

function toDraftInput(
  templates: Pick<ProgrammaticDraftInput, 'urlTemplate' | 'titleTemplate' | 'metaDescriptionTemplate'>,
  variables: VariableRow[],
): ProgrammaticDraftInput {
  return {
    ...templates,
    variables: variables.map((variable) => ({
      key: variable.key,
      values: variable.valuesText.split(/\r?\n/).map((value) => value.trim()).filter(Boolean),
    })),
  };
}

export default function ProgrammaticPage() {
  const [templates, setTemplates] = useState({ urlTemplate: '', titleTemplate: '', metaDescriptionTemplate: '' });
  const [variables, setVariables] = useState<VariableRow[]>([{ id: 'variable-1', key: '', valuesText: '' }]);
  const nextVariableId = useRef(2);
  const [preview, setPreview] = useState<SuccessfulPreview | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [reviewConfirmed, setReviewConfirmed] = useState(false);
  const [attempted, setAttempted] = useState(false);
  const [filter, setFilter] = useState('');

  const draft = useMemo(() => toDraftInput(templates, variables), [templates, variables]);
  const validation = useMemo(() => validateProgrammaticDraft(draft), [draft]);

  function resetPreview() {
    setPreview(null);
    setShowAll(false);
    setReviewConfirmed(false);
    setAttempted(false);
    setFilter('');
  }

  function updateTemplate(key: keyof typeof templates, value: string) {
    setTemplates((current) => ({ ...current, [key]: value }));
    resetPreview();
  }

  function updateVariable(id: string, key: 'key' | 'valuesText', value: string) {
    setVariables((current) => current.map((variable) => variable.id === id ? { ...variable, [key]: value } : variable));
    resetPreview();
  }

  function addVariable() {
    if (variables.length >= PROGRAMMATIC_LIMITS.variables) return;
    const id = `variable-${nextVariableId.current++}`;
    setVariables((current) => [...current, { id, key: '', valuesText: '' }]);
    resetPreview();
  }

  function removeVariable(id: string) {
    setVariables((current) => current.filter((variable) => variable.id !== id));
    resetPreview();
  }

  function onPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAttempted(true);
    const result = buildProgrammaticPreview(draft);
    if (!result.ok) {
      setPreview(null);
      return;
    }
    setPreview(result);
    setShowAll(result.rows.length <= PROGRAMMATIC_LIMITS.sampleRows);
    setReviewConfirmed(false);
    setFilter('');
  }

  function exportReviewedCsv() {
    if (!preview || !showAll || !reviewConfirmed || preview.duplicatePathGroups > 0) return;
    const variableKeys = variables.map((variable) => variable.key.trim());
    const csv = serializeProgrammaticCsv(preview.rows, variableKeys);
    const objectUrl = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    anchor.download = 'programmatic-seo-draft-preview.csv';
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
  }

  const visibleRows = useMemo(() => {
    if (!preview) return [];
    const query = filter.trim().toLocaleLowerCase();
    const rows = preview.rows.slice(0, showAll ? undefined : PROGRAMMATIC_LIMITS.sampleRows);
    return query
      ? rows.filter((row) => `${row.path} ${row.title} ${row.metaDescription} ${Object.values(row.values).join(' ')}`.toLocaleLowerCase().includes(query))
      : rows;
  }, [filter, preview, showAll]);

  const countLabel = validation.pageCount === 0
    ? 'Not calculated'
    : validation.pageCount > PROGRAMMATIC_LIMITS.variants
      ? `More than ${PROGRAMMATIC_LIMITS.variants}`
      : validation.pageCount.toLocaleString();

  return (
    <Page className={`nxScope ${styles.page}`}>
      <PageHeader
        title="Programmatic SEO Draft Preview"
        subtitle="Expand user-supplied URL, title, and description templates into a small review set. This tool does not publish pages or assess search performance."
        actions={<Badge tone="brand">Browser-local</Badge>}
      />

      <aside className={styles.notice} aria-label="Local processing and scope">
        <strong>Nothing leaves this page.</strong> Templates and values stay in temporary page state and clear when you leave. No server request, saved record, traffic estimate, quality score, or publishing action is involved.
      </aside>

      <div className={styles.limitRow}>
        <p id="matrix-limit-help">Preview limit: {PROGRAMMATIC_LIMITS.variants} variants, {PROGRAMMATIC_LIMITS.variables} variables, and {PROGRAMMATIC_LIMITS.valuesPerVariable} values per variable.</p>
        <p className={styles.count} aria-live="polite"><span>Matrix size</span><strong>{countLabel}</strong></p>
      </div>

      <form onSubmit={onPreview} noValidate>
        <Card className={styles.formCard}>
          <div className={styles.sectionHeader}>
            <div>
              <span className={styles.step}>Step 1</span>
              <CardTitle>Templates</CardTitle>
            </div>
            <p>Use square-bracket tokens that exactly match a variable name, such as <code>[city]</code>.</p>
          </div>

          <div className={styles.templateGrid}>
            <Field
              id="programmatic-url-template"
              label="Relative URL path template"
              value={templates.urlTemplate}
              onChange={(event) => updateTemplate('urlTemplate', event.target.value)}
              placeholder="/areas/[city]/[service]"
              maxLength={PROGRAMMATIC_LIMITS.templateCharacters}
              aria-describedby="url-template-help matrix-limit-help"
            />
            <p className={styles.fieldHint} id="url-template-help">Must start with one slash. External URLs, query strings, and parent-directory segments are not accepted.</p>
            <Field
              id="programmatic-title-template"
              label="Page-title template"
              value={templates.titleTemplate}
              onChange={(event) => updateTemplate('titleTemplate', event.target.value)}
              placeholder="[service] in [city] | [brand]"
              maxLength={PROGRAMMATIC_LIMITS.templateCharacters}
            />
            <Field
              id="programmatic-description-template"
              label="Meta-description template"
              value={templates.metaDescriptionTemplate}
              onChange={(event) => updateTemplate('metaDescriptionTemplate', event.target.value)}
              placeholder="Describe what a reader will find in [city]."
              maxLength={PROGRAMMATIC_LIMITS.templateCharacters}
            />
          </div>

          <div className={styles.sectionHeader}>
            <div>
              <span className={styles.step}>Step 2</span>
              <CardTitle>Variable matrix</CardTitle>
            </div>
            <p>Enter only values you intend to review. One value per line.</p>
          </div>

          <div className={styles.variableList}>
            {variables.map((variable, index) => (
              <fieldset className={styles.variableRow} key={variable.id}>
                <legend>Variable {index + 1}</legend>
                <Field
                  id={`${variable.id}-key`}
                  label={`Token name ${index + 1}`}
                  value={variable.key}
                  onChange={(event) => updateVariable(variable.id, 'key', event.target.value)}
                  placeholder="city"
                  maxLength={40}
                  autoComplete="off"
                />
                <div className={styles.valuesField}>
                  <label htmlFor={`${variable.id}-values`}>Values for variable {index + 1} (one per line)</label>
                  <textarea
                    id={`${variable.id}-values`}
                    value={variable.valuesText}
                    onChange={(event) => updateVariable(variable.id, 'valuesText', event.target.value)}
                    rows={3}
                    maxLength={PROGRAMMATIC_LIMITS.valuesPerVariable * (PROGRAMMATIC_LIMITS.valueCharacters + 1)}
                    placeholder={'Austin\nBoston'}
                    aria-describedby="matrix-limit-help"
                  />
                </div>
                <Button
                  type="button"
                  variant="danger"
                  className={styles.removeButton}
                  onClick={() => removeVariable(variable.id)}
                  aria-label={`Remove variable ${index + 1}`}
                >
                  Remove
                </Button>
              </fieldset>
            ))}
          </div>

          <div className={styles.formActions}>
            <Button type="button" onClick={addVariable} disabled={variables.length >= PROGRAMMATIC_LIMITS.variables}>
              Add variable
            </Button>
            <Button type="submit" variant="primary">Preview variants</Button>
          </div>

          {attempted && validation.errors.length > 0 && (
            <div className={styles.validation} role="alert" aria-label="Template validation errors">
              <strong>Review the template before previewing.</strong>
              <ul>{validation.errors.map((error) => <li key={error}>{error}</li>)}</ul>
            </div>
          )}
        </Card>
      </form>

      {preview && (
        <section className={styles.previewSection} aria-labelledby="preview-heading">
          <Card className={styles.previewCard}>
            <div className={styles.previewHeader}>
              <div>
                <span className={styles.step}>Step 3</span>
                <h2 id="preview-heading">Draft variants</h2>
                <p role="status">{preview.pageCount} draft {preview.pageCount === 1 ? 'variant' : 'variants'} expanded locally from your matrix.</p>
              </div>
              {preview.pageCount > PROGRAMMATIC_LIMITS.sampleRows && !showAll && (
                <Button type="button" onClick={() => { setShowAll(true); setReviewConfirmed(false); }}>
                  Show all {preview.pageCount} variants for review
                </Button>
              )}
            </div>

            {preview.duplicatePathGroups > 0 && (
              <div className={styles.warning} role="alert">
                {preview.duplicatePathGroups} URL-path collision {preview.duplicatePathGroups === 1 ? 'group was' : 'groups were'} found. Nothing was deduplicated; edit the matrix before exporting.
              </div>
            )}

            {preview.pageCount > PROGRAMMATIC_LIMITS.sampleRows && !showAll && (
              <p className={styles.sampleNote}>Showing the first {PROGRAMMATIC_LIMITS.sampleRows} of {preview.pageCount}. Review the full set before export.</p>
            )}

            {(showAll || preview.pageCount <= PROGRAMMATIC_LIMITS.sampleRows) && preview.rows.length > 1 && (
              <Field
                id="programmatic-filter"
                label="Filter displayed draft variants"
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
                placeholder="Filter by path, title, description, or value"
              />
            )}

            {visibleRows.length === 0 ? (
              <p className={styles.empty}>No displayed variants match this filter. Clear it to review the draft set.</p>
            ) : (
              <TableWrap>
                <table className={tableClass}>
                  <caption className={styles.caption}>
                    {showAll || preview.pageCount <= PROGRAMMATIC_LIMITS.sampleRows
                      ? `All ${preview.pageCount} local draft variants`
                      : `Sample of ${visibleRows.length} from ${preview.pageCount} local draft variants`}
                  </caption>
                  <thead><tr><th scope="col">Path</th><th scope="col">Page title</th><th scope="col">Meta description</th><th scope="col">Values</th></tr></thead>
                  <tbody>
                    {visibleRows.map((row, index) => (
                      <tr key={`${row.path}-${index}`}>
                        <td className={styles.pathCell}>
                          <code>{row.path}</code>
                          {row.duplicatePath && <span className={styles.duplicate}>Duplicate path</span>}
                        </td>
                        <td>{row.title}</td>
                        <td>{row.metaDescription}</td>
                        <td>{Object.entries(row.values).map(([key, value]) => <span className={styles.valueChip} key={key}>{key}: {value}</span>)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
            )}

            <div className={styles.exportPanel}>
              <span className={styles.step}>Step 4</span>
              <p>Export is a local CSV of the exact draft rows above; it is not a content-quality review or a publish action.</p>
              <label className={styles.reviewCheck}>
                <input
                  type="checkbox"
                  checked={reviewConfirmed}
                  onChange={(event) => setReviewConfirmed(event.target.checked)}
                  disabled={!showAll || preview.duplicatePathGroups > 0}
                />
                I reviewed the complete draft set and understand these rows have not been published.
              </label>
              <Button
                type="button"
                variant="primary"
                onClick={exportReviewedCsv}
                disabled={!showAll || !reviewConfirmed || preview.duplicatePathGroups > 0}
              >
                Export reviewed CSV
              </Button>
            </div>
          </Card>
          <p className={styles.scopeNote}>This preview performs string substitution only. It does not verify demand, unique value, indexing eligibility, or cannibalization; validate content and routes before using any exported draft.</p>
        </section>
      )}
    </Page>
  );
}
