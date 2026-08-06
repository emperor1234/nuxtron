'use client';

import { useEffect, useRef, useState } from 'react';
import { adsApi, AdsCampaign, CalendarEvent, PLATFORM_LABELS } from '@/app/lib/ads-api';

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

function handleDragOver(event: React.DragEvent) {
  event.preventDefault();
  event.dataTransfer.dropEffect = 'move';
}

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function buildCalendarDays(year: number, month: number): Date[] {
  const first = new Date(year, month, 1);
  const last = new Date(year, month + 1, 0);
  const days: Date[] = [];
  // Pad leading empty days
  for (let i = 0; i < first.getDay(); i++) days.push(new Date(0));
  for (let d = 1; d <= last.getDate(); d++) days.push(new Date(year, month, d));
  return days;
}

type DragState = { campaignId: string; fromDate: string; campaignName: string } | null;

export default function CalendarPage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [campaigns, setCampaigns] = useState<AdsCampaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [rescheduling, setRescheduling] = useState(false);
  const drag = useRef<DragState>(null);

  async function refresh() {
    setLoading(true);
    try {
      const [calRes, campRes] = await Promise.all([adsApi.calendar(), adsApi.listCampaigns()]);
      setEvents(calRes.events);
      setCampaigns(campRes.campaigns);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load calendar.');
    } finally {
      setLoading(false);
    }
  }

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => {
    void refresh();
  }, []);

  function prevMonth() {
    if (month === 0) {
      setYear((y) => y - 1);
      setMonth(11);
    } else setMonth((m) => m - 1);
  }
  function nextMonth() {
    if (month === 11) {
      setYear((y) => y + 1);
      setMonth(0);
    } else setMonth((m) => m + 1);
  }

  function eventsForDay(date: Date): CalendarEvent[] {
    if (date.getTime() === 0) return [];
    const key = isoDate(date);
    return events.filter((e) => e.date === key);
  }

  function handleDragStart(event: React.DragEvent, campaignId: string, fromDate: string, campaignName: string) {
    event.dataTransfer.effectAllowed = 'move';
    drag.current = { campaignId, fromDate, campaignName };
  }

  async function handleDrop(event: React.DragEvent, toDate: string) {
    event.preventDefault();
    const d = drag.current;
    if (!d || d.fromDate === toDate) {
      drag.current = null;
      return;
    }

    setRescheduling(true);
    setError('');
    try {
      const res = await adsApi.dragReschedule({
        campaign_id: d.campaignId,
        from_date: d.fromDate,
        to_date: toDate,
        auto_select_window_days: 14,
      });
      // Update local events
      setEvents((prev) => {
        const filtered = prev.filter((e) => !(e.campaign_id === d.campaignId && e.date === d.fromDate));
        const updated: CalendarEvent = {
          campaign_id: d.campaignId,
          campaign_name: d.campaignName,
          platform: res.campaign.platform,
          date: toDate,
          timezone: 'UTC',
          auto_post: true,
        };
        return [...filtered, updated].sort((a, b) => a.date.localeCompare(b.date));
      });
      setCampaigns((prev) => prev.map((c) => (c.id === d.campaignId ? res.campaign : c)));
      setInfo(`"${d.campaignName}" rescheduled to ${toDate}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reschedule failed.');
    } finally {
      drag.current = null;
      setRescheduling(false);
    }
  }

  const days = buildCalendarDays(year, month);

  return (
    <main style={{ padding: 24, minHeight: '100vh', background: 'var(--bg, #0a0a0a)', color: 'var(--text, #f1f5f9)' }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ margin: 0, fontSize: 26 }}>Campaign Calendar</h1>
          <div style={{ fontSize: 12, color: '#64748b' }}>
            {rescheduling ? 'Rescheduling…' : 'Drag events to reschedule'}
          </div>
        </div>

        {error && (
          <div
            style={{
              marginTop: 12,
              padding: 12,
              borderRadius: 10,
              border: '1px solid #ef4444',
              color: '#dc2626',
              background: '#7f1d1d22',
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}
        {info && (
          <div
            style={{
              marginTop: 12,
              padding: 12,
              borderRadius: 10,
              border: '1px solid #22c55e',
              color: '#86efac',
              background: '#14532d22',
              fontSize: 13,
            }}
          >
            {info}
          </div>
        )}

        {/* Month nav */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 18 }}>
          <button
            onClick={prevMonth}
            style={{
              padding: '6px 14px',
              borderRadius: 8,
              border: '1px solid var(--line, #333)',
              color: 'var(--text, #f1f5f9)',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: 14,
            }}
          >
            ‹
          </button>
          <span style={{ fontWeight: 800, fontSize: 18, minWidth: 180, textAlign: 'center' }}>
            {MONTHS[month]} {year}
          </span>
          <button
            onClick={nextMonth}
            style={{
              padding: '6px 14px',
              borderRadius: 8,
              border: '1px solid var(--line, #333)',
              color: 'var(--text, #f1f5f9)',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: 14,
            }}
          >
            ›
          </button>
        </div>

        {loading ? (
          <div style={{ marginTop: 40, textAlign: 'center', color: '#64748b' }}>Loading calendar…</div>
        ) : (
          <>
            {/* Weekday headers */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))', gap: 4, marginTop: 16 }}>
              {WEEKDAYS.map((w) => (
                <div
                  key={w}
                  style={{
                    textAlign: 'center',
                    fontSize: 11,
                    fontWeight: 700,
                    color: '#64748b',
                    textTransform: 'uppercase',
                    padding: '4px 0',
                  }}
                >
                  {w}
                </div>
              ))}
            </div>

            {/* Calendar grid */}
            <ul
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))',
                gap: 4,
                marginTop: 4,
                padding: 0,
                margin: '4px 0 0',
              }}
            >
              {days.map((date, idx) => {
                if (date.getTime() === 0) {
                  return (
                    <li key={`empty-col-${date.getDay()}-row-${Math.floor(idx / 7)}`} style={{ listStyle: 'none' }} />
                  );
                }
                const dayKey = isoDate(date);
                const dayEvents = eventsForDay(date);
                const isToday = dayKey === isoDate(today);
                return (
                  <li
                    key={dayKey}
                    onDragOver={handleDragOver}
                    onDrop={(e) => void handleDrop(e, dayKey)}
                    style={{
                      listStyle: 'none',
                      minHeight: 80,
                      background: isToday ? '#6366f122' : 'var(--bg-soft, #111)',
                      border: isToday ? '1px solid #6366f1' : '1px solid var(--line, #333)',
                      borderRadius: 8,
                      padding: 6,
                    }}
                  >
                    <div
                      style={{
                        fontSize: 11,
                        fontWeight: isToday ? 800 : 400,
                        color: isToday ? '#93c5fd' : '#64748b',
                        marginBottom: 4,
                      }}
                    >
                      {date.getDate()}
                    </div>
                    {dayEvents.map((ev) => (
                      <button
                        key={`${ev.campaign_id}-${ev.date}`}
                        type="button"
                        draggable
                        onKeyDown={() => {
                          /* keyboard reschedule not yet implemented */
                        }}
                        onDragStart={(e) => handleDragStart(e, ev.campaign_id, ev.date, ev.campaign_name)}
                        title={`${ev.campaign_name} — ${PLATFORM_LABELS[ev.platform] ?? ev.platform}`}
                        style={{
                          padding: '3px 6px',
                          borderRadius: 6,
                          background: '#6366f1',
                          color: '#bfdbfe',
                          fontSize: 10,
                          fontWeight: 700,
                          marginBottom: 2,
                          cursor: 'grab',
                          overflow: 'hidden',
                          whiteSpace: 'nowrap',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {ev.campaign_name}
                      </button>
                    ))}
                  </li>
                );
              })}
            </ul>

            {/* Campaign list below calendar */}
            {campaigns.length > 0 && (
              <div style={{ marginTop: 24 }}>
                <h2 style={{ fontSize: 15, marginBottom: 10 }}>Campaigns with scheduled dates</h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {campaigns
                    .filter((c) => (c.schedule.posting_dates?.length ?? 0) > 0)
                    .map((c) => (
                      <div
                        key={c.id}
                        style={{
                          padding: '10px 14px',
                          background: 'var(--bg-soft, #111)',
                          borderRadius: 10,
                          border: '1px solid var(--line, #333)',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          fontSize: 13,
                        }}
                      >
                        <span style={{ fontWeight: 700 }}>{c.campaign_name}</span>
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          {c.schedule.posting_dates.map((d) => (
                            <span
                              key={d}
                              style={{
                                padding: '2px 8px',
                                borderRadius: 999,
                                background: '#6366f122',
                                color: '#93c5fd',
                                border: '1px solid #6366f155',
                                fontSize: 11,
                              }}
                            >
                              {d}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}
