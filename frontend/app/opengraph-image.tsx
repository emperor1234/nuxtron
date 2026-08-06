import { ImageResponse } from 'next/og';

export const runtime = 'nodejs';
export const alt = 'Nuxtron Platform';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function OgImage() {
  return new ImageResponse(
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        width: '100%',
        height: '100%',
        background: 'linear-gradient(165deg, #f5f8ff 0%, #eef4ff 45%, #f8faff 100%)',
        fontFamily: 'sans-serif',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 20,
          marginBottom: 32,
        }}
      >
        <div
          style={{
            width: 96,
            height: 96,
            background: '#ffffff',
            borderRadius: 16,
            border: '2px solid #22cdea',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#0f213f',
            fontSize: 44,
            fontWeight: 800,
            letterSpacing: -2,
          }}
        >
          NX
        </div>
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <span
            style={{
              color: '#0f213f',
              fontSize: 72,
              fontWeight: 800,
              letterSpacing: -3,
              lineHeight: 1,
            }}
          >
            NUXTRON
          </span>
          <span
            style={{
              color: '#22cdea',
              fontSize: 22,
              fontWeight: 500,
              letterSpacing: 6,
              textTransform: 'uppercase',
            }}
          >
            Platform
          </span>
        </div>
      </div>
      <div
        style={{
          color: '#4f627f',
          fontSize: 28,
          fontWeight: 400,
          textAlign: 'center',
          maxWidth: 720,
        }}
      >
        AI content · analytics · integrations · automation
      </div>
    </div>,
    { ...size }
  );
}
