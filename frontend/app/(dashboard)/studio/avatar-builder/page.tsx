"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { DEFAULT_TENANT_ID, apiGet } from "@/app/lib/platform-api";

type Avatar = {
  id: string;
  name: string;
  gender: string;
  age_range: string;
  ethnicity: string;
  style: string;
  preview_url: string;
  languages: string[];
};

type AvatarCatalogResponse = {
  avatars: Avatar[];
};

const GENDERS = ["all", "female", "male"];
const STYLES = [
  "all",
  "professional",
  "casual",
  "animated",
  "lifestyle",
  "corporate",
];

export default function AvatarBuilderPage() {
  const [avatars, setAvatars] = useState<Avatar[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAvatar, setSelectedAvatar] = useState<Avatar | null>(null);
  const [genderFilter, setGenderFilter] = useState("all");
  const [styleFilter, setStyleFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  async function loadAvatars() {
    try {
      const data = await apiGet<AvatarCatalogResponse>(
        "/ai/social-studio/avatar-catalog",
        DEFAULT_TENANT_ID,
      );
      setAvatars(data.avatars ?? []);
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    globalThis.queueMicrotask(() => {
      if (active) void loadAvatars();
    });
    return () => {
      active = false;
    };
  }, []);

  const filtered = avatars.filter((a) => {
    if (genderFilter !== "all" && a.gender !== genderFilter) return false;
    if (styleFilter !== "all" && !a.style.toLowerCase().includes(styleFilter))
      return false;
    if (
      searchQuery &&
      !a.name.toLowerCase().includes(searchQuery.toLowerCase())
    )
      return false;
    return true;
  });

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--card)",
        color: "var(--text)",
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          background: "var(--card)",
          borderBottom: "1px solid var(--line)",
          padding: "20px 32px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link
            href="/studio"
            style={{
              color: "var(--muted)",
              textDecoration: "none",
              fontSize: 14,
            }}
          >
            ← Studio
          </Link>
          <span style={{ color: "var(--line)" }}>|</span>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              lineHeight: 1.2,
              margin: 0,
            }}
          >
            🧑‍💻 Avatar Builder
          </h1>
          <span
            style={{
              background: "color-mix(in oklab, var(--info) 13%, transparent)",
              color: "var(--brand)",
              fontSize: 11,
              padding: "2px 8px",
              borderRadius: 12,
              fontWeight: 600,
            }}
          >
            AI AVATAR CATALOG
          </span>
        </div>
        <Link
          href="/studio/faceless-video-engine"
          style={{
            background: "var(--brand)",
            color: "var(--on-brand)",
            padding: "8px 16px",
            borderRadius: 8,
            textDecoration: "none",
            fontSize: 13,
          }}
        >
          Use in Videos →
        </Link>
      </div>

      {/* Stats */}
      <div
        style={{
          background: "var(--card)",
          padding: "12px 32px",
          display: "flex",
          gap: 32,
          borderBottom: "1px solid var(--line)",
        }}
      >
        {[
          { label: "Total Avatars", value: `${avatars.length}` },
          {
            label: "Female",
            value: `${avatars.filter((a) => a.gender === "female").length}`,
          },
          {
            label: "Male",
            value: `${avatars.filter((a) => a.gender === "male").length}`,
          },
          { label: "Languages", value: "20+" },
        ].map((s) => (
          <div key={s.label}>
            <div
              style={{ fontSize: 18, fontWeight: 700, color: "var(--brand)" }}
            >
              {s.value}
            </div>
            <div style={{ fontSize: 11, color: "var(--muted)" }}>{s.label}</div>
          </div>
        ))}
      </div>

      <div style={{ padding: 32, maxWidth: 1200, margin: "0 auto" }}>
        {error && (
          <div
            style={{
              background:
                "color-mix(in oklab, var(--danger-soft) 20%, transparent)",
              border: "1px solid var(--danger)",
              borderRadius: 8,
              padding: 12,
              marginBottom: 16,
              color: "var(--danger)",
            }}
          >
            {error}
          </div>
        )}

        {/* Filters */}
        <div
          style={{
            display: "flex",
            gap: 12,
            marginBottom: 24,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="🔍 Search avatars…"
            style={{
              background: "var(--card)",
              border: "1px solid var(--line)",
              color: "var(--text)",
              padding: "8px 14px",
              borderRadius: 8,
              fontSize: 14,
              minWidth: 180,
            }}
          />
          <div style={{ display: "flex", gap: 6 }}>
            {GENDERS.map((g) => (
              <button
                key={g}
                onClick={() => setGenderFilter(g)}
                style={{
                  background:
                    genderFilter === g
                      ? "color-mix(in oklab, var(--info) 20%, transparent)"
                      : "var(--line-soft)",
                  border: `1px solid ${genderFilter === g ? "var(--info)" : "var(--neutral-soft)"}`,
                  color: genderFilter === g ? "var(--brand)" : "var(--muted)",
                  padding: "6px 14px",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontSize: 12,
                  textTransform: "capitalize",
                }}
              >
                {g}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {STYLES.map((s) => (
              <button
                key={s}
                onClick={() => setStyleFilter(s)}
                style={{
                  background:
                    styleFilter === s
                      ? "color-mix(in oklab, var(--warning) 20%, transparent)"
                      : "var(--line-soft)",
                  border: `1px solid ${styleFilter === s ? "var(--warning)" : "var(--neutral-soft)"}`,
                  color: styleFilter === s ? "var(--warning)" : "var(--muted)",
                  padding: "6px 14px",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontSize: 12,
                  textTransform: "capitalize",
                }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div
            style={{
              textAlign: "center",
              padding: "40px 0",
              color: "var(--muted)",
            }}
          >
            Loading avatar catalog…
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: selectedAvatar ? "1fr 360px" : "1fr",
              gap: 24,
            }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns:
                  "repeat(auto-fill, minmax(min(100%, 180px), 1fr))",
                gap: 14,
              }}
            >
              {filtered.map((avatar) => (
                <div
                  key={avatar.id}
                  onClick={() =>
                    setSelectedAvatar(
                      avatar.id === selectedAvatar?.id ? null : avatar,
                    )
                  }
                  style={{
                    background:
                      selectedAvatar?.id === avatar.id
                        ? "#1a1f3a"
                        : "var(--line-soft)",
                    border: `2px solid ${selectedAvatar?.id === avatar.id ? "var(--info)" : "var(--neutral-soft)"}`,
                    borderRadius: 16,
                    padding: 16,
                    cursor: "pointer",
                    textAlign: "center",
                    transition:
                      "background-color 150ms ease, border-color 150ms ease",
                  }}
                >
                  <div
                    style={{
                      width: 80,
                      height: 80,
                      borderRadius: "50%",
                      background: `url(${avatar.preview_url}) center/cover`,
                      margin: "0 auto 10px",
                      border: `3px solid ${selectedAvatar?.id === avatar.id ? "var(--info)" : "var(--neutral-soft)"}`,
                    }}
                  />
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 700,
                      color:
                        selectedAvatar?.id === avatar.id
                          ? "var(--brand)"
                          : "var(--text)",
                      marginBottom: 2,
                    }}
                  >
                    {avatar.name}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--muted)",
                      marginBottom: 4,
                    }}
                  >
                    {avatar.gender} · {avatar.age_range}
                  </div>
                  <span
                    style={{
                      background: "var(--neutral-soft)",
                      color: "var(--ink-2)",
                      fontSize: 10,
                      padding: "2px 8px",
                      borderRadius: 10,
                    }}
                  >
                    {avatar.style}
                  </span>
                  <div
                    style={{
                      fontSize: 10,
                      color: "var(--brand)",
                      marginTop: 6,
                    }}
                  >
                    {avatar.languages.slice(0, 4).join(", ")}
                    {avatar.languages.length > 4
                      ? ` +${avatar.languages.length - 4}`
                      : ""}
                  </div>
                </div>
              ))}
              {filtered.length === 0 && (
                <div
                  style={{
                    gridColumn: "1/-1",
                    textAlign: "center",
                    padding: "40px 0",
                    color: "var(--muted)",
                  }}
                >
                  No avatars match your filters.
                </div>
              )}
            </div>

            {/* Avatar Detail Panel */}
            {selectedAvatar && (
              <div
                style={{
                  position: "sticky",
                  top: 24,
                  alignSelf: "start",
                  background: "var(--card)",
                  border: "1px solid var(--line)",
                  borderRadius: 16,
                  padding: 24,
                }}
              >
                <div
                  style={{
                    width: 120,
                    height: 120,
                    borderRadius: "50%",
                    background: `url(${selectedAvatar.preview_url}) center/cover`,
                    margin: "0 auto 16px",
                    border: "3px solid var(--brand)",
                  }}
                />
                <div
                  style={{
                    fontSize: 22,
                    fontWeight: 700,
                    textAlign: "center",
                    marginBottom: 4,
                  }}
                >
                  {selectedAvatar.name}
                </div>
                <div
                  style={{
                    fontSize: 13,
                    color: "var(--muted)",
                    textAlign: "center",
                    marginBottom: 16,
                  }}
                >
                  {selectedAvatar.ethnicity} · {selectedAvatar.age_range} ·{" "}
                  {selectedAvatar.gender}
                </div>

                <div style={{ marginBottom: 16 }}>
                  <div
                    style={{
                      fontSize: 12,
                      color: "var(--muted)",
                      marginBottom: 6,
                      fontWeight: 600,
                    }}
                  >
                    STYLE
                  </div>
                  <span
                    style={{
                      background:
                        "color-mix(in oklab, var(--info) 20%, transparent)",
                      color: "var(--brand)",
                      padding: "4px 12px",
                      borderRadius: 16,
                      fontSize: 13,
                    }}
                  >
                    {selectedAvatar.style}
                  </span>
                </div>

                <div style={{ marginBottom: 20 }}>
                  <div
                    style={{
                      fontSize: 12,
                      color: "var(--muted)",
                      marginBottom: 6,
                      fontWeight: 600,
                    }}
                  >
                    SUPPORTED LANGUAGES ({selectedAvatar.languages.length})
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {selectedAvatar.languages.map((lang) => (
                      <span
                        key={lang}
                        style={{
                          background: "var(--line)",
                          color: "var(--text)",
                          fontSize: 11,
                          padding: "2px 8px",
                          borderRadius: 10,
                        }}
                      >
                        {lang.toUpperCase()}
                      </span>
                    ))}
                  </div>
                </div>

                <Link
                  href="/studio/faceless-video-engine"
                  style={{
                    display: "block",
                    background: "var(--brand)",
                    color: "var(--on-brand)",
                    padding: "12px 0",
                    borderRadius: 10,
                    textDecoration: "none",
                    textAlign: "center",
                    fontSize: 14,
                    fontWeight: 700,
                    marginBottom: 10,
                  }}
                >
                  🎬 Create Video with {selectedAvatar.name}
                </Link>
                <button
                  onClick={() => setSelectedAvatar(null)}
                  style={{
                    width: "100%",
                    background: "var(--line)",
                    color: "var(--text)",
                    border: "none",
                    padding: "10px 0",
                    borderRadius: 10,
                    cursor: "pointer",
                    fontSize: 13,
                  }}
                >
                  Deselect
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
