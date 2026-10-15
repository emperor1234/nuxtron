import { describe, expect, it } from 'vitest';
import { mediaReviewCsv, parseMediaMarkup } from './media-markup-model';

describe('parseMediaMarkup', () => {
  it('counts only the supplied image and video elements and reports their markup evidence', () => {
    const result = parseMediaMarkup(`
      <main>
        <img src="/hero.webp">
        <img src="/decorative.svg" alt="" role="presentation" width="40" height="20">
        <video src="/captions.mp4" poster="/poster.jpg" title="Product demo" controls>
          <track kind="captions" src="/captions.vtt">
        </video>
        <video><source src="/interview.mp4" type="video/mp4"></video>
      </main>
    `);

    expect(result.imageCount).toBe(2);
    expect(result.videoCount).toBe(2);
    expect(result.imagesMissingAlt).toBe(1);
    expect(result.imagesWithEmptyAltReview).toBe(0);
    expect(result.imagesMissingDimensions).toBe(1);
    expect(result.videosWithoutCaptions).toBe(1);
    expect(result.videosWithoutPoster).toBe(1);
    expect(result.videosWithoutAccessibleName).toBe(1);
    expect(result.assets[0].source).toBe('/hero.webp');
  });

  it('distinguishes a real empty media sample and flags ambiguous empty alt text for review', () => {
    const empty = parseMediaMarkup('<main><p>No media included.</p></main>');
    expect(empty.imageCount).toBe(0);
    expect(empty.videoCount).toBe(0);
    expect(empty.findingCount).toBe(0);

    const image = parseMediaMarkup('<img src="/image.png" alt="" width="10" height="10">');
    expect(image.imagesWithEmptyAltReview).toBe(1);
    expect(image.assets[0].issues[0]).toMatch(/confirm this image is decorative/i);
  });

  it('rejects blank and over-limit markup samples', () => {
    expect(() => parseMediaMarkup('  ')).toThrow(/paste page markup/i);
    expect(() => parseMediaMarkup('x'.repeat(1_000_001))).toThrow(/1 MB/i);
  });

  it('exports audit notes as formula-safe CSV text', () => {
    const review = parseMediaMarkup('<img src="=HYPERLINK(\"https://example.test\")" alt="">');
    const csv = mediaReviewCsv(review);
    expect(csv).toContain("'=HYPERLINK(");
    expect(csv).toContain('Markup review notes');
  });
});
