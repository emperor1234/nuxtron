'use client';

import { useState } from 'react';

interface Draft {
  id: string;
  title: string;
  topic: string;
  status: string;
  word_count: number;
  seo_score?: { overall_score: number; recommendations: string[] };
  created_at: string;
  updated_at?: string;
  _source?: string;
}

interface DraftDetail extends Draft {
  content: string;
  target_keyword?: string;
}

interface ContentIdea {
  id: string;
  title: string;
  estimated_traffic: number;
  difficulty: string;
  intent: string;
  word_count_target?: number;
}

const DIFFICULTY_COLORS: Record<string, string> = {
  Easy: 'bg-green-100 text-green-700',
  Medium: 'bg-yellow-100 text-yellow-700',
  Hard: 'bg-red-100 text-red-700',
};

export default function ContentShakePage() {
  const [activeTab, setActiveTab] = useState<'ideas' | 'generate' | 'drafts'>('ideas');

  // Ideas
  const [ideaTopic, setIdeaTopic] = useState('');
  const [ideas, setIdeas] = useState<ContentIdea[]>([]);
  const [ideasLoading, setIdeasLoading] = useState(false);

  // Generate
  const [genTopic, setGenTopic] = useState('');
  const [genKeyword, setGenKeyword] = useState('');
  const [genWordCount, setGenWordCount] = useState(1200);
  const [genTone, setGenTone] = useState('Professional');
  const [genLoading, setGenLoading] = useState(false);
  const [generatedDraft, setGeneratedDraft] = useState<DraftDetail | null>(null);

  // Drafts
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [draftsLoading, setDraftsLoading] = useState(false);
  const [selectedDraft, setSelectedDraft] = useState<DraftDetail | null>(null);

  const [error, setError] = useState('');

  async function fetchIdeas() {
    if (!ideaTopic.trim()) return;
    setIdeasLoading(true);
    setError('');
    try {
      const res = await fetch(`/api/contentshake/ideas?topic=${encodeURIComponent(ideaTopic.trim())}&count=12`);
      const data = await res.json();
      setIdeas(data.ideas || []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setIdeasLoading(false);
    }
  }

  async function generateArticle() {
    if (!genTopic.trim()) return;
    setGenLoading(true);
    setError('');
    try {
      const res = await fetch('/api/contentshake/generate-article', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: genTopic.trim(),
          keyword: genKeyword.trim(),
          word_count: genWordCount,
          tone: genTone,
          include_faq: true,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setGeneratedDraft(await res.json());
      setActiveTab('drafts');
      await loadDrafts();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Generation failed');
    } finally {
      setGenLoading(false);
    }
  }

  async function loadDrafts() {
    setDraftsLoading(true);
    try {
      const res = await fetch('/api/contentshake/drafts');
      const data = await res.json();
      setDrafts(data.drafts || []);
    } catch {
    } finally {
      setDraftsLoading(false);
    }
  }

  async function openDraft(id: string) {
    const res = await fetch(`/api/contentshake/drafts/${id}`);
    if (res.ok) setSelectedDraft(await res.json());
  }

  async function deleteDraft(id: string) {
    await fetch(`/api/contentshake/drafts/${id}`, { method: 'DELETE' });
    setDrafts((prev) => prev.filter((d) => d.id !== id));
    if (selectedDraft?.id === id) setSelectedDraft(null);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b px-6 py-4 flex items-center gap-3">
        <svg className="w-7 h-7 text-[var(--brand)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
          />
        </svg>
        <div>
          <h1 className="text-xl font-bold text-gray-900">ContentShake AI</h1>
          <p className="text-sm text-gray-500">AI-powered SEO content generation, optimization &amp; management</p>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Tabs */}
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
          {[
            { id: 'ideas', label: 'Content Ideas' },
            { id: 'generate', label: 'Generate Article' },
            { id: 'drafts', label: `Drafts (${drafts.length})` },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => {
                setActiveTab(t.id as 'ideas' | 'generate' | 'drafts');
                if (t.id === 'drafts') loadDrafts();
              }}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === t.id ? 'bg-white shadow text-[var(--brand)]' : 'text-gray-600 hover:text-gray-900'}`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {error && (
          <p className="text-red-500 text-sm mb-4 bg-red-50 border border-red-200 rounded-lg px-4 py-2">{error}</p>
        )}

        {/* Ideas Tab */}
        {activeTab === 'ideas' && (
          <div>
            <div className="bg-white rounded-xl border shadow-sm p-6 mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">Topic or Niche</label>
              <div className="flex gap-3">
                <input
                  type="text"
                  value={ideaTopic}
                  onChange={(e) => setIdeaTopic(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && fetchIdeas()}
                  placeholder="e.g. technical SEO, local marketing, e-commerce"
                  className="flex-1 border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-[var(--brand)] focus:outline-none"
                />
                <button
                  onClick={fetchIdeas}
                  disabled={ideasLoading || !ideaTopic.trim()}
                  className="bg-[var(--brand)] hover:bg-[var(--brand)] text-white font-semibold px-6 py-2.5 rounded-lg disabled:opacity-50 text-sm"
                >
                  {ideasLoading ? 'Generating…' : 'Get Ideas'}
                </button>
              </div>
            </div>
            {ideas.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {ideas.map((idea) => (
                  <div key={idea.id} className="bg-white rounded-xl border p-4 hover:shadow-md transition-shadow">
                    <p className="font-semibold text-gray-900 text-sm mb-2 line-clamp-2">{idea.title}</p>
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${DIFFICULTY_COLORS[idea.difficulty] || 'bg-gray-100 text-gray-600'}`}
                      >
                        {idea.difficulty}
                      </span>
                      <span className="text-xs bg-blue-50 text-[var(--brand)] px-2 py-0.5 rounded-full">{idea.intent}</span>
                    </div>
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>~{idea.word_count_target ?? 1200} words</span>
                      <span>{(idea.estimated_traffic / 1000).toFixed(0)}K traffic</span>
                    </div>
                    <button
                      onClick={() => {
                        setGenTopic(idea.title);
                        setActiveTab('generate');
                      }}
                      className="mt-3 w-full text-xs text-[var(--brand)] border border-indigo-200 rounded-lg py-1.5 hover:bg-indigo-50"
                    >
                      Generate Article →
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Generate Tab */}
        {activeTab === 'generate' && (
          <div className="bg-white rounded-xl border shadow-sm p-6">
            <h2 className="font-semibold text-gray-800 mb-4">Generate SEO Article</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Article Topic *</label>
                <input
                  type="text"
                  value={genTopic}
                  onChange={(e) => setGenTopic(e.target.value)}
                  placeholder="The Complete Guide to Technical SEO"
                  className="w-full border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-[var(--brand)] focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Target Keyword</label>
                <input
                  type="text"
                  value={genKeyword}
                  onChange={(e) => setGenKeyword(e.target.value)}
                  placeholder="technical seo"
                  className="w-full border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-[var(--brand)] focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Word Count</label>
                <select
                  value={genWordCount}
                  onChange={(e) => setGenWordCount(Number(e.target.value))}
                  className="w-full border rounded-lg px-3 py-2.5 text-sm"
                >
                  {[600, 800, 1000, 1200, 1500, 2000, 2500, 3000].map((n) => (
                    <option key={n} value={n}>
                      {n.toLocaleString()} words
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tone</label>
                <select
                  value={genTone}
                  onChange={(e) => setGenTone(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2.5 text-sm"
                >
                  {['Professional', 'Conversational', 'Authoritative', 'Friendly', 'Educational'].map((t) => (
                    <option key={t}>{t}</option>
                  ))}
                </select>
              </div>
            </div>
            <button
              onClick={generateArticle}
              disabled={genLoading || !genTopic.trim()}
              className="bg-[var(--brand)] hover:bg-[var(--brand)] text-white font-semibold px-8 py-3 rounded-lg disabled:opacity-50 text-sm"
            >
              {genLoading ? '✨ Generating with AI…' : '✨ Generate Article'}
            </button>
            {genLoading && (
              <p className="text-sm text-gray-500 mt-2">This may take 30–60 seconds with AI generation…</p>
            )}
          </div>
        )}

        {/* Drafts Tab */}
        {activeTab === 'drafts' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Draft list */}
            <div className="lg:col-span-1 bg-white rounded-xl border shadow-sm p-5">
              <div className="flex justify-between items-center mb-3">
                <h2 className="font-semibold text-gray-800">All Drafts</h2>
                <button
                  onClick={loadDrafts}
                  disabled={draftsLoading}
                  className="text-xs text-[var(--brand)] hover:underline"
                >
                  Refresh
                </button>
              </div>
              {drafts.length === 0 ? (
                <p className="text-sm text-[var(--muted)] text-center py-8">No drafts yet. Generate an article first.</p>
              ) : (
                <ul className="space-y-2">
                  {drafts.map((d) => (
                    <li
                      key={d.id}
                      className={`border rounded-lg p-3 cursor-pointer hover:border-[var(--brand)] ${selectedDraft?.id === d.id ? 'border-[var(--brand)] bg-indigo-50' : ''}`}
                      onClick={() => openDraft(d.id)}
                    >
                      <p className="font-medium text-sm text-gray-900 line-clamp-1">{d.title}</p>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-xs text-[var(--muted)]">{d.word_count} words</span>
                        <div className="flex items-center gap-1">
                          <span
                            className={`text-xs px-1.5 py-0.5 rounded font-medium ${d.status === 'published' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}
                          >
                            {d.status}
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteDraft(d.id);
                            }}
                            className="text-[var(--muted)] hover:text-red-500 text-xs ml-1"
                          >
                            ✕
                          </button>
                        </div>
                      </div>
                      {d.seo_score && (
                        <div className="mt-1.5">
                          <div className="h-1.5 bg-gray-100 rounded-full">
                            <div
                              className="h-1.5 bg-[var(--brand)] rounded-full"
                              style={{ width: `${d.seo_score.overall_score}%` }}
                            />
                          </div>
                          <p className="text-xs text-[var(--muted)] mt-0.5">SEO {d.seo_score.overall_score}/100</p>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Draft detail */}
            <div className="lg:col-span-2 bg-white rounded-xl border shadow-sm p-5">
              {selectedDraft ? (
                <div>
                  <div className="flex items-start justify-between mb-4">
                    <h2 className="font-bold text-gray-900 text-lg">{selectedDraft.title}</h2>
                    <span className="text-xs text-[var(--muted)] shrink-0 ml-2">
                      {selectedDraft._source === 'ollama'
                        ? '🤖 Ollama'
                        : selectedDraft._source === 'openai'
                          ? '🤖 OpenAI'
                          : selectedDraft._source === 'seed'
                            ? '📋 Template'
                            : ''}
                    </span>
                  </div>
                  {selectedDraft.seo_score && selectedDraft.seo_score.recommendations.length > 0 && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
                      <p className="text-xs font-semibold text-amber-700 mb-1">SEO Recommendations</p>
                      <ul className="list-disc list-inside space-y-0.5">
                        {selectedDraft.seo_score.recommendations.map((r, i) => (
                          <li key={i} className="text-xs text-amber-700">
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div className="prose prose-sm max-w-none max-h-[500px] overflow-y-auto border rounded-lg p-4 bg-gray-50">
                    <pre className="whitespace-pre-wrap text-sm text-gray-800 font-sans">{selectedDraft.content}</pre>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-48 text-[var(--muted)]">
                  <div className="text-center">
                    <p className="text-4xl mb-2">📝</p>
                    <p className="text-sm">Select a draft to view</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
