'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { socialApi, type CalendarEvent, type PublishingQueueResponse } from '@/app/lib/social-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

export default function CalendarPage() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [draggingEvent, setDraggingEvent] = useState<CalendarEvent | null>(null);
  const [queue, setQueue] = useState<PublishingQueueResponse | null>(null);
  const [pauseReason, setPauseReason] = useState('Operational review in progress.');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadEvents();
  }, [currentMonth]);

  async function loadEvents() {
    setError(null);
    try {
      const startDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1).toISOString().split('T')[0];
      const endDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0).toISOString().split('T')[0];

      const [result, queueResult] = await Promise.all([
        socialApi.listCalendarEvents(startDate, endDate),
        socialApi.getPublishingQueue(),
      ]);
      setEvents(result || []);
      setQueue(queueResult);
    } catch (err) {
      console.error('Failed to load events:', err);
      setEvents([]);
      setQueue(null);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Calendar backend unavailable in strict no-mock mode.'
          : 'Calendar backend unavailable in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  function getDaysInMonth() {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const days = [];
    for (let i = 0; i < firstDay; i++) {
      days.push(null);
    }
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(i);
    }
    return days;
  }

  function getEventsForDay(day: number | null) {
    if (!day) return [];
    const date = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
    return events.filter((e) => {
      const eventDate = new Date(e.scheduledTime);
      return eventDate.toDateString() === date.toDateString();
    });
  }

  async function handleReschedule(event: CalendarEvent, newDay: number) {
    if (!newDay) return;
    const newDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), newDay);
    const eventTime = new Date(event.scheduledTime);
    newDate.setHours(eventTime.getHours(), eventTime.getMinutes());

    try {
      await socialApi.moveSchedule(event.id, newDate.toISOString());
      setEvents(events.map((e) => (e.id === event.id ? { ...e, scheduledTime: newDate.toISOString() } : e)));
    } catch (err) {
      console.error('Reschedule failed:', err);
      alert('Failed to reschedule event');
    }
    setDraggingEvent(null);
  }

  async function handlePauseAll() {
    try {
      const pause_all = await socialApi.setPauseAll(!(queue?.pause_all.paused ?? false), pauseReason);
      setQueue((current) =>
        current ? { ...current, pause_all } : { pause_all, summary: { scheduled: events.length, drafts: 0 }, items: [] }
      );
    } catch (err) {
      console.error('Pause-all update failed:', err);
      alert('Failed to update pause-all state');
    }
  }

  const monthName = currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  const days = getDaysInMonth();
  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Campaign Calendar</h1>
          <p style={styles.subtitle}>Drag posts to reschedule them across platforms</p>
        </div>
      </div>

      {error ? <div style={styles.errorBanner}>⚠ {error}</div> : null}

      {/* Month Navigation */}
      <div style={styles.monthNav}>
        <button
          onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))}
          style={styles.navBtn}
        >
          ← Previous
        </button>
        <h2 style={styles.monthName}>{monthName}</h2>
        <button
          onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))}
          style={styles.navBtn}
        >
          Next →
        </button>
      </div>

      <div style={styles.queuePanel}>
        <div>
          <strong style={styles.queueTitle}>Automation Queue</strong>
          <p style={styles.queueCopy}>
            Scheduled {queue?.summary.scheduled ?? 0} • Drafts {queue?.summary.drafts ?? 0} • State{' '}
            {queue?.pause_all.paused ? 'Paused' : 'Active'}
          </p>
        </div>
        <div style={styles.queueActions}>
          <input
            value={pauseReason}
            onChange={(event) => setPauseReason(event.target.value)}
            placeholder="Pause reason"
            style={styles.queueInput}
          />
          <button onClick={handlePauseAll} style={styles.pauseBtn}>
            {queue?.pause_all.paused ? 'Resume all' : 'Pause all'}
          </button>
        </div>
      </div>

      {loading ? (
        <div style={styles.skeleton}>
          <div style={styles.skeletonCalendar} />
        </div>
      ) : (
        <>
          {/* Calendar Grid */}
          <div style={styles.calendarCard}>
            <div style={styles.weekDaysRow}>
              {weekDays.map((day) => (
                <div key={day} style={styles.weekDayCell}>
                  {day}
                </div>
              ))}
            </div>

            <div style={styles.daysGrid}>
              {days.map((day, idx) => (
                <div
                  key={idx}
                  style={{
                    ...styles.dayCell,
                    ...(day === null ? { backgroundColor: 'var(--card)' } : {}),
                  }}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => draggingEvent && day && handleReschedule(draggingEvent, day)}
                >
                  {day && (
                    <>
                      <div style={styles.dayNumber}>{day}</div>
                      <div style={styles.eventsContainer}>
                        {getEventsForDay(day).map((event) => (
                          <div
                            key={event.id}
                            draggable
                            onDragStart={() => setDraggingEvent(event)}
                            onDragEnd={() => setDraggingEvent(null)}
                            style={{
                              ...styles.eventChip,
                              opacity: draggingEvent?.id === event.id ? 0.5 : 1,
                              cursor: 'grab',
                            }}
                            title={`${event.caption} - ${new Date(event.scheduledTime).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}`}
                          >
                            <span style={styles.eventDot}>●</span>
                            <span style={styles.eventTime}>
                              {new Date(event.scheduledTime).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Events List */}
          {events.length > 0 && (
            <div style={styles.eventsList}>
              <h2 style={styles.listTitle}>Scheduled Posts ({events.length})</h2>
              <div style={styles.eventItems}>
                {events.map((event) => (
                  <div key={event.id} style={styles.eventItem}>
                    <div style={styles.eventItemLeft}>
                      {event.mediaUrl && <img src={event.mediaUrl} alt="post" style={styles.eventItemImg} />}
                      <div style={styles.eventItemInfo}>
                        <p style={styles.eventItemCaption}>{event.caption}</p>
                        <div style={styles.eventItemMeta}>
                          <span style={styles.eventItemTime}>📅 {new Date(event.scheduledTime).toLocaleString()}</span>
                          <span style={styles.eventItemPlatforms}>{event.platforms.join(', ')}</span>
                        </div>
                      </div>
                    </div>
                    <div style={styles.eventItemRight}>
                      <label style={styles.autoPostLabel}>
                        <input
                          type="checkbox"
                          checked={event.autoPost}
                          onChange={async (e) => {
                            await socialApi.toggleAutoPost(event.id, e.target.checked);
                            setEvents(
                              events.map((ev) => (ev.id === event.id ? { ...ev, autoPost: e.target.checked } : ev))
                            );
                          }}
                        />
                        Auto-post
                      </label>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    backgroundColor: 'var(--card)',
    color: 'var(--text)',
    padding: '32px 24px',
  },
  header: {
    marginBottom: '32px',
  },
  backLink: {
    display: 'inline-block',
    marginBottom: '16px',
    color: 'var(--muted)',
    textDecoration: 'none',
    fontSize: '14px',
  },
  title: {
    fontSize: '32px',
    fontWeight: 700,
    margin: '0 0 8px',
  },
  subtitle: {
    fontSize: '14px',
    color: 'var(--muted)',
    margin: 0,
  },
  errorBanner: {
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    border: '1px solid rgba(245, 158, 11, 0.4)',
    color: '#b45309',
    padding: '12px 14px',
    borderRadius: '10px',
    marginBottom: '16px',
  },
  monthNav: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
  },
  queuePanel: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '16px',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginBottom: '24px',
    padding: '18px 20px',
    borderRadius: '16px',
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
  },
  queueTitle: {
    display: 'block',
    marginBottom: '6px',
    fontSize: '16px',
    fontWeight: 700,
  },
  queueCopy: {
    margin: 0,
    fontSize: '13px',
    color: 'var(--muted)',
  },
  queueActions: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  queueInput: {
    minWidth: '220px',
    padding: '10px 12px',
    backgroundColor: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid var(--line)',
    borderRadius: '8px',
  },
  pauseBtn: {
    padding: '10px 14px',
    backgroundColor: '#6366f1',
    color: 'var(--text)',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 600,
  },
  navBtn: {
    padding: '8px 16px',
    backgroundColor: 'var(--card)',
    color: 'var(--text)',
    border: '1px solid var(--line)',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  monthName: {
    fontSize: '20px',
    fontWeight: 600,
    margin: 0,
  },
  calendarCard: {
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: '12px',
    padding: '16px',
    marginBottom: '32px',
  },
  weekDaysRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))',
    gap: '4px',
    marginBottom: '8px',
  },
  weekDayCell: {
    padding: '12px',
    textAlign: 'center',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--muted)',
    backgroundColor: 'var(--card)',
    borderRadius: '4px',
  },
  daysGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))',
    gap: '4px',
  },
  dayCell: {
    minHeight: '100px',
    padding: '8px',
    backgroundColor: 'var(--card)',
    borderRadius: '4px',
    position: 'relative',
  },
  dayNumber: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--muted)',
    marginBottom: '4px',
  },
  eventsContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  eventChip: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 6px',
    backgroundColor: '#6366f1',
    color: 'var(--text)',
    borderRadius: '3px',
    fontSize: '11px',
    fontWeight: 500,
    userSelect: 'none',
  },
  eventDot: {
    fontSize: '11px',
  },
  eventTime: {
    fontSize: '11px',
  },
  eventsList: {
    marginTop: '32px',
  },
  listTitle: {
    fontSize: '18px',
    fontWeight: 600,
    marginBottom: '16px',
    margin: '0 0 16px',
  },
  eventItems: {
    display: 'grid',
    gap: '12px',
  },
  eventItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: '8px',
    padding: '12px',
  },
  eventItemLeft: {
    display: 'flex',
    gap: '12px',
    flex: 1,
  },
  eventItemImg: {
    width: '60px',
    height: '60px',
    borderRadius: '6px',
    objectFit: 'cover',
  },
  eventItemInfo: {
    flex: 1,
  },
  eventItemCaption: {
    margin: '0 0 6px',
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--text)',
  },
  eventItemMeta: {
    display: 'flex',
    gap: '12px',
    fontSize: '12px',
    color: 'var(--muted)',
  },
  eventItemTime: {
    whiteSpace: 'nowrap',
  },
  eventItemPlatforms: {
    color: '#6366f1',
  },
  eventItemRight: {
    display: 'flex',
    alignItems: 'center',
  },
  autoPostLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
    color: 'var(--muted)',
    cursor: 'pointer',
  },
  skeleton: {
    marginBottom: '32px',
  },
  skeletonCalendar: {
    height: '400px',
    backgroundColor: 'var(--card)',
    borderRadius: '12px',
    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
  },
};
