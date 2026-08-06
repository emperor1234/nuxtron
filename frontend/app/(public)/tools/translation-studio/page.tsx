'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { apiGet, apiPost, PROXY_BASE_URL } from '@/app/lib/api-client';

type LanguageItem = {
  language: string;
  name: string;
  supports_formality: boolean;
};

type GlossaryItem = {
  id: string;
  name: string;
  source_lang: string;
  target_lang: string;
  deepl_glossary_id?: string | null;
};

type TranslationMemoryItem = {
  id: string;
  name: string;
  source_lang: string;
  target_lang: string;
  description?: string | null;
  deepl_translation_memory_id?: string | null;
};

type TranslationRecord = {
  detected_source_language?: string;
  text: string;
};

export default function TranslationStudioPage() {
  const [sourceLanguages, setSourceLanguages] = useState<LanguageItem[]>([]);
  const [targetLanguages, setTargetLanguages] = useState<LanguageItem[]>([]);
  const [glossaries, setGlossaries] = useState<GlossaryItem[]>([]);
  const [translationMemories, setTranslationMemories] = useState<TranslationMemoryItem[]>([]);

  const [sourceLang, setSourceLang] = useState('');
  const [targetLang, setTargetLang] = useState('DE');
  const [formality, setFormality] = useState('default');
  const [preserveFormatting, setPreserveFormatting] = useState(false);
  const [modelType, setModelType] = useState('');
  const [splitSentences, setSplitSentences] = useState('');
  const [tagHandling, setTagHandling] = useState('');
  const [tagHandlingVersion, setTagHandlingVersion] = useState('');
  const [outlineDetection, setOutlineDetection] = useState('');
  const [nonSplittingTags, setNonSplittingTags] = useState('');
  const [splittingTags, setSplittingTags] = useState('');
  const [ignoreTags, setIgnoreTags] = useState('');
  const [styleId, setStyleId] = useState('');
  const [customInstructionsText, setCustomInstructionsText] = useState('');
  const [translationMemoryId, setTranslationMemoryId] = useState('');
  const [translationMemoryThreshold, setTranslationMemoryThreshold] = useState('');
  const [context, setContext] = useState('');
  const [selectedGlossaryId, setSelectedGlossaryId] = useState('');
  const [textInput, setTextInput] = useState('Hello world');

  const [creatingGlossary, setCreatingGlossary] = useState(false);
  const [newGlossaryName, setNewGlossaryName] = useState('Brand Terms');
  const [newGlossarySource, setNewGlossarySource] = useState('EN');
  const [newGlossaryTarget, setNewGlossaryTarget] = useState('DE');
  const [newGlossaryEntries, setNewGlossaryEntries] = useState('Nuxtron\tNuxtron\nagent\tAgent');
  const [newGlossaryDeepLId, setNewGlossaryDeepLId] = useState('');

  const [creatingMemory, setCreatingMemory] = useState(false);
  const [newMemoryName, setNewMemoryName] = useState('Product Support Memory');
  const [newMemorySource, setNewMemorySource] = useState('EN');
  const [newMemoryTarget, setNewMemoryTarget] = useState('DE');
  const [newMemoryDescription, setNewMemoryDescription] = useState('Terminology and phrasing for support docs');
  const [newMemoryDeepLId, setNewMemoryDeepLId] = useState('');

  const [translating, setTranslating] = useState(false);
  const [translations, setTranslations] = useState<TranslationRecord[]>([]);
  const [providerUsed, setProviderUsed] = useState('');
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [billedChars, setBilledChars] = useState<number | null>(null);

  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentBusy, setDocumentBusy] = useState(false);
  const [documentResult, setDocumentResult] = useState<string>('');

  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [vendors, setVendors] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');

  const cardStyle: React.CSSProperties = useMemo(
    () => ({ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 14, padding: 16 }),
    []
  );

  async function loadBootstrapData() {
    setError('');
    try {
      const [languages, glossaryData, memoryData, healthData, vendorData] = await Promise.all([
        apiGet('/translations/languages'),
        apiGet('/translations/glossaries'),
        apiGet('/translations/translation-memories'),
        apiGet('/translations/health'),
        apiGet('/translations/vendors'),
      ]);

      setSourceLanguages((languages.source as LanguageItem[]) || []);
      setTargetLanguages((languages.target as LanguageItem[]) || []);
      setGlossaries((glossaryData.items as GlossaryItem[]) || []);
      setTranslationMemories((memoryData.items as TranslationMemoryItem[]) || []);
      setHealth(healthData);
      setVendors(vendorData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load translation studio data');
    }
  }

  useEffect(() => {
    void loadBootstrapData();
  }, []);

  async function onTranslateText(event: FormEvent) {
    event.preventDefault();
    setError('');
    setTranslating(true);
    setTranslations([]);

    try {
      const payload: Record<string, unknown> = {
        texts: textInput
          .split('\n')
          .map((line) => line.trim())
          .filter(Boolean),
        target_lang: targetLang,
        source_lang: sourceLang || undefined,
        context: context || undefined,
        formality,
        preserve_formatting: preserveFormatting,
        model_type: modelType || undefined,
        split_sentences: splitSentences || undefined,
        tag_handling: tagHandling || undefined,
        tag_handling_version: tagHandlingVersion || undefined,
        outline_detection: outlineDetection === 'true' ? true : outlineDetection === 'false' ? false : undefined,
        non_splitting_tags: nonSplittingTags
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
        splitting_tags: splittingTags
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
        ignore_tags: ignoreTags
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
        style_id: styleId || undefined,
        custom_instructions: customInstructionsText
          .split('\n')
          .map((item) => item.trim())
          .filter(Boolean),
        translation_memory_id: translationMemoryId || undefined,
        translation_memory_threshold: translationMemoryThreshold ? Number(translationMemoryThreshold) : undefined,
        glossary_id: selectedGlossaryId || undefined,
        provider: 'auto',
      };

      const response = await apiPost('/translations/text', payload);
      setProviderUsed(String(response.provider_used || ''));
      setLatencyMs(Number(response.latency_ms || 0));
      setBilledChars(Number(response.billed_characters || 0));
      setTranslations((response.translations as TranslationRecord[]) || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Text translation failed');
    } finally {
      setTranslating(false);
    }
  }

  async function onCreateGlossary(event: FormEvent) {
    event.preventDefault();
    setError('');
    setCreatingGlossary(true);
    try {
      const entries: Record<string, string> = {};
      for (const row of newGlossaryEntries.split('\n')) {
        const [source, target] = row.split('\t');
        const sourceTerm = (source || '').trim();
        const targetTerm = (target || '').trim();
        if (sourceTerm && targetTerm) {
          entries[sourceTerm] = targetTerm;
        }
      }

      await apiPost('/translations/glossaries', {
        name: newGlossaryName,
        source_lang: newGlossarySource,
        target_lang: newGlossaryTarget,
        entries,
        deepl_glossary_id: newGlossaryDeepLId || undefined,
      });

      await loadBootstrapData();
      setNewGlossaryEntries('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create glossary');
    } finally {
      setCreatingGlossary(false);
    }
  }

  async function onCreateTranslationMemory(event: FormEvent) {
    event.preventDefault();
    setError('');
    setCreatingMemory(true);
    try {
      const created = await apiPost('/translations/translation-memories', {
        name: newMemoryName,
        source_lang: newMemorySource,
        target_lang: newMemoryTarget,
        description: newMemoryDescription || undefined,
        deepl_translation_memory_id: newMemoryDeepLId || undefined,
      });

      await loadBootstrapData();
      setTranslationMemoryId(String(created.id || ''));
      setNewMemoryDeepLId('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create translation memory');
    } finally {
      setCreatingMemory(false);
    }
  }

  async function onTranslateDocument(event: FormEvent) {
    event.preventDefault();
    if (!documentFile) {
      setError('Please select a document first');
      return;
    }

    setError('');
    setDocumentBusy(true);
    setDocumentResult('');

    try {
      const formData = new FormData();
      formData.append('file', documentFile);
      formData.append('target_lang', targetLang);
      if (sourceLang) formData.append('source_lang', sourceLang);
      if (formality) formData.append('formality', formality);
      if (selectedGlossaryId) formData.append('glossary_id', selectedGlossaryId);

      const response = await fetch(`${PROXY_BASE_URL}/translations/documents`, {
        method: 'POST',
        body: formData,
        cache: 'no-store',
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(String(data?.detail || 'Document translation failed'));
      }

      setDocumentResult(
        `Provider: ${String(data.provider_used || '')}\nLatency: ${String(data.latency_ms || '')} ms\nOutput bytes: ${String(
          data.output_size_bytes || ''
        )}\nBilled characters: ${String(data.billed_characters || '')}`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Document translation failed');
    } finally {
      setDocumentBusy(false);
    }
  }

  return (
    <main>
      <section className="hero" style={{ marginBottom: 16 }}>
        <p className="eyebrow">Translation Studio</p>
        <h1>DeepL-style translation workflow, wired end-to-end</h1>
        <p>
          This page uses live backend vendor calls only. If vendor keys are missing, requests fail explicitly instead of
          using mock translations.
        </p>
      </section>

      {error ? (
        <section style={{ ...cardStyle, borderColor: '#ef4444', color: '#fecaca', marginBottom: 12 }}>{error}</section>
      ) : null}

      <section className="grid" style={{ marginTop: 0 }}>
        <article style={cardStyle}>
          <h3>Live vendor status</h3>
          <pre>{JSON.stringify(vendors || {}, null, 2)}</pre>
          <h3 style={{ marginTop: 12 }}>Health</h3>
          <pre>{JSON.stringify(health || {}, null, 2)}</pre>
        </article>

        <article style={cardStyle}>
          <h3>Language settings</h3>
          <label>Source language (optional)</label>
          <select value={sourceLang} onChange={(e) => setSourceLang(e.target.value)}>
            <option value="">Auto detect</option>
            {sourceLanguages.map((item) => (
              <option key={item.language} value={item.language}>
                {item.name} ({item.language})
              </option>
            ))}
          </select>

          <label style={{ marginTop: 8 }}>Target language</label>
          <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)}>
            {targetLanguages.map((item) => (
              <option key={item.language} value={item.language}>
                {item.name} ({item.language})
              </option>
            ))}
          </select>

          <label style={{ marginTop: 8 }}>Formality</label>
          <select value={formality} onChange={(e) => setFormality(e.target.value)}>
            <option value="default">default</option>
            <option value="more">more formal</option>
            <option value="less">less formal</option>
            <option value="prefer_more">prefer more</option>
            <option value="prefer_less">prefer less</option>
          </select>

          <label style={{ marginTop: 8 }}>Glossary</label>
          <select value={selectedGlossaryId} onChange={(e) => setSelectedGlossaryId(e.target.value)}>
            <option value="">None</option>
            {glossaries.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} ({item.source_lang}-{item.target_lang})
              </option>
            ))}
          </select>

          <label style={{ marginTop: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={preserveFormatting}
              onChange={(e) => setPreserveFormatting(e.target.checked)}
            />
            Preserve formatting
          </label>

          <label style={{ marginTop: 8 }}>Model type</label>
          <select value={modelType} onChange={(e) => setModelType(e.target.value)}>
            <option value="">default</option>
            <option value="latency_optimized">latency_optimized</option>
            <option value="quality_optimized">quality_optimized</option>
            <option value="prefer_quality_optimized">prefer_quality_optimized</option>
          </select>

          <label style={{ marginTop: 8 }}>Split sentences</label>
          <select value={splitSentences} onChange={(e) => setSplitSentences(e.target.value)}>
            <option value="">default</option>
            <option value="0">0</option>
            <option value="1">1</option>
            <option value="nonewlines">nonewlines</option>
          </select>

          <label style={{ marginTop: 8 }}>Tag handling</label>
          <select value={tagHandling} onChange={(e) => setTagHandling(e.target.value)}>
            <option value="">none</option>
            <option value="html">html</option>
            <option value="xml">xml</option>
          </select>

          <label style={{ marginTop: 8 }}>Tag handling version</label>
          <select value={tagHandlingVersion} onChange={(e) => setTagHandlingVersion(e.target.value)}>
            <option value="">default</option>
            <option value="v1">v1</option>
            <option value="v2">v2</option>
          </select>

          <label style={{ marginTop: 8 }}>Outline detection</label>
          <select value={outlineDetection} onChange={(e) => setOutlineDetection(e.target.value)}>
            <option value="">default</option>
            <option value="true">true</option>
            <option value="false">false</option>
          </select>

          <label style={{ marginTop: 8 }}>Non splitting tags (comma separated)</label>
          <input value={nonSplittingTags} onChange={(e) => setNonSplittingTags(e.target.value)} />

          <label style={{ marginTop: 8 }}>Splitting tags (comma separated)</label>
          <input value={splittingTags} onChange={(e) => setSplittingTags(e.target.value)} />

          <label style={{ marginTop: 8 }}>Ignore tags (comma separated)</label>
          <input value={ignoreTags} onChange={(e) => setIgnoreTags(e.target.value)} />
        </article>
      </section>

      <section className="grid">
        <article style={cardStyle}>
          <h3>Text translation</h3>
          <form onSubmit={onTranslateText}>
            <label>Context (optional)</label>
            <textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              rows={3}
              placeholder="Product description, policy context, or style notes"
            />

            <label style={{ marginTop: 8 }}>Text (one sentence/segment per line)</label>
            <textarea value={textInput} onChange={(e) => setTextInput(e.target.value)} rows={8} />

            <label style={{ marginTop: 8 }}>Style ID (optional)</label>
            <input value={styleId} onChange={(e) => setStyleId(e.target.value)} placeholder="DeepL style_id" />

            <label style={{ marginTop: 8 }}>Custom instructions (one per line, max 10)</label>
            <textarea
              value={customInstructionsText}
              onChange={(e) => setCustomInstructionsText(e.target.value)}
              rows={4}
              placeholder="Prefer legal terminology"
            />

            <label style={{ marginTop: 8 }}>Translation memory ID (optional)</label>
            <select value={translationMemoryId} onChange={(e) => setTranslationMemoryId(e.target.value)}>
              <option value="">None</option>
              {translationMemories.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} ({item.source_lang}-{item.target_lang})
                </option>
              ))}
            </select>

            <label style={{ marginTop: 8 }}>Or enter raw DeepL translation memory ID</label>
            <input
              value={translationMemoryId}
              onChange={(e) => setTranslationMemoryId(e.target.value)}
              placeholder="DeepL translation_memory_id"
            />

            <label style={{ marginTop: 8 }}>Translation memory threshold (0-100)</label>
            <input
              type="number"
              min={0}
              max={100}
              value={translationMemoryThreshold}
              onChange={(e) => setTranslationMemoryThreshold(e.target.value)}
              placeholder="75"
            />

            <button type="submit" disabled={translating}>
              {translating ? 'Translating...' : 'Translate text'}
            </button>
          </form>

          {translations.length > 0 ? (
            <div style={{ marginTop: 12 }}>
              <p>
                Provider: <strong>{providerUsed}</strong> | Latency: <strong>{latencyMs ?? 0} ms</strong> | Billed:
                <strong> {billedChars ?? 0}</strong>
              </p>
              <pre>{JSON.stringify(translations, null, 2)}</pre>
            </div>
          ) : null}
        </article>

        <article style={cardStyle}>
          <h3>Document translation</h3>
          <form onSubmit={onTranslateDocument}>
            <input
              type="file"
              onChange={(e) => setDocumentFile(e.target.files?.[0] || null)}
              accept=".txt,.md,.docx,.pptx,.pdf,.xlsx"
            />
            <button type="submit" disabled={documentBusy}>
              {documentBusy ? 'Translating...' : 'Translate document'}
            </button>
          </form>

          {documentResult ? <pre style={{ marginTop: 12 }}>{documentResult}</pre> : null}
        </article>
      </section>

      <section className="grid">
        <article style={cardStyle}>
          <h3>Glossary manager</h3>
          <form onSubmit={onCreateGlossary}>
            <label>Name</label>
            <input value={newGlossaryName} onChange={(e) => setNewGlossaryName(e.target.value)} />

            <label style={{ marginTop: 8 }}>Source language</label>
            <input value={newGlossarySource} onChange={(e) => setNewGlossarySource(e.target.value.toUpperCase())} />

            <label style={{ marginTop: 8 }}>Target language</label>
            <input value={newGlossaryTarget} onChange={(e) => setNewGlossaryTarget(e.target.value.toUpperCase())} />

            <label style={{ marginTop: 8 }}>DeepL glossary id (optional passthrough)</label>
            <input value={newGlossaryDeepLId} onChange={(e) => setNewGlossaryDeepLId(e.target.value)} />

            <label style={{ marginTop: 8 }}>Entries (tab-separated source and target terms)</label>
            <textarea value={newGlossaryEntries} onChange={(e) => setNewGlossaryEntries(e.target.value)} rows={8} />

            <button type="submit" disabled={creatingGlossary}>
              {creatingGlossary ? 'Creating...' : 'Create glossary'}
            </button>
          </form>

          <pre style={{ marginTop: 12 }}>{JSON.stringify(glossaries, null, 2)}</pre>
        </article>

        <article style={cardStyle}>
          <h3>Translation memory manager</h3>
          <form onSubmit={onCreateTranslationMemory}>
            <label>Name</label>
            <input value={newMemoryName} onChange={(e) => setNewMemoryName(e.target.value)} />

            <label style={{ marginTop: 8 }}>Source language</label>
            <input value={newMemorySource} onChange={(e) => setNewMemorySource(e.target.value.toUpperCase())} />

            <label style={{ marginTop: 8 }}>Target language</label>
            <input value={newMemoryTarget} onChange={(e) => setNewMemoryTarget(e.target.value.toUpperCase())} />

            <label style={{ marginTop: 8 }}>Description</label>
            <textarea value={newMemoryDescription} onChange={(e) => setNewMemoryDescription(e.target.value)} rows={3} />

            <label style={{ marginTop: 8 }}>DeepL translation memory id (optional passthrough)</label>
            <input value={newMemoryDeepLId} onChange={(e) => setNewMemoryDeepLId(e.target.value)} />

            <button type="submit" disabled={creatingMemory}>
              {creatingMemory ? 'Creating...' : 'Create translation memory'}
            </button>
          </form>

          <pre style={{ marginTop: 12 }}>{JSON.stringify(translationMemories, null, 2)}</pre>
        </article>
      </section>
    </main>
  );
}
