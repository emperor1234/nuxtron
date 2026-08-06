import { describe, expect, it } from 'vitest';

import { filterQueueItemsByStage, type ContentGenerationJob } from './page';

function makeJob(stage: string): ContentGenerationJob {
  return {
    job_id: `job-${stage}`,
    status: 'failed',
    progress_pct: 100,
    stage,
  };
}

describe('content generation queue stage filtering', () => {
  it('returns all jobs for all stage filter', () => {
    const jobs = [makeJob('timeout'), makeJob('failed'), makeJob('queued')];

    const filtered = filterQueueItemsByStage(jobs, 'all');

    expect(filtered).toHaveLength(3);
    expect(filtered).toEqual(jobs);
  });

  it('returns only timeout stage jobs for timeout filter', () => {
    const jobs = [makeJob('timeout'), makeJob(' TIMEOUT '), makeJob('failed'), makeJob('running')];

    const filtered = filterQueueItemsByStage(jobs, 'timeout');

    expect(filtered).toHaveLength(2);
    expect(filtered.every((job) => String(job.stage).trim().toLowerCase() === 'timeout')).toBe(true);
  });

  it('returns failed and error stage jobs for failed filter', () => {
    const jobs = [makeJob('failed'), makeJob('error'), makeJob('timeout'), makeJob('running')];

    const filtered = filterQueueItemsByStage(jobs, 'failed');

    expect(filtered).toHaveLength(2);
    expect(filtered.map((job) => String(job.stage).trim().toLowerCase()).sort()).toEqual(['error', 'failed']);
  });
});
