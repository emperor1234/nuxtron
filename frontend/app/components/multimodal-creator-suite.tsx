'use client';

import { useMemo, useState } from 'react';

type CreativeMode =
  | 'single-image-silent'
  | 'single-image-voice'
  | 'multi-image-silent'
  | 'multi-image-voice'
  | 'promo-image'
  | 'ad-image'
  | 'influencer-image'
  | 'video'
  | 'text'
  | 'voice';

type ModuleType = 'social-studio' | 'ads-engine';

export type CreatorSuiteConfig = {
  creativeMode: CreativeMode;
  promptDescription: string;
  aspectRatio: string;
  resolution: string;
  model: string;
  containsRealPeople: boolean;
  returnLastFrame: boolean;
  seedEnabled: boolean;
  seedValue: string;
  referenceImageNames: string[];
  referenceVideoNames: string[];
  referenceAudioNames: string[];
  referenceImageFiles: File[];
  referenceVideoFiles: File[];
  referenceAudioFiles: File[];
  portrait: {
    gender: 'male' | 'female' | 'all';
    country: string;
    ageBand: AgeBand;
    totalAvatars: number;
  };
};

type Props = {
  moduleType: ModuleType;
  onApplyConfig?: (config: CreatorSuiteConfig) => void;
};

type AgeBand = '18-30' | '31-40' | '41-50' | '51-60' | '61-70' | '71-80' | '81-90' | '91-100' | '100+';

const CREATIVE_MODES: Array<{ value: CreativeMode; label: string }> = [
  { value: 'single-image-silent', label: 'Single image without voice/sound' },
  { value: 'single-image-voice', label: 'Single image with voice/sound' },
  { value: 'multi-image-silent', label: 'Multiple images without voice/sound' },
  { value: 'multi-image-voice', label: 'Multiple images with voice/sound' },
  { value: 'promo-image', label: 'Promotional image' },
  { value: 'ad-image', label: 'Ad image' },
  { value: 'influencer-image', label: 'Influencer image' },
  { value: 'video', label: 'Video' },
  { value: 'text', label: 'Text' },
  { value: 'voice', label: 'Voice' },
];

const EDIT_TOOLS = [
  'Shadow',
  'Text',
  'Fonts',
  'Shapes',
  'Brushes',
  'Panels',
  'Layer',
  'Background removal',
  'Auto lighting',
  'Auto product enhancement',
  'Hue',
  'Distort',
  'Sharpness',
  'Colour',
  'Brightness',
  'Resize',
  'Rotate',
  'Flip',
  'Cutting tool',
  'Multi colour gradient',
  'Texture',
];

const ASPECT_RATIOS = ['Auto', '16:9', '9:16', '4:3', '3:4', '21:9', '1:1'];
const RESOLUTIONS = ['480p', '720p', '1080p', '1440p', '4K'];
const AI_MODELS = ['Auto choose model', 'SDXL', 'Flux Pro', 'Imagen', 'Runway', 'ElevenLabs', 'Claude', 'GPT'];
const AGE_BANDS: AgeBand[] = ['18-30', '31-40', '41-50', '51-60', '61-70', '71-80', '81-90', '91-100', '100+'];
const MODEL_MENU_OPTIONS = [
  {
    name: 'Seedance 2.0',
    description: 'Multimodal input with powerful reference capabilities',
    badges: ['With Audio'],
  },
  {
    name: 'Seedance 2.0 Fast',
    description: 'Faster generation with multimodal reference support',
    badges: ['With Audio'],
  },
  {
    name: 'Seedance 1.5 Pro',
    description: 'Joint audio-video with multilingual lip-sync',
    badges: ['With Audio'],
  },
  {
    name: 'Seedance 1.0',
    description: 'Advanced model with smooth, stable motion',
    badges: [],
  },
  {
    name: 'Veo 3.1',
    description: "Google's latest video model with native audio",
    badges: ['With Audio', 'Multi-image'],
  },
] as const;
const COUNTRY_OPTIONS = [
  'All',
  'Armenia',
  'Australia',
  'Austria',
  'Azerbaijan',
  'Bangladesh',
  'Benin',
  'Bhutan',
  'Bolivia',
  'Botswana',
  'Brazil',
  'China',
  'India',
  'Indonesia',
  'Japan',
  'Netherlands',
  'South Africa',
  'South Korea',
  'Spain',
  'UK',
  'USA',
];

function sectionTitle(moduleType: ModuleType): string {
  return moduleType === 'social-studio' ? 'AI Social Studio Multimodal Suite' : 'AI Ads Engine Multimodal Suite';
}

function capabilityList() {
  return [
    'Collaboration at scale: multi-user editing, version control, commenting/review workflows',
    'AI automation: auto editing, speech-to-text captions, content generation',
    'Cloud & remote workflows: browser editing, shared storage/access control, remote team editing',
    'Brand & governance controls: templates, brand kits, permissions, compliance + security',
    'Integration ecosystem: APIs, DAM/CMS/marketing tool integrations',
    'Enterprise browser editing: low-bandwidth remote workflows and scalable org access',
    'AI avatars + auto translations (125+ languages), subtitles, voice cloning, screen recording',
    'Edit video like a document, filler-word removal, auto multicam, studio audio cleanup',
    'Hollywood-level grading, VFX/audio pipelines, shared timelines, live stream editing',
    'AI scene detection, object tracking, facial analysis, generative edits',
  ];
}

function computeUsedCredits(resolution: string, creativeMode: string, containsRealPeople: boolean): number {
  let credits = 30;
  if (resolution === '4K') credits += 25;
  if (resolution === '1440p') credits += 12;
  if (creativeMode.includes('multi-image')) credits += 10;
  if (creativeMode === 'video') credits += 18;
  if (creativeMode === 'voice') credits += 9;
  if (containsRealPeople) credits += 8;
  return credits;
}

function filterCountries(query: string): string[] {
  const q = query.trim().toLowerCase();
  if (!q) return COUNTRY_OPTIONS;
  return COUNTRY_OPTIONS.filter((country) => country.toLowerCase().includes(q));
}

export default function MultimodalCreatorSuite({ moduleType, onApplyConfig }: Props) {
  // NOSONAR
  const [creativeMode, setCreativeMode] = useState<CreativeMode>('single-image-silent');
  const [promptDescription, setPromptDescription] = useState('');
  const [aspectRatio, setAspectRatio] = useState('Auto');
  const [resolution, setResolution] = useState('1080p');
  const [durationSeconds, setDurationSeconds] = useState(5);
  const [videoInputMode, setVideoInputMode] = useState<'multi-references' | 'image-to-video' | 'text-to-video'>(
    'multi-references'
  );
  const [model, setModel] = useState('Auto choose model');
  const [showVideoModelMenu, setShowVideoModelMenu] = useState(false);
  const [containsRealPeople, setContainsRealPeople] = useState(false);
  const [returnLastFrame, setReturnLastFrame] = useState(true);
  const [seedEnabled, setSeedEnabled] = useState(false);
  const [seedValue, setSeedValue] = useState('');
  const [availableCredits] = useState(1240);

  const [referenceImages, setReferenceImages] = useState<File[]>([]);
  const [referenceVideos, setReferenceVideos] = useState<File[]>([]);
  const [referenceAudios, setReferenceAudios] = useState<File[]>([]);

  const [showPortraitLibrary, setShowPortraitLibrary] = useState(false);
  const [portraitGender, setPortraitGender] = useState<'male' | 'female' | 'all'>('all');
  const [portraitCountry, setPortraitCountry] = useState('All');
  const [portraitCountrySearch, setPortraitCountrySearch] = useState('');
  const [showCountryMenu, setShowCountryMenu] = useState(false);
  const [portraitAgeBand, setPortraitAgeBand] = useState<AgeBand>('18-30');
  const [portraitCount, setPortraitCount] = useState(24);

  const remainingImageSlots = Math.max(0, 9 - referenceImages.length);
  const remainingVideoSlots = Math.max(0, 3 - referenceVideos.length);
  const remainingAudioSlots = Math.max(0, 3 - referenceAudios.length);
  const isVideoMode = creativeMode === 'video';
  const filteredCountries = useMemo(() => filterCountries(portraitCountrySearch), [portraitCountrySearch]);

  const usedCredits = useMemo(
    () => computeUsedCredits(resolution, creativeMode, containsRealPeople),
    [containsRealPeople, creativeMode, resolution]
  );

  function handleImageUpload(files: FileList | null) {
    if (!files) return;
    const next = Array.from(files).slice(0, remainingImageSlots);
    setReferenceImages((prev) => [...prev, ...next]);
  }

  function handleVideoUpload(files: FileList | null) {
    if (!files) return;
    const next = Array.from(files).slice(0, remainingVideoSlots);
    setReferenceVideos((prev) => [...prev, ...next]);
  }

  function handleAudioUpload(files: FileList | null) {
    if (!files) return;
    const next = Array.from(files).slice(0, remainingAudioSlots);
    setReferenceAudios((prev) => [...prev, ...next]);
  }

  function setRandomSeed() {
    const randomSeed = Math.floor(Math.random() * 1_000_000_000);
    setSeedValue(String(randomSeed));
    setSeedEnabled(true);
  }

  function getReferencePreviewContent() {
    if (referenceVideos.length > 0) {
      return (
        <>
          <p style={{ margin: 0, fontSize: 13, fontWeight: 700 }}>Video Reference Ready</p>
          <p style={{ margin: '6px 0 0', fontSize: 12, color: 'var(--muted)' }}>{referenceVideos[0].name}</p>
        </>
      );
    }
    if (referenceImages.length > 0) {
      return (
        <>
          <p style={{ margin: 0, fontSize: 13, fontWeight: 700 }}>Image Reference</p>
          <p style={{ margin: '6px 0 0', fontSize: 12, color: 'var(--muted)' }}>{referenceImages[0].name}</p>
        </>
      );
    }
    return (
      <>
        <p style={{ margin: 0, fontSize: 13, fontWeight: 700 }}>Video Preview</p>
        <p style={{ margin: '6px 0 0', fontSize: 12, color: 'var(--muted)' }}>
          Upload references or generate to preview output here.
        </p>
      </>
    );
  }

  function applyConfigToParent() {
    if (!onApplyConfig) return;
    onApplyConfig({
      creativeMode,
      promptDescription,
      aspectRatio,
      resolution,
      model,
      containsRealPeople,
      returnLastFrame,
      seedEnabled,
      seedValue,
      referenceImageNames: referenceImages.map((file) => file.name),
      referenceVideoNames: referenceVideos.map((file) => file.name),
      referenceAudioNames: referenceAudios.map((file) => file.name),
      referenceImageFiles: [...referenceImages],
      referenceVideoFiles: [...referenceVideos],
      referenceAudioFiles: [...referenceAudios],
      portrait: {
        gender: portraitGender,
        country: portraitCountry,
        ageBand: portraitAgeBand,
        totalAvatars: portraitCount,
      },
    });
  }

  return (
    <section className="card" style={{ padding: 20, marginTop: 20 }}>
      <div
        style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}
      >
        <div>
          <h3 style={{ margin: 0 }}>{sectionTitle(moduleType)}</h3>
          <p style={{ margin: '6px 0 0', color: 'var(--muted)' }}>
            End-to-end image, video, voice, and text generation suite with enterprise collaboration and governance.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowPortraitLibrary(true)}
          style={{
            borderRadius: 8,
            border: '1px solid var(--line)',
            background: 'transparent',
            color: 'var(--brand)',
            padding: '8px 12px',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          Open Virtual Portrait Library
        </button>
      </div>

      {isVideoMode ? (
        <div
          style={{
            marginTop: 18,
            display: 'grid',
            gridTemplateColumns: 'minmax(320px, 0.92fr) minmax(420px, 1.08fr)',
            gap: 18,
          }}
        >
          <div style={{ display: 'grid', gap: 12, alignContent: 'start' }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {[
                { value: 'multi-references', label: 'Multi References' },
                { value: 'image-to-video', label: 'Image to Video' },
                { value: 'text-to-video', label: 'Text to Video' },
              ].map((tab) => {
                const active = videoInputMode === tab.value;
                return (
                  <button
                    key={tab.value}
                    type="button"
                    onClick={() =>
                      setVideoInputMode(tab.value as 'multi-references' | 'image-to-video' | 'text-to-video')
                    }
                    style={{
                      borderRadius: 10,
                      border: active ? '1px solid rgba(255,255,255,0.24)' : '1px solid rgba(255,255,255,0.08)',
                      background: active ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.02)',
                      color: 'var(--text)',
                      padding: '8px 12px',
                      fontSize: 12,
                      cursor: 'pointer',
                    }}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>

            <div
              style={{
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 14,
                padding: 14,
                background: 'rgba(255,255,255,0.02)',
              }}
            >
              <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>AI Model</p>
              <div style={{ position: 'relative', marginTop: 8 }}>
                <button
                  type="button"
                  onClick={() => setShowVideoModelMenu((value) => !value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: 10,
                    border: '1px solid rgba(255,255,255,0.08)',
                    background: '#111318',
                    color: 'var(--text)',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <span style={{ display: 'block', fontSize: 13, fontWeight: 700 }}>
                    {model === 'Auto choose model' ? 'Seedance 2.0' : model}
                  </span>
                  <span style={{ display: 'block', marginTop: 4, fontSize: 11, color: 'var(--muted)' }}>
                    Multimodal input with powerful reference capabilities
                  </span>
                </button>
                {showVideoModelMenu ? (
                  <div
                    style={{
                      position: 'absolute',
                      left: 0,
                      right: 0,
                      top: 'calc(100% + 8px)',
                      zIndex: 20,
                      borderRadius: 12,
                      border: '1px solid rgba(255,255,255,0.08)',
                      background: '#0f1014',
                      boxShadow: '0 20px 60px rgba(0,0,0,0.35)',
                      overflow: 'hidden',
                    }}
                  >
                    {MODEL_MENU_OPTIONS.map((option) => (
                      <button
                        key={option.name}
                        type="button"
                        onClick={() => {
                          setModel(option.name);
                          setShowVideoModelMenu(false);
                        }}
                        style={{
                          width: '100%',
                          border: 'none',
                          borderBottom: '1px solid rgba(255,255,255,0.06)',
                          background: 'transparent',
                          color: 'var(--text)',
                          padding: '12px 14px',
                          cursor: 'pointer',
                          textAlign: 'left',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'start' }}>
                          <div>
                            <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                              <span style={{ fontSize: 13, fontWeight: 700 }}>{option.name}</span>
                              {option.badges.map((badge) => (
                                <span
                                  key={badge}
                                  style={{
                                    borderRadius: 999,
                                    background: 'rgba(255,255,255,0.08)',
                                    padding: '2px 7px',
                                    fontSize: 10,
                                    color: 'rgba(255,255,255,0.82)',
                                  }}
                                >
                                  {badge}
                                </span>
                              ))}
                            </div>
                            <p style={{ margin: '5px 0 0', fontSize: 11, color: 'var(--muted)' }}>
                              {option.description}
                            </p>
                          </div>
                          <span style={{ fontSize: 12, opacity: model === option.name ? 1 : 0.2 }}>✓</span>
                        </div>
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>

            <div style={{ display: 'grid', gap: 10 }}>
              <div
                style={{
                  border: '1px dashed rgba(255,255,255,0.1)',
                  borderRadius: 14,
                  padding: 14,
                  background: '#17181c',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                  <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Reference Images (max 9)</p>
                  <button
                    type="button"
                    onClick={() => setShowPortraitLibrary(true)}
                    style={{
                      borderRadius: 999,
                      border: '1px solid rgba(111,86,255,0.35)',
                      background: 'rgba(111,86,255,0.16)',
                      color: '#c6b7ff',
                      padding: '4px 10px',
                      fontSize: 11,
                      cursor: 'pointer',
                    }}
                  >
                    Select Virtual Portrait
                  </button>
                </div>
                <p style={{ margin: '6px 0 0', fontSize: 11, color: 'var(--muted)' }}>
                  Click to upload images png, jpg, jpeg, webp ({remainingImageSlots} remaining)
                </p>
                <input
                  type="file"
                  accept=".png,.jpg,.jpeg,.webp"
                  multiple
                  onChange={(event) => handleImageUpload(event.target.files)}
                  style={{ marginTop: 10, width: '100%' }}
                />
              </div>

              <div
                style={{
                  border: '1px dashed rgba(255,255,255,0.1)',
                  borderRadius: 14,
                  padding: 14,
                  background: '#17181c',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                  <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Reference Videos (max 3, total 15s)</p>
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>00/15s</span>
                </div>
                <p style={{ margin: '6px 0 0', fontSize: 11, color: 'var(--muted)' }}>
                  Click to upload videos mp4, mov ({remainingVideoSlots} remaining)
                </p>
                <input
                  type="file"
                  accept=".mp4,.mov"
                  multiple
                  onChange={(event) => handleVideoUpload(event.target.files)}
                  style={{ marginTop: 10, width: '100%' }}
                />
              </div>

              <div
                style={{
                  border: '1px dashed rgba(255,255,255,0.1)',
                  borderRadius: 14,
                  padding: 14,
                  background: '#17181c',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                  <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Reference Audios (max 3, total 15s)</p>
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>00/15s</span>
                </div>
                <p style={{ margin: '6px 0 0', fontSize: 11, color: 'var(--muted)' }}>
                  Click to upload audio mp3, wav ({remainingAudioSlots} remaining)
                </p>
                <input
                  type="file"
                  accept=".mp3,.wav"
                  multiple
                  onChange={(event) => handleAudioUpload(event.target.files)}
                  style={{ marginTop: 10, width: '100%' }}
                />
              </div>
            </div>

            <label
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: 12,
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 12,
                padding: '10px 12px',
                background: '#17181c',
              }}
            >
              <span style={{ fontSize: 12 }}>Contains Real People</span>
              <input
                type="checkbox"
                checked={containsRealPeople}
                onChange={(event) => setContainsRealPeople(event.target.checked)}
              />
            </label>

            <label
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: 12,
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 12,
                padding: '10px 12px',
                background: '#17181c',
              }}
            >
              <span style={{ fontSize: 12 }}>Return Last Frame</span>
              <input
                type="checkbox"
                checked={returnLastFrame}
                onChange={(event) => setReturnLastFrame(event.target.checked)}
              />
            </label>

            <div
              style={{
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 12,
                padding: 12,
                background: '#17181c',
              }}
            >
              <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Prompt</p>
              <textarea
                value={promptDescription}
                onChange={(event) => setPromptDescription(event.target.value.slice(0, 5000))}
                placeholder="Type @ to reference uploaded materials, e.g. @Image1 as first frame..."
                rows={5}
                style={{
                  width: '100%',
                  marginTop: 8,
                  padding: 10,
                  borderRadius: 10,
                  border: '1px solid rgba(255,255,255,0.08)',
                  background: '#101115',
                  color: 'var(--text)',
                  resize: 'vertical',
                }}
              />
              <p style={{ margin: '6px 0 0', fontSize: 11, color: 'var(--muted)', textAlign: 'right' }}>
                {promptDescription.length}/5000
              </p>
            </div>

            <div>
              <p style={{ margin: '0 0 8px', fontSize: 12, fontWeight: 700 }}>Resolution</p>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {RESOLUTIONS.slice(0, 3).map((item) => {
                  const active = resolution === item;
                  return (
                    <button
                      key={item}
                      type="button"
                      onClick={() => setResolution(item)}
                      style={{
                        borderRadius: 10,
                        border: active ? '1px solid rgba(255,255,255,0.22)' : '1px solid rgba(255,255,255,0.08)',
                        background: active ? 'rgba(255,255,255,0.08)' : '#17181c',
                        color: 'var(--text)',
                        padding: '8px 14px',
                        fontSize: 12,
                        cursor: 'pointer',
                      }}
                    >
                      {item}
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Duration</p>
                <span style={{ fontSize: 12, color: 'var(--muted)' }}>{durationSeconds}s</span>
              </div>
              <input
                type="range"
                min={1}
                max={15}
                value={durationSeconds}
                onChange={(event) => setDurationSeconds(Number(event.target.value))}
                style={{ width: '100%', marginTop: 8 }}
              />
            </div>

            <div>
              <p style={{ margin: '0 0 8px', fontSize: 12, fontWeight: 700 }}>Aspect Ratio</p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 8 }}>
                {ASPECT_RATIOS.map((ratio) => {
                  const active = aspectRatio === ratio;
                  return (
                    <button
                      key={ratio}
                      type="button"
                      onClick={() => setAspectRatio(ratio)}
                      style={{
                        borderRadius: 12,
                        border: active ? '1px solid rgba(255,255,255,0.25)' : '1px solid rgba(255,255,255,0.08)',
                        background: active ? 'rgba(255,255,255,0.08)' : '#17181c',
                        color: 'var(--text)',
                        padding: '12px 8px',
                        minHeight: 58,
                        fontSize: 11,
                        cursor: 'pointer',
                      }}
                    >
                      {ratio}
                    </button>
                  );
                })}
              </div>
            </div>

            <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 10 }}>
              <button
                type="button"
                onClick={setRandomSeed}
                style={{
                  width: '100%',
                  borderRadius: 12,
                  border: '1px solid rgba(255,255,255,0.08)',
                  background: '#17181c',
                  color: 'var(--text)',
                  padding: '8px 12px',
                  cursor: 'pointer',
                }}
              >
                Advanced
              </button>
              <div style={{ marginTop: 8, display: 'grid', gap: 8 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                  <input
                    type="checkbox"
                    checked={seedEnabled}
                    onChange={(event) => setSeedEnabled(event.target.checked)}
                  />{' '}
                  Seed
                </label>
                <input
                  disabled={!seedEnabled}
                  value={seedValue}
                  onChange={(event) => setSeedValue(event.target.value.replaceAll(/\D/g, '').slice(0, 12))}
                  placeholder="Choose any number"
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: 10,
                    border: '1px solid rgba(255,255,255,0.08)',
                    background: '#101115',
                    color: 'var(--text)',
                  }}
                />
              </div>
            </div>

            <div>
              {onApplyConfig ? (
                <button
                  type="button"
                  onClick={applyConfigToParent}
                  style={{
                    width: '100%',
                    borderRadius: 12,
                    border: 'none',
                    background: 'linear-gradient(90deg, #6d5efc, #8a38ff)',
                    color: '#fff',
                    padding: '12px 14px',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Generate
                </button>
              ) : null}
              <p style={{ margin: '8px 0 0', fontSize: 11, color: 'var(--muted)', textAlign: 'center' }}>
                Cost: {usedCredits} credits | Available: {availableCredits}
              </p>
            </div>
          </div>

          <div style={{ display: 'grid', gap: 14, alignContent: 'start' }}>
            <div
              style={{
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 18,
                padding: 14,
                background: 'rgba(255,255,255,0.03)',
              }}
            >
              <div
                style={{
                  borderRadius: 14,
                  minHeight: 360,
                  background: 'radial-gradient(circle at top, rgba(91,103,255,0.16), rgba(13,13,16,0.92) 58%)',
                  display: 'grid',
                  placeItems: 'center',
                  overflow: 'hidden',
                }}
              >
                <div style={{ textAlign: 'center' }}>{getReferencePreviewContent()}</div>
              </div>
            </div>

            <div
              style={{
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 14,
                padding: 14,
                background: '#17181c',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Multi Reference Guide</p>
                <span
                  style={{
                    borderRadius: 999,
                    border: '1px solid rgba(255,255,255,0.08)',
                    padding: '4px 8px',
                    fontSize: 11,
                    color: 'var(--muted)',
                  }}
                >
                  Full Guide
                </span>
              </div>
              <div
                style={{
                  marginTop: 10,
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 10,
                  padding: 10,
                  background: '#111318',
                }}
              >
                <p style={{ margin: 0, fontSize: 11, color: 'var(--muted)' }}>Prompt Guide</p>
                <p style={{ margin: '6px 0 0', fontSize: 12 }}>
                  Type @ to quickly insert uploaded file refs inside the prompt. Supported: @Image1, @Video1, @Audio1.
                </p>
              </div>
              <div style={{ marginTop: 12, display: 'grid', gap: 10 }}>
                <div>
                  <p style={{ margin: 0, fontSize: 11, fontWeight: 700 }}>Material Limits</p>
                  <ul style={{ margin: '6px 0 0', paddingLeft: 18, fontSize: 12, color: 'var(--muted)' }}>
                    <li>Up to 9 reference images</li>
                    <li>Up to 3 reference videos, total duration 15 seconds</li>
                    <li>Up to 3 reference audios, total duration 15 seconds</li>
                    <li>Maximum 12 material slots across all types</li>
                  </ul>
                </div>
                <div>
                  <p style={{ margin: 0, fontSize: 11, fontWeight: 700 }}>Supported Input Combinations</p>
                  <ul style={{ margin: '6px 0 0', paddingLeft: 18, fontSize: 12, color: 'var(--muted)' }}>
                    <li>Text + Image</li>
                    <li>Text + Video</li>
                    <li>Text + Image + Video</li>
                    <li>Text + Image + Audio</li>
                    <li>Text + Video + Audio</li>
                    <li>Text + Image + Video + Audio</li>
                  </ul>
                  <p style={{ margin: '6px 0 0', fontSize: 11, color: 'var(--muted)' }}>
                    Note: audio can be used alone with text, or combined with at least one image or video reference.
                  </p>
                </div>
              </div>
            </div>

            <div
              style={{
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 14,
                padding: 14,
                background: 'linear-gradient(180deg, rgba(15,20,48,0.88), rgba(9,12,28,0.96))',
              }}
            >
              <h4 style={{ margin: 0, textAlign: 'center', color: '#5ea0ff' }}>Get Inspired</h4>
              <p style={{ margin: '8px 0 0', textAlign: 'center', fontSize: 12, color: 'rgba(255,255,255,0.72)' }}>
                Explore multimodal video examples created with the current reference workflow.
              </p>
              <div
                style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 10, marginTop: 12 }}
              >
                {['Brand reel', 'Angel motion', 'Promo shot', 'Ambient loop'].map((item) => (
                  <div
                    key={item}
                    style={{
                      borderRadius: 12,
                      minHeight: 100,
                      background: 'linear-gradient(135deg, rgba(255,255,255,0.14), rgba(255,255,255,0.04))',
                      display: 'grid',
                      placeItems: 'center',
                      fontSize: 12,
                      color: 'rgba(255,255,255,0.8)',
                    }}
                  >
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {isVideoMode ? (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 14, marginTop: 16 }}>
            <div>
              <label
                htmlFor="creative-mode"
                style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 6 }}
              >
                Creative Mode
              </label>
              <select
                id="creative-mode"
                value={creativeMode}
                onChange={(event) => setCreativeMode(event.target.value as CreativeMode)}
                style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid var(--line)' }}
              >
                {CREATIVE_MODES.map((mode) => (
                  <option key={mode.value} value={mode.value}>
                    {mode.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="ai-model" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 6 }}>
                AI Model
              </label>
              <select
                id="ai-model"
                value={model}
                onChange={(event) => setModel(event.target.value)}
                style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid var(--line)' }}
              >
                {AI_MODELS.map((modelOption) => (
                  <option key={modelOption} value={modelOption}>
                    {modelOption}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ marginTop: 12 }}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 6 }}>
              Prompt Description ({promptDescription.length}/5000)
            </label>
            <textarea
              value={promptDescription}
              onChange={(event) => setPromptDescription(event.target.value.slice(0, 5000))}
              placeholder="Describe your creative output in detail..."
              rows={5}
              style={{
                width: '100%',
                padding: 10,
                borderRadius: 8,
                border: '1px solid var(--line)',
                resize: 'vertical',
              }}
            />
          </div>

          <div
            style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(160px, 1fr))', gap: 12, marginTop: 12 }}
          >
            <div>
              <label
                htmlFor="aspect-ratio"
                style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 6 }}
              >
                Aspect Ratio
              </label>
              <select
                id="aspect-ratio"
                value={aspectRatio}
                onChange={(event) => setAspectRatio(event.target.value)}
                style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid var(--line)' }}
              >
                {ASPECT_RATIOS.map((ratio) => (
                  <option key={ratio} value={ratio}>
                    {ratio}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="resolution" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 6 }}>
                Resolution
              </label>
              <select
                id="resolution"
                value={resolution}
                onChange={(event) => setResolution(event.target.value)}
                style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid var(--line)' }}
              >
                {RESOLUTIONS.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ border: '1px solid var(--line)', borderRadius: 8, padding: 10 }}>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Cost & Credits</p>
              <p style={{ margin: '8px 0 0', fontSize: 13 }}>{usedCredits} credits</p>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--muted)' }}>Available: {availableCredits}</p>
            </div>
          </div>

          <div
            style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(180px, 1fr))', gap: 12, marginTop: 12 }}
          >
            <div style={{ border: '1px dashed var(--line)', borderRadius: 8, padding: 10 }}>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Reference Images</p>
              <p style={{ margin: '6px 0 0', fontSize: 12, color: 'var(--muted)' }}>
                Max 9 (png, jpg, jpeg, webp) ({remainingImageSlots} remaining)
              </p>
              <input
                type="file"
                accept=".png,.jpg,.jpeg,.webp"
                multiple
                onChange={(event) => handleImageUpload(event.target.files)}
                style={{ marginTop: 8, width: '100%' }}
              />
            </div>

            <div style={{ border: '1px dashed var(--line)', borderRadius: 8, padding: 10 }}>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Reference Videos</p>
              <p style={{ margin: '6px 0 0', fontSize: 12, color: 'var(--muted)' }}>
                Max 3, total 15s (mp4, mov) ({remainingVideoSlots} remaining)
              </p>
              <input
                type="file"
                accept=".mp4,.mov"
                multiple
                onChange={(event) => handleVideoUpload(event.target.files)}
                style={{ marginTop: 8, width: '100%' }}
              />
            </div>

            <div style={{ border: '1px dashed var(--line)', borderRadius: 8, padding: 10 }}>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Reference Audios</p>
              <p style={{ margin: '6px 0 0', fontSize: 12, color: 'var(--muted)' }}>
                Max 3, total 15s (mp3, wav) ({remainingAudioSlots} remaining)
              </p>
              <input
                type="file"
                accept=".mp3,.wav"
                multiple
                onChange={(event) => handleAudioUpload(event.target.files)}
                style={{ marginTop: 8, width: '100%' }}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                border: '1px solid var(--line)',
                borderRadius: 8,
                padding: 10,
              }}
            >
              <input
                type="checkbox"
                checked={containsRealPeople}
                onChange={(event) => setContainsRealPeople(event.target.checked)}
              />
              <span style={{ fontSize: 13 }}>
                Contains Real People (specialized realistic-human generation pipeline)
              </span>
            </label>

            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                border: '1px solid var(--line)',
                borderRadius: 8,
                padding: 10,
              }}
            >
              <input
                type="checkbox"
                checked={returnLastFrame}
                onChange={(event) => setReturnLastFrame(event.target.checked)}
              />
              <span style={{ fontSize: 13 }}>Return Last Frame (for seamless continuation in next video task)</span>
            </label>
          </div>

          <div style={{ marginTop: 12, border: '1px solid var(--line)', borderRadius: 8, padding: 10 }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                gap: 10,
                alignItems: 'center',
                flexWrap: 'wrap',
              }}
            >
              <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Advanced: Seed Control</p>
              <button
                type="button"
                onClick={setRandomSeed}
                style={{
                  borderRadius: 8,
                  border: '1px solid var(--line)',
                  background: 'transparent',
                  color: 'var(--text)',
                  padding: '6px 10px',
                  cursor: 'pointer',
                }}
              >
                Random Seed
              </button>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8, alignItems: 'center' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input
                  type="checkbox"
                  checked={seedEnabled}
                  onChange={(event) => setSeedEnabled(event.target.checked)}
                />{' '}
                Use Seed
              </label>
              <input
                disabled={!seedEnabled}
                value={seedValue}
                onChange={(event) => setSeedValue(event.target.value.replaceAll(/\D/g, '').slice(0, 12))}
                placeholder="Choose any number"
                style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid var(--line)', minWidth: 180 }}
              />
            </div>
          </div>

          <div style={{ marginTop: 12, border: '1px solid var(--line)', borderRadius: 8, padding: 10 }}>
            <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Edit Tools</p>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
              {EDIT_TOOLS.map((tool) => (
                <span
                  key={tool}
                  style={{ borderRadius: 999, border: '1px solid var(--line)', padding: '4px 10px', fontSize: 12 }}
                >
                  {tool}
                </span>
              ))}
            </div>
          </div>

          <div style={{ marginTop: 12, border: '1px solid var(--line)', borderRadius: 8, padding: 10 }}>
            <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Enterprise Capability Stack</p>
            <ul style={{ margin: '8px 0 0', paddingLeft: 18 }}>
              {capabilityList().map((item) => (
                <li key={item} style={{ marginBottom: 4, fontSize: 13 }}>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div
            style={{
              marginTop: 12,
              border: '1px solid #f59e0b55',
              borderRadius: 8,
              padding: 10,
              background: '#f59e0b12',
            }}
          >
            <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Public Figure / Celebrity Controls</p>
            <p style={{ margin: '6px 0 0', fontSize: 13 }}>
              Celebrity avatar or voice cloning is restricted by policy and rights checks. Use licensed likeness/voice
              profiles only after documented consent and legal approval.
            </p>
          </div>

          {onApplyConfig ? (
            <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={applyConfigToParent}
                style={{
                  borderRadius: 8,
                  border: 'none',
                  background: 'var(--brand)',
                  color: '#00101e',
                  padding: '9px 12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                Apply Suite Config To Generator
              </button>
            </div>
          ) : null}
        </>
      ) : null}

      {showPortraitLibrary ? (
        <dialog
          open
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(5, 8, 18, 0.72)',
            display: 'grid',
            placeItems: 'center',
            zIndex: 50,
            padding: 16,
            border: 'none',
            margin: 0,
            width: '100vw',
            height: '100vh',
          }}
        >
          <div className="card" style={{ width: 'min(920px, 100%)', maxHeight: '90vh', overflow: 'auto', padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
              <h3 style={{ margin: 0 }}>Virtual Portrait Library</h3>
              <button
                type="button"
                onClick={() => setShowPortraitLibrary(false)}
                style={{
                  borderRadius: 8,
                  border: '1px solid var(--line)',
                  background: 'transparent',
                  padding: '6px 10px',
                  cursor: 'pointer',
                }}
              >
                Close
              </button>
            </div>

            <div
              style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(140px, 1fr))', gap: 12, marginTop: 12 }}
            >
              <div>
                <label htmlFor="gender" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 6 }}>
                  Gender
                </label>
                <select
                  id="gender"
                  value={portraitGender}
                  onChange={(event) => setPortraitGender(event.target.value as 'male' | 'female' | 'all')}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid var(--line)' }}
                >
                  <option value="all">All</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="country-dropdown"
                  style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 6 }}
                >
                  Country
                </label>
                <div style={{ position: 'relative' }}>
                  <button
                    id="country-dropdown"
                    type="button"
                    onClick={() => setShowCountryMenu((value) => !value)}
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      borderRadius: 8,
                      border: '1px solid var(--line)',
                      background: '#111318',
                      color: 'var(--text)',
                      textAlign: 'left',
                      cursor: 'pointer',
                    }}
                  >
                    {portraitCountry}
                  </button>
                  {showCountryMenu ? (
                    <div
                      style={{
                        position: 'absolute',
                        top: 'calc(100% + 6px)',
                        left: 0,
                        right: 0,
                        zIndex: 40,
                        borderRadius: 10,
                        border: '1px solid rgba(255,255,255,0.08)',
                        background: '#17181c',
                        boxShadow: '0 20px 60px rgba(0,0,0,0.35)',
                        overflow: 'hidden',
                      }}
                    >
                      <div style={{ padding: 8, borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                        <input
                          value={portraitCountrySearch}
                          onChange={(event) => setPortraitCountrySearch(event.target.value)}
                          placeholder="Search country..."
                          style={{
                            width: '100%',
                            padding: '8px 10px',
                            borderRadius: 8,
                            border: '1px solid rgba(255,255,255,0.08)',
                            background: '#101115',
                            color: 'var(--text)',
                          }}
                        />
                      </div>
                      <div style={{ maxHeight: 220, overflow: 'auto' }}>
                        {filteredCountries.map((country) => (
                          <button
                            key={country}
                            type="button"
                            onClick={() => {
                              setPortraitCountry(country);
                              setPortraitCountrySearch('');
                              setShowCountryMenu(false);
                            }}
                            style={{
                              width: '100%',
                              border: 'none',
                              background: portraitCountry === country ? 'rgba(255,255,255,0.08)' : 'transparent',
                              color: 'var(--text)',
                              padding: '10px 12px',
                              textAlign: 'left',
                              cursor: 'pointer',
                            }}
                          >
                            {country}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>

              <div>
                <label htmlFor="age" style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 6 }}>
                  Age
                </label>
                <select
                  id="age"
                  value={portraitAgeBand}
                  onChange={(event) => setPortraitAgeBand(event.target.value as AgeBand)}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid var(--line)' }}
                >
                  {AGE_BANDS.map((band) => (
                    <option key={band} value={band}>
                      {band}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="total-avatars"
                  style={{ display: 'block', fontSize: 12, fontWeight: 700, marginBottom: 6 }}
                >
                  Total Avatars
                </label>
                <input
                  id="total-avatars"
                  type="number"
                  value={portraitCount}
                  onChange={(event) => setPortraitCount(Math.max(1, Number(event.target.value) || 1))}
                  min={1}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid var(--line)' }}
                />
              </div>
            </div>

            <div style={{ marginTop: 14, border: '1px solid var(--line)', borderRadius: 8, padding: 10 }}>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 700 }}>Preview Selection</p>
              <p style={{ margin: '8px 0 0', fontSize: 13 }}>
                {portraitCount} avatars | Gender: {portraitGender} | Country: {portraitCountry || 'Any'} | Age:{' '}
                {portraitAgeBand}
              </p>
            </div>
          </div>
        </dialog>
      ) : null}
    </section>
  );
}
