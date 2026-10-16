"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { apiGet, apiSend } from "@/app/lib/platform-api";
import { Button, ButtonLink, Callout, Card, Field, IconButton, Modal, Page, PageHeader, StatusBadge } from "../../../_ui/kit";
import { fromLocalInputValue, toLocalInputValue } from "../../../_ui/format";
import { ResourceView, useResource, useTenant } from "../../../_ui/use-resource";
import { platformLabel } from "../_lib/social";
import styles from "./calendar.module.css";

type CalendarItem = {
  id: string;
  title: string;
  platforms: string[];
  scheduled_for: string;
  status: string;
};

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function dayKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

/** Monday-first grid of dates covering the whole month, padded with neighbouring days. */
function monthGrid(year: number, month: number): Date[] {
  const first = new Date(year, month - 1, 1);
  const offset = (first.getDay() + 6) % 7;
  const start = new Date(year, month - 1, 1 - offset);
  const total = Math.ceil((offset + new Date(year, month, 0).getDate()) / 7) * 7;
  return Array.from({ length: total }, (_, index) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + index));
}

export default function ContentCalendarPage() {
  const tenant = useTenant();
  const today = new Date();
  const [cursor, setCursor] = useState({ year: today.getFullYear(), month: today.getMonth() + 1 });
  const resource = useResource<CalendarItem[]>(
    async (id) => {
      const res = await apiGet<{ items?: CalendarItem[] }>(`/social/calendar?month=${cursor.month}&year=${cursor.year}`, id);
      return res.items ?? [];
    },
    [cursor.month, cursor.year],
  );

  const [selected, setSelected] = useState<CalendarItem | null>(null);
  const [moveTo, setMoveTo] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const byDay = useMemo(() => {
    const map = new Map<string, CalendarItem[]>();
    for (const item of resource.data ?? []) {
      const key = dayKey(new Date(item.scheduled_for));
      map.set(key, [...(map.get(key) ?? []), item]);
    }
    return map;
  }, [resource.data]);

  const cells = useMemo(() => monthGrid(cursor.year, cursor.month), [cursor]);
  const label = new Date(cursor.year, cursor.month - 1, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });

  function shift(delta: number) {
    const next = new Date(cursor.year, cursor.month - 1 + delta, 1);
    setCursor({ year: next.getFullYear(), month: next.getMonth() + 1 });
  }

  async function reschedule() {
    const iso = fromLocalInputValue(moveTo);
    if (!selected || !iso) return setError("Choose a valid date and time.");
    setSaving(true);
    setError(null);
    try {
      await apiSend(`/social/calendar/${selected.id}/move`, "PUT", { new_scheduled_time: iso }, tenant);
      setSelected(null);
      await resource.reload();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "The post could not be moved.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Page width="wide">
      <PageHeader
        title="Content Calendar"
        subtitle="See your planned posts by day and move them. Nuxtron keeps the plan; it does not publish for you."
        actions={<ButtonLink href="/studio/social-studio/posts" variant="primary">Plan a post</ButtonLink>}
      />

      <Card pad={false}>
        <div className={styles.bar}>
          <div className={styles.nav}>
            <IconButton label="Previous month" onClick={() => shift(-1)}>
              <ChevronLeft size={16} aria-hidden="true" />
            </IconButton>
            <h2 className={styles.month}>{label}</h2>
            <IconButton label="Next month" onClick={() => shift(1)}>
              <ChevronRight size={16} aria-hidden="true" />
            </IconButton>
          </div>
          <Button size="sm" onClick={() => setCursor({ year: today.getFullYear(), month: today.getMonth() + 1 })}>
            Today
          </Button>
        </div>
        <ResourceView resource={resource}>
          {(items) => (
            <>
              <div className={styles.grid} role="grid" aria-label={label}>
                {WEEKDAYS.map((name) => (
                  <div key={name} className={styles.weekday} role="columnheader">
                    {name}
                  </div>
                ))}
                {cells.map((date) => {
                  const key = dayKey(date);
                  const inMonth = date.getMonth() === cursor.month - 1;
                  const isToday = key === dayKey(today);
                  const dayItems = byDay.get(key) ?? [];
                  return (
                    <div key={key} className={`${styles.cell} ${inMonth ? "" : styles.outside}`} role="gridcell" aria-label={date.toDateString()}>
                      <span className={`${styles.date} ${isToday ? styles.today : ""}`}>{date.getDate()}</span>
                      {dayItems.slice(0, 3).map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          className={styles.chip}
                          onClick={() => {
                            setSelected(item);
                            setMoveTo(toLocalInputValue(new Date(item.scheduled_for)));
                            setError(null);
                          }}
                        >
                          <span className={styles.time}>
                            {new Date(item.scheduled_for).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}
                          </span>
                          <span className={styles.chipText}>{item.title}</span>
                        </button>
                      ))}
                      {dayItems.length > 3 ? <span className={styles.more}>+{dayItems.length - 3} more</span> : null}
                    </div>
                  );
                })}
              </div>
              {items.length === 0 ? <p className={styles.empty}>No posts are planned for {label}.</p> : null}
            </>
          )}
        </ResourceView>
      </Card>

      <Modal
        open={Boolean(selected)}
        onOpenChange={(open) => !open && setSelected(null)}
        title="Planned post"
        description={selected ? `${selected.platforms.map(platformLabel).join(", ")}` : undefined}
        footer={
          <>
            <Button onClick={() => setSelected(null)} disabled={saving}>
              Close
            </Button>
            <Button variant="primary" loading={saving} onClick={() => void reschedule()}>
              Move post
            </Button>
          </>
        }
      >
        {selected ? (
          <div style={{ display: "grid", gap: 14 }}>
            {error ? <Callout tone="danger">{error}</Callout> : null}
            <p style={{ margin: 0 }}>{selected.title}</p>
            <StatusBadge status={selected.status} />
            <Field label="Planned for" type="datetime-local" value={moveTo} onChange={(event) => setMoveTo(event.target.value)} />
          </div>
        ) : null}
      </Modal>
    </Page>
  );
}
