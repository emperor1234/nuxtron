import { ImageResponse } from 'next/og';

export const runtime = 'nodejs';
export const alt = 'Nuxtron — Search, AI visibility, content, social and growth';
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
        background: 'linear-gradient(165deg, #f4f7ff 0%, #e8f0fb 45%, #fffefc 100%)',
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
            background: '#0b1330',
            borderRadius: 16,
            border: '2px solid #22cdea',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#f4f7ff',
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
              color: '#0b1330',
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
              color: '#2563c9',
              fontSize: 22,
              fontWeight: 500,
              letterSpacing: 6,
              textTransform: 'uppercase',
            }}
          >
            Search & AI · Marketing
          </span>
        </div>
      </div>
      <div
        style={{
          color: '#526071',
          fontSize: 28,
          fontWeight: 400,
          textAlign: 'center',
          maxWidth: 720,
        }}
      >
        Search & AI visibility · Content · Social · Growth
      </div>
    </div>,
    { ...size }
  );
}
