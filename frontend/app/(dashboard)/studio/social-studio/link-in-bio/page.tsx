'use client';

import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import Link from 'next/link';
import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type LinkInBioPage = {
  id: number;
  title: string;
  bio: string;
  theme: string;
  custom_domain: string;
  profile_image_url: string;
  slug: string;
  published: boolean;
  total_views: number;
  total_clicks: number;
  created_at: string;
  updated_at: string;
};

type LinkInBioLink = {
  id: number;
  page_id: number;
  label: string;
  url: string;
  emoji: string;
  is_product: boolean;
  product_price: number;
  product_currency: string;
  active: boolean;
  clicks: number;
  created_at: string;
};

type LinkInBioAnalytics = {
  page_id: number;
  total_views: number;
  total_clicks: number;
  click_through_rate: number;
  top_links: LinkInBioLink[];
  total_links: number;
  active_links: number;
};

type LinkInBioTimeseriesPoint = {
  date: string;
  views: number;
  clicks: number;
  ctr: number;
};

type LinkInBioPerLinkPoint = {
  date: string;
  clicks: number;
};

type LinkInBioPerLinkSeries = {
  link_id: number;
  label: string;
  total_clicks: number;
  series: LinkInBioPerLinkPoint[];
};

const THEMES = ['minimal', 'midnight', 'neon', 'sunset', 'mono'];

export default function SocialLinkInBioPage() {
  const [pages, setPages] = useState<LinkInBioPage[]>([]);
  const [selectedPageId, setSelectedPageId] = useState<number | null>(null);
  const [links, setLinks] = useState<LinkInBioLink[]>([]);
  const [analytics, setAnalytics] = useState<LinkInBioAnalytics | null>(null);
  const [timeseries, setTimeseries] = useState<LinkInBioTimeseriesPoint[]>([]);
  const [perLinkSeries, setPerLinkSeries] = useState<LinkInBioPerLinkSeries[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [dataFreshness, setDataFreshness] = useState<'live' | 'unavailable'>('live');
  const [lastLiveUpdatedAt, setLastLiveUpdatedAt] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);

  const [newPageTitle, setNewPageTitle] = useState('My Link Hub');
  const [newPageBio, setNewPageBio] = useState('Shop my creator picks, latest drops, and campaign links.');
  const [newPageTheme, setNewPageTheme] = useState('minimal');
  const [newPageDomain, setNewPageDomain] = useState('');
  const [newPageProfileImage, setNewPageProfileImage] = useState('');

  const [newLinkLabel, setNewLinkLabel] = useState('');
  const [newLinkUrl, setNewLinkUrl] = useState('');
  const [newLinkEmoji, setNewLinkEmoji] = useState('');
  const [newLinkIsProduct, setNewLinkIsProduct] = useState(false);
  const [newLinkPrice, setNewLinkPrice] = useState('0');
  const [newLinkCurrency, setNewLinkCurrency] = useState('USD');
  const [topLinkMetric, setTopLinkMetric] = useState<'clicks' | 'ctr'>('clicks');

  const selectedPage = useMemo(() => pages.find((page) => page.id === selectedPageId) ?? null, [pages, selectedPageId]);

  const sortedByClicks = useMemo(() => [...links].sort((a, b) => b.clicks - a.clicks), [links]);

  const maxClicks = useMemo(() => Math.max(1, ...sortedByClicks.map((item) => item.clicks)), [sortedByClicks]);

  const perLinkById = useMemo(() => new Map(perLinkSeries.map((item) => [item.link_id, item])), [perLinkSeries]);

  const trendSeries = useMemo(() => {
    return timeseries.slice(-6).map((point) => {
      const d = new Date(point.date);
      const label = Number.isNaN(d.getTime()) ? point.date.slice(5) : `${d.getMonth() + 1}/${d.getDate()}`;
      return { label, value: point.clicks };
    });
  }, [timeseries]);

  const trendMax = useMemo(() => Math.max(1, ...trendSeries.map((item) => item.value)), [trendSeries]);

  const freshnessTimestampLabel = useMemo(() => {
    if (!lastLiveUpdatedAt) return 'No live sync yet';
    const parsed = new Date(lastLiveUpdatedAt);
    if (Number.isNaN(parsed.getTime())) return 'No live sync yet';
    return `Last live sync ${parsed.toLocaleString()}`;
  }, [lastLiveUpdatedAt]);

  const AUTO_REFRESH_SECONDS = 30;

  const viewsByDate = useMemo(
    () => new Map(timeseries.map((point) => [point.date, Math.max(0, point.views)])),
    [timeseries]
  );

  useEffect(() => {
    void loadPages();
  }, []);

  useEffect(() => {
    if (selectedPageId === null) return;
    void loadPageDetails(selectedPageId);
  }, [selectedPageId]);

  useEffect(() => {
    if (selectedPageId === null || !autoRefreshEnabled) return;

    const timer = window.setInterval(() => {
      void loadPageDetails(selectedPageId);
    }, AUTO_REFRESH_SECONDS * 1000);

    return () => {
      window.clearInterval(timer);
    };
  }, [selectedPageId, autoRefreshEnabled]);

  async function loadPages() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<{ pages?: LinkInBioPage[] }>('/linkinbio/pages', DEFAULT_TENANT_ID);
      const loaded = res.pages ?? [];
      setPages(loaded);
      setSelectedPageId((current) => current ?? loaded[0]?.id ?? null);
      setDataFreshness('live');
      setLastLiveUpdatedAt(new Date().toISOString());
    } catch {
      setPages([]);
      setSelectedPageId(null);
      setLinks([]);
      setAnalytics(null);
      setTimeseries([]);
      setPerLinkSeries([]);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Backend not reachable in strict no-mock mode.'
          : 'Backend not reachable in fail-closed mode.'
      );
      setDataFreshness('unavailable');
    } finally {
      setLoading(false);
    }
  }

  async function loadPageDetails(pageId: number) {
    try {
      const [linksRes, analyticsRes, timeseriesRes] = await Promise.all([
        apiGet<{ links?: LinkInBioLink[] }>(`/linkinbio/pages/${pageId}/links`, DEFAULT_TENANT_ID),
        apiGet<{ analytics?: LinkInBioAnalytics }>(`/linkinbio/pages/${pageId}/analytics`, DEFAULT_TENANT_ID),
        apiGet<{ timeseries?: { series?: LinkInBioTimeseriesPoint[]; per_link?: LinkInBioPerLinkSeries[] } }>(
          `/linkinbio/pages/${pageId}/analytics/timeseries?days=30`,
          DEFAULT_TENANT_ID
        ),
      ]);
      setLinks(linksRes.links ?? []);
      setAnalytics(analyticsRes.analytics ?? null);
      setTimeseries(timeseriesRes.timeseries?.series ?? []);
      setPerLinkSeries(timeseriesRes.timeseries?.per_link ?? []);
      setDataFreshness('live');
      setLastLiveUpdatedAt(new Date().toISOString());
    } catch {
      setAnalytics((current) => current);
      setLinks((current) => current.filter((item) => item.page_id === pageId));
      setTimeseries((current) => current);
      setPerLinkSeries((current) => current);
      setError('Backend not reachable. Live analytics refresh failed in fail-closed mode.');
      setDataFreshness('unavailable');
    }
  }

  async function createPage() {
    if (!newPageTitle.trim()) return;
    setBusy(true);
    try {
      const res = await apiSend<{ page: LinkInBioPage }>(
        '/linkinbio/pages',
        'POST',
        {
          title: newPageTitle.trim(),
          bio: newPageBio.trim(),
          theme: newPageTheme,
          custom_domain: newPageDomain.trim(),
          profile_image_url: newPageProfileImage.trim(),
        },
        DEFAULT_TENANT_ID
      );
      setPages((prev) => [res.page, ...prev]);
      setSelectedPageId(res.page.id);
      setSuccess('Link in Bio page created and published.');
    } catch {
      setError('Failed to create Link in Bio page.');
    } finally {
      setBusy(false);
    }
  }

  async function updateCurrentPage() {
    if (!selectedPage) return;
    setBusy(true);
    try {
      const res = await apiSend<{ page: LinkInBioPage }>(
        `/linkinbio/pages/${selectedPage.id}`,
        'PATCH',
        {
          title: selectedPage.title,
          bio: selectedPage.bio,
          theme: selectedPage.theme,
          custom_domain: selectedPage.custom_domain,
        },
        DEFAULT_TENANT_ID
      );
      setPages((prev) => prev.map((page) => (page.id === res.page.id ? res.page : page)));
      setSuccess('Page profile updated.');
    } catch {
      setError('Failed to update page profile.');
    } finally {
      setBusy(false);
    }
  }

  async function addLink() {
    if (!selectedPage || !newLinkLabel.trim() || !newLinkUrl.trim()) return;
    setBusy(true);
    try {
      await apiSend<{ link: LinkInBioLink }>(
        `/linkinbio/pages/${selectedPage.id}/links`,
        'POST',
        {
          label: newLinkLabel.trim(),
          url: newLinkUrl.trim(),
          emoji: newLinkEmoji.trim(),
          is_product: newLinkIsProduct,
          product_price: Number.parseFloat(newLinkPrice || '0') || 0,
          product_currency: newLinkCurrency.trim() || 'USD',
          active: true,
        },
        DEFAULT_TENANT_ID
      );
      setNewLinkLabel('');
      setNewLinkUrl('');
      setNewLinkEmoji('');
      setNewLinkIsProduct(false);
      setNewLinkPrice('0');
      await loadPageDetails(selectedPage.id);
      setSuccess('Link added successfully.');
    } catch {
      setError('Failed to add link.');
    } finally {
      setBusy(false);
    }
  }

  async function toggleLink(link: LinkInBioLink) {
    if (!selectedPage) return;
    try {
      await apiSend(
        `/linkinbio/pages/${selectedPage.id}/links/${link.id}`,
        'PATCH',
        { active: !link.active },
        DEFAULT_TENANT_ID
      );
      await loadPageDetails(selectedPage.id);
    } catch {
      setError('Failed to update link status.');
    }
  }

  async function deleteLink(link: LinkInBioLink) {
    if (!selectedPage) return;
    try {
      await apiSend(`/linkinbio/pages/${selectedPage.id}/links/${link.id}`, 'DELETE', {}, DEFAULT_TENANT_ID);
      await loadPageDetails(selectedPage.id);
      setSuccess('Link removed.');
    } catch {
      setError('Failed to delete link.');
    }
  }

  async function simulateClick(link: LinkInBioLink) {
    if (!selectedPage) return;
    try {
      await apiSend(`/linkinbio/pages/${selectedPage.id}/links/${link.id}/click`, 'POST', {}, DEFAULT_TENANT_ID);
      await loadPageDetails(selectedPage.id);
    } catch {
      setError('Failed to record click event.');
    }
  }

  async function simulatePageView() {
    if (!selectedPage) return;
    try {
      await apiSend(`/linkinbio/pages/${selectedPage.id}/view`, 'POST', {}, DEFAULT_TENANT_ID);
      await loadPageDetails(selectedPage.id);
    } catch {
      setError('Failed to record page view event.');
    }
  }

  async function refreshAnalyticsNow() {
    if (selectedPageId === null) {
      await loadPages();
      return;
    }

    setRefreshing(true);
    try {
      await loadPageDetails(selectedPageId);
    } finally {
      setRefreshing(false);
    }
  }

  if (loading) {
    return <div style={styles.loading}>Loading Link in Bio workspace...</div>;
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Link In Bio Commerce</h1>
          <p style={styles.subtitle}>Build storefront bio pages, manage shoppable links, and track CTR in real time.</p>
        </div>
      </div>

      {error ? <div style={styles.error}>{error}</div> : null}
      {success ? <div style={styles.success}>{success}</div> : null}

      <div style={styles.grid}>
        <section style={styles.panel}>
          <h2 style={styles.panelTitle}>Pages</h2>
          <div style={styles.stack}>
            <input
              style={styles.input}
              value={newPageTitle}
              onChange={(e) => setNewPageTitle(e.target.value)}
              placeholder="Page title"
            />
            <textarea
              style={styles.textarea}
              value={newPageBio}
              onChange={(e) => setNewPageBio(e.target.value)}
              placeholder="Short bio"
            />
            <select style={styles.input} value={newPageTheme} onChange={(e) => setNewPageTheme(e.target.value)}>
              {THEMES.map((theme) => (
                <option key={theme} value={theme}>
                  {theme}
                </option>
              ))}
            </select>
            <input
              style={styles.input}
              value={newPageDomain}
              onChange={(e) => setNewPageDomain(e.target.value)}
              placeholder="Custom domain (optional)"
            />
            <input
              style={styles.input}
              value={newPageProfileImage}
              onChange={(e) => setNewPageProfileImage(e.target.value)}
              placeholder="Profile image URL (optional)"
            />
            <button style={styles.primaryBtn} onClick={() => void createPage()} disabled={busy}>
              Create New Page
            </button>
          </div>

          <div style={styles.divider} />

          <div style={styles.pageList}>
            {pages.map((page) => (
              <button
                key={page.id}
                style={{ ...styles.pageChip, ...(selectedPageId === page.id ? styles.pageChipActive : {}) }}
                onClick={() => setSelectedPageId(page.id)}
              >
                {page.title}
              </button>
            ))}
          </div>
        </section>

        <section style={styles.panel}>
          <h2 style={styles.panelTitle}>Links</h2>
          {selectedPage ? (
            <>
              <div style={styles.stack}>
                <input
                  style={styles.input}
                  value={selectedPage.title}
                  onChange={(e) =>
                    setPages((prev) =>
                      prev.map((p) => (p.id === selectedPage.id ? { ...p, title: e.target.value } : p))
                    )
                  }
                  placeholder="Page title"
                />
                <textarea
                  style={styles.textarea}
                  value={selectedPage.bio}
                  onChange={(e) =>
                    setPages((prev) => prev.map((p) => (p.id === selectedPage.id ? { ...p, bio: e.target.value } : p)))
                  }
                  placeholder="Page bio"
                />
                <button style={styles.secondaryBtn} onClick={() => void updateCurrentPage()} disabled={busy}>
                  Save Page Profile
                </button>
              </div>

              <div style={styles.divider} />

              <div style={styles.inlineRow}>
                <input
                  style={styles.input}
                  value={newLinkLabel}
                  onChange={(e) => setNewLinkLabel(e.target.value)}
                  placeholder="Link label"
                />
                <input
                  style={styles.input}
                  value={newLinkUrl}
                  onChange={(e) => setNewLinkUrl(e.target.value)}
                  placeholder="https://..."
                />
              </div>
              <div style={styles.inlineRow}>
                <input
                  style={styles.input}
                  value={newLinkEmoji}
                  onChange={(e) => setNewLinkEmoji(e.target.value)}
                  placeholder="Emoji"
                />
                <input
                  style={styles.input}
                  value={newLinkCurrency}
                  onChange={(e) => setNewLinkCurrency(e.target.value)}
                  placeholder="Currency"
                />
                <input
                  style={styles.input}
                  value={newLinkPrice}
                  onChange={(e) => setNewLinkPrice(e.target.value)}
                  placeholder="Price"
                />
              </div>
              <label style={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={newLinkIsProduct}
                  onChange={(e) => setNewLinkIsProduct(e.target.checked)}
                />
                Treat as product link
              </label>
              <button style={styles.primaryBtn} onClick={() => void addLink()} disabled={busy}>
                Add Link
              </button>

              <div style={styles.list}>
                {links.map((linkItem) => (
                  <div key={linkItem.id} style={styles.linkRow}>
                    <div>
                      <div style={styles.linkTitle}>
                        {linkItem.emoji} {linkItem.label}
                      </div>
                      <div style={styles.linkMeta}>{linkItem.url}</div>
                    </div>
                    <div style={styles.linkActions}>
                      <button style={styles.smallBtn} onClick={() => void simulateClick(linkItem)}>
                        Click +1
                      </button>
                      <button style={styles.smallBtn} onClick={() => void toggleLink(linkItem)}>
                        {linkItem.active ? 'Disable' : 'Enable'}
                      </button>
                      <button style={styles.smallDanger} onClick={() => void deleteLink(linkItem)}>
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p style={styles.muted}>Create or select a page to manage links.</p>
          )}
        </section>

        <section style={styles.panel}>
          <div style={styles.panelHead}>
            <h2 style={styles.panelTitle}>Analytics + Preview</h2>
            <div style={styles.freshnessWrap}>
              <span
                style={{
                  ...styles.freshnessPill,
                  ...(dataFreshness === 'live' ? styles.freshnessLive : styles.freshnessUnavailable),
                }}
              >
                {dataFreshness === 'live' ? 'Live data' : 'Data unavailable'}
              </span>
              <span style={styles.freshnessMeta}>
                {autoRefreshEnabled ? `Refreshes every ${AUTO_REFRESH_SECONDS}s` : 'Auto-refresh paused'}
              </span>
              <span style={styles.freshnessMeta}>{freshnessTimestampLabel}</span>
              <button
                type="button"
                style={{
                  ...styles.refreshNowBtn,
                  ...(autoRefreshEnabled ? styles.pauseBtn : styles.resumeBtn),
                }}
                onClick={() => setAutoRefreshEnabled((current) => !current)}
              >
                {autoRefreshEnabled ? 'Pause auto-refresh' : 'Resume auto-refresh'}
              </button>
              <button
                type="button"
                style={styles.refreshNowBtn}
                onClick={() => {
                  void refreshAnalyticsNow();
                }}
                disabled={refreshing}
              >
                {refreshing ? 'Refreshing...' : 'Refresh now'}
              </button>
            </div>
          </div>
          {selectedPage ? (
            <>
              <div style={styles.kpiGrid}>
                <div style={styles.kpiCard}>
                  <span style={styles.kpiLabel}>Views</span>
                  <strong style={styles.kpiValue}>{analytics?.total_views ?? 0}</strong>
                </div>
                <div style={styles.kpiCard}>
                  <span style={styles.kpiLabel}>Clicks</span>
                  <strong style={styles.kpiValue}>{analytics?.total_clicks ?? 0}</strong>
                </div>
                <div style={styles.kpiCard}>
                  <span style={styles.kpiLabel}>CTR</span>
                  <strong style={styles.kpiValue}>{((analytics?.click_through_rate ?? 0) * 100).toFixed(2)}%</strong>
                </div>
                <div style={styles.kpiCard}>
                  <span style={styles.kpiLabel}>Active Links</span>
                  <strong style={styles.kpiValue}>{analytics?.active_links ?? 0}</strong>
                </div>
              </div>
              <button style={styles.smallBtn} onClick={() => void simulatePageView()}>
                Record Page View +1
              </button>

              <div style={styles.chartCard}>
                <div style={styles.chartHeadRow}>
                  <h4 style={styles.chartTitle}>Top Link Performance</h4>
                  <div style={styles.metricToggleWrap}>
                    <button
                      type="button"
                      style={{
                        ...styles.metricToggleBtn,
                        ...(topLinkMetric === 'clicks' ? styles.metricToggleBtnActive : {}),
                      }}
                      onClick={() => setTopLinkMetric('clicks')}
                    >
                      Clicks
                    </button>
                    <button
                      type="button"
                      style={{
                        ...styles.metricToggleBtn,
                        ...(topLinkMetric === 'ctr' ? styles.metricToggleBtnActive : {}),
                      }}
                      onClick={() => setTopLinkMetric('ctr')}
                    >
                      CTR
                    </button>
                  </div>
                </div>
                <div style={styles.chartStack}>
                  {sortedByClicks.slice(0, 5).map((item) => (
                    <div key={item.id} style={styles.sparklineRow}>
                      <div style={styles.barLabel}>{item.label}</div>
                      <div style={styles.barTrackWrap}>
                        <div style={styles.barTrack}>
                          <div
                            style={{
                              ...styles.barFill,
                              width: `${Math.max(6, Math.round((item.clicks / maxClicks) * 100))}%`,
                            }}
                          />
                        </div>
                        <div style={styles.sparklineWrap}>
                          {(perLinkById.get(item.id)?.series ?? []).slice(-10).map((point, idx, arr) => {
                            const values = arr.map((p) => {
                              const dailyViews = viewsByDate.get(p.date) ?? 0;
                              return topLinkMetric === 'ctr' ? (dailyViews > 0 ? p.clicks / dailyViews : 0) : p.clicks;
                            });
                            const localMax = Math.max(1e-6, ...values);
                            const currentValue = values[idx] ?? 0;
                            return (
                              <span
                                key={`${item.id}-${point.date}`}
                                style={{
                                  ...styles.sparklineBar,
                                  height: `${Math.max(2, Math.round((currentValue / localMax) * 18))}px`,
                                  opacity: idx === arr.length - 1 ? 1 : 0.75,
                                }}
                                title={
                                  topLinkMetric === 'ctr'
                                    ? `${point.date}: ${(currentValue * 100).toFixed(1)}% CTR`
                                    : `${point.date}: ${point.clicks} clicks`
                                }
                              />
                            );
                          })}
                        </div>
                      </div>
                      <div style={styles.barValue}>
                        {topLinkMetric === 'ctr'
                          ? `${(
                              ((perLinkById.get(item.id)?.series ?? []).reduce((acc, p) => {
                                const dailyViews = viewsByDate.get(p.date) ?? 0;
                                return acc + (dailyViews > 0 ? p.clicks / dailyViews : 0);
                              }, 0) /
                                Math.max(1, (perLinkById.get(item.id)?.series ?? []).length)) *
                              100
                            ).toFixed(1)}%`
                          : item.clicks}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={styles.chartCard}>
                <h4 style={styles.chartTitle}>Traffic Trend (real daily timeseries)</h4>
                <div style={styles.miniChart}>
                  {trendSeries.map((point) => (
                    <div key={point.label} style={styles.miniBarCol}>
                      <div
                        style={{
                          ...styles.miniBar,
                          height: `${Math.max(8, Math.round((point.value / trendMax) * 80))}px`,
                        }}
                      />
                      <span style={styles.miniLabel}>{point.label}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div style={styles.chartCard}>
                <h4 style={styles.chartTitle}>Daily Views vs Clicks (last 30 days)</h4>
                <div style={styles.seriesList}>
                  {timeseries
                    .slice(-8)
                    .reverse()
                    .map((point) => (
                      <div key={point.date} style={styles.seriesRow}>
                        <span style={styles.seriesDate}>{point.date}</span>
                        <span style={styles.seriesMetric}>Views {point.views}</span>
                        <span style={styles.seriesMetric}>Clicks {point.clicks}</span>
                        <span style={styles.seriesMetric}>CTR {(point.ctr * 100).toFixed(1)}%</span>
                      </div>
                    ))}
                </div>
              </div>

              <div style={styles.chartCard}>
                <h4 style={styles.chartTitle}>Conversion Funnel</h4>
                <div style={styles.funnelWrap}>
                  <div style={{ ...styles.funnelStep, width: '100%' }}>
                    Profile Views: {analytics?.total_views ?? 0}
                  </div>
                  <div style={{ ...styles.funnelStep, width: '78%' }}>Link Clicks: {analytics?.total_clicks ?? 0}</div>
                  <div style={{ ...styles.funnelStep, width: '56%' }}>
                    Product Intent: {Math.round((analytics?.total_clicks ?? 0) * 0.42)}
                  </div>
                  <div style={{ ...styles.funnelStep, width: '42%' }}>
                    Estimated Checkouts: {Math.round((analytics?.total_clicks ?? 0) * 0.18)}
                  </div>
                </div>
              </div>

              <div style={styles.preview}>
                <div style={styles.previewHeader}>@{selectedPage.slug}</div>
                <h3 style={styles.previewTitle}>{selectedPage.title}</h3>
                <p style={styles.previewBio}>{selectedPage.bio}</p>
                <div style={styles.previewLinks}>
                  {links
                    .filter((item) => item.active)
                    .map((item) => (
                      <div key={item.id} style={styles.previewLink}>
                        {item.emoji} {item.label}
                      </div>
                    ))}
                </div>
              </div>
            </>
          ) : (
            <p style={styles.muted}>No page selected.</p>
          )}
        </section>
      </div>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  container: { background: 'var(--card)', minHeight: '100vh', color: 'var(--text)', padding: 28 },
  header: { marginBottom: 16 },
  backLink: { color: 'var(--muted)', textDecoration: 'none', fontSize: 13 },
  title: { margin: '8px 0 4px', fontSize: 28 },
  subtitle: { margin: 0, color: 'var(--muted)' },
  error: { background: '#fee2e2', border: '1px solid #ef4444', borderRadius: 8, padding: 10, marginBottom: 12 },
  success: { background: '#dcfce7', border: '1px solid #22c55e', borderRadius: 8, padding: 10, marginBottom: 12 },
  loading: { background: 'var(--card)', color: 'var(--text)', minHeight: '100vh', display: 'grid', placeItems: 'center' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 14 },
  panel: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 },
  panelHead: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  panelTitle: { margin: '0 0 12px', fontSize: 16 },
  freshnessWrap: { display: 'grid', justifyItems: 'end', gap: 4 },
  freshnessPill: {
    borderRadius: 999,
    border: '1px solid transparent',
    padding: '3px 8px',
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  freshnessMeta: { color: 'var(--muted)', fontSize: 11 },
  refreshNowBtn: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 6,
    color: 'var(--text)',
    padding: '4px 8px',
    cursor: 'pointer',
    fontSize: 12,
    justifySelf: 'end',
  },
  pauseBtn: { color: '#dc2626', borderColor: '#fee2e2', background: '#fee2e2' },
  resumeBtn: { color: '#15803d', borderColor: '#dcfce7', background: '#dcfce7' },
  freshnessLive: { color: '#15803d', borderColor: '#dcfce7', background: '#dcfce7' },
  freshnessUnavailable: { color: '#b45309', borderColor: '#fef3c7', background: '#fef3c7' },
  stack: { display: 'grid', gap: 8 },
  input: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, color: 'var(--text)', padding: '8px 10px' },
  textarea: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    color: 'var(--text)',
    padding: '8px 10px',
    minHeight: 70,
  },
  primaryBtn: {
    background: '#6366f1',
    border: 'none',
    borderRadius: 8,
    color: '#fff',
    padding: '9px 12px',
    cursor: 'pointer',
  },
  secondaryBtn: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    color: 'var(--text)',
    padding: '8px 10px',
    cursor: 'pointer',
  },
  divider: { borderTop: '1px solid var(--line)', margin: '12px 0' },
  pageList: { display: 'flex', flexWrap: 'wrap', gap: 8 },
  pageChip: {
    background: 'var(--card)',
    color: 'var(--muted)',
    border: '1px solid var(--line)',
    borderRadius: 999,
    padding: '6px 10px',
    cursor: 'pointer',
  },
  pageChipActive: { background: '#1e3a8a', color: '#fff', border: '1px solid #6366f1' },
  inlineRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 8, marginBottom: 8 },
  checkboxLabel: { display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, color: 'var(--muted)', marginBottom: 8 },
  list: { display: 'grid', gap: 8, marginTop: 10, maxHeight: 320, overflowY: 'auto' },
  linkRow: {
    border: '1px solid var(--line)',
    borderRadius: 8,
    padding: 10,
    display: 'flex',
    justifyContent: 'space-between',
    gap: 12,
  },
  linkTitle: { fontWeight: 600, marginBottom: 4 },
  linkMeta: {
    color: 'var(--muted)',
    fontSize: 12,
    maxWidth: 280,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  linkActions: { display: 'flex', gap: 6, alignItems: 'center' },
  smallBtn: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 6,
    color: 'var(--text)',
    padding: '4px 8px',
    cursor: 'pointer',
    fontSize: 12,
  },
  smallDanger: {
    background: '#fee2e2',
    border: '1px solid #ef4444',
    borderRadius: 6,
    color: '#fecaca',
    padding: '4px 8px',
    cursor: 'pointer',
    fontSize: 12,
  },
  muted: { color: 'var(--muted)' },
  kpiGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 8, marginBottom: 12 },
  kpiCard: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, padding: 10 },
  kpiLabel: { color: 'var(--muted)', fontSize: 11, textTransform: 'uppercase' },
  kpiValue: { display: 'block', marginTop: 4, fontSize: 20 },
  chartCard: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 10, padding: 10, marginBottom: 10 },
  chartHeadRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  chartTitle: { margin: '0 0 8px', fontSize: 13, color: 'var(--muted)' },
  metricToggleWrap: { display: 'flex', gap: 4 },
  metricToggleBtn: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 6,
    color: 'var(--muted)',
    padding: '3px 7px',
    cursor: 'pointer',
    fontSize: 11,
  },
  metricToggleBtnActive: { color: '#ECFDF5', border: '1px solid #22c55e', background: '#dcfce7' },
  chartStack: { display: 'grid', gap: 6 },
  barRow: { display: 'grid', gridTemplateColumns: '1fr 2fr 48px', gap: 8, alignItems: 'center' },
  sparklineRow: { display: 'grid', gridTemplateColumns: '1fr 2fr 48px', gap: 8, alignItems: 'center' },
  barLabel: { fontSize: 12, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  barTrackWrap: { display: 'grid', gap: 4 },
  barTrack: { background: 'var(--card)', height: 8, borderRadius: 999, overflow: 'hidden' },
  barFill: { background: 'linear-gradient(90deg,#6366f1,#22c55e)', height: '100%' },
  barValue: { fontSize: 12, textAlign: 'right', color: 'var(--muted)' },
  sparklineWrap: { display: 'flex', alignItems: 'end', gap: 2, height: 20 },
  sparklineBar: { width: 4, background: '#22c55e', borderRadius: 2, display: 'inline-block' },
  miniChart: { height: 112, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))', gap: 8, alignItems: 'end' },
  miniBarCol: { display: 'grid', justifyItems: 'center', gap: 4 },
  miniBar: { width: 18, background: 'var(--brand)', borderRadius: 6 },
  miniLabel: { fontSize: 11, color: 'var(--muted)' },
  seriesList: { display: 'grid', gap: 6 },
  seriesRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: 8, fontSize: 12, color: 'var(--text)' },
  seriesDate: { color: 'var(--muted)' },
  seriesMetric: { textAlign: 'right' },
  funnelWrap: { display: 'grid', gap: 6, justifyItems: 'center' },
  funnelStep: {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 8,
    padding: '6px 8px',
    textAlign: 'center',
    fontSize: 12,
    color: 'var(--text)',
  },
  preview: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 14 },
  previewHeader: { color: 'var(--brand)', fontSize: 12, marginBottom: 8 },
  previewTitle: { margin: 0, fontSize: 20 },
  previewBio: { color: 'var(--muted)', marginTop: 6 },
  previewLinks: { display: 'grid', gap: 8, marginTop: 12 },
  previewLink: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, padding: '8px 10px' },
};
