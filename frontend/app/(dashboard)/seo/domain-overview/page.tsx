"use client";

import { useCallback, useEffect, useState } from "react";
import { Globe2 } from "lucide-react";
import { useSearchParams } from "next/navigation";
import {
  Badge,
  Button,
  Card,
  CardTitle,
  Field,
  Page,
  PageHeader,
  Stat,
  StatGrid,
  TableWrap,
  tableClass,
} from "../../_ui/kit";
import styles from "../components/seo-workspace.module.css";

interface DomainSummary {
  domain: string;
  organic_traffic: number;
  organic_keywords: number;
  authority_score: number;
  backlinks: number;
  paid_keywords?: number;
  estimated_traffic_cost_usd?: number;
  traffic_trend_pct?: number;
  top_organic_keywords?: {
    keyword: string;
    position: number;
    volume: number;
  }[];
  top_competitors?: {
    domain: string;
    common_keywords: number;
    authority_score: number;
  }[];
  _source?: string;
}

export default function DomainOverviewPage() {
  const searchParams = useSearchParams();
  const requestedDomain = searchParams.get("domain")?.trim() || "";
  const [domain, setDomain] = useState(requestedDomain);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<DomainSummary | null>(null);
  const [error, setError] = useState("");

  const runSummary = useCallback(async (value: string) => {
    if (!value.trim()) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(
        `/api/domain-overview/summary?domain=${encodeURIComponent(value.trim())}`,
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setData((await response.json()) as DomainSummary);
    } catch (exception: unknown) {
      setError(
        exception instanceof Error ? exception.message : "Request failed",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!requestedDomain) return;
    const timer = window.setTimeout(() => {
      void runSummary(requestedDomain);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [requestedDomain, runSummary]);

  const formatNumber = (value: number | undefined) =>
    value === undefined
      ? "—"
      : value >= 1_000_000
        ? `${(value / 1_000_000).toFixed(1)}M`
        : value >= 1_000
          ? `${(value / 1_000).toFixed(1)}K`
          : String(value);

  const formatTrend = (value: number | undefined) =>
    value === undefined ? "—" : `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;

  return (
    <Page className={styles.page}>
      <PageHeader
        title="Domain Overview"
        subtitle="A live snapshot of search visibility, authority, backlinks, and competitors."
        actions={
          data?._source ? (
            <Badge tone="neutral">Source: {data._source}</Badge>
          ) : undefined
        }
      />

      <Card>
        <div className={styles.searchCard}>
          <Field
            id="domain-overview-domain"
            label="Analyze a domain"
            value={domain}
            onChange={(event) => setDomain(event.target.value)}
            onKeyDown={(event) =>
              event.key === "Enter" && void runSummary(domain)
            }
            placeholder="example.com"
            autoComplete="url"
          />
          <Button
            variant="primary"
            onClick={() => void runSummary(domain)}
            disabled={loading || !domain.trim()}
          >
            {loading ? "Analyzing…" : "Analyze domain"}
          </Button>
        </div>
      </Card>

      {error ? <div className={styles.error}>{error}</div> : null}

      {!data && !loading ? (
        <Card className={styles.empty}>
          <span className={styles.emptyIcon}>
            <Globe2 size={23} aria-hidden="true" />
          </span>
          <h2>Start with a domain</h2>
          <p>
            Enter your website or a competitor to build a comparable,
            decision-ready visibility snapshot.
          </p>
        </Card>
      ) : null}

      {data ? (
        <>
          <StatGrid>
            <Stat
              label="Organic traffic"
              value={formatNumber(data.organic_traffic)}
              hint="Estimated monthly visits"
            />
            <Stat
              label="Organic keywords"
              value={formatNumber(data.organic_keywords)}
              hint="Ranking search terms"
            />
            <Stat
              label="Authority score"
              value={data.authority_score ?? "—"}
              hint="Domain strength"
            />
            <Stat
              label="Backlinks"
              value={formatNumber(data.backlinks)}
              hint="Known inbound links"
            />
            <Stat
              label="Paid keywords"
              value={formatNumber(data.paid_keywords)}
            />
            <Stat
              label="Traffic cost"
              value={
                data.estimated_traffic_cost_usd === undefined
                  ? "—"
                  : `$${formatNumber(data.estimated_traffic_cost_usd)}`
              }
              hint="Estimated monthly value"
            />
            <Stat
              label="30-day trend"
              value={formatTrend(data.traffic_trend_pct)}
            />
          </StatGrid>

          {data.top_organic_keywords?.length ? (
            <Card pad={false} className={styles.sectionCard}>
              <div style={{ padding: "20px 22px 10px" }}>
                <CardTitle sub="The search terms contributing most to current visibility.">
                  Top organic keywords
                </CardTitle>
              </div>
              <TableWrap>
                <table className={tableClass}>
                  <thead>
                    <tr>
                      <th>Keyword</th>
                      <th>Position</th>
                      <th>Volume</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.top_organic_keywords.map((keyword) => (
                      <tr key={`${keyword.keyword}-${keyword.position}`}>
                        <td>{keyword.keyword}</td>
                        <td>
                          <Badge
                            tone={
                              keyword.position <= 10 ? "success" : "neutral"
                            }
                          >
                            #{keyword.position}
                          </Badge>
                        </td>
                        <td>{formatNumber(keyword.volume)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
            </Card>
          ) : null}

          {data.top_competitors?.length ? (
            <Card pad={false} className={styles.sectionCard}>
              <div style={{ padding: "20px 22px 10px" }}>
                <CardTitle sub="Domains competing for the same organic demand.">
                  Top competitors
                </CardTitle>
              </div>
              <TableWrap>
                <table className={tableClass}>
                  <thead>
                    <tr>
                      <th>Domain</th>
                      <th>Common keywords</th>
                      <th>Authority score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.top_competitors.map((competitor) => (
                      <tr key={competitor.domain}>
                        <td>{competitor.domain}</td>
                        <td>{formatNumber(competitor.common_keywords)}</td>
                        <td>{competitor.authority_score}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
            </Card>
          ) : null}
        </>
      ) : null}
    </Page>
  );
}
