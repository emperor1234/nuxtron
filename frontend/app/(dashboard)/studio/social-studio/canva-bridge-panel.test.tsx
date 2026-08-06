import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { CanvaBridgePanel, type CanvaImportJob, type CanvaPublishMode, type SocialAccount } from './canva-bridge-panel';

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

describe('CanvaBridgePanel', () => {
  const socialAccounts: SocialAccount[] = [
    { id: 1, account_name: 'Nuxtron Social', network: 'instagram' },
    { id: 2, account_name: 'Nuxtron Video', network: 'linkedin' },
  ];

  const canvaImports: CanvaImportJob[] = [
    {
      id: 7,
      account_id: 1,
      design_id: 'design_123456',
      resolved_media_url: 'https://cdn.example.com/render.png',
      post_id: 88,
      status: 'imported',
      created_at: '2026-05-28T10:30:00.000Z',
    },
  ];

  const inputStyle = { color: 'inherit' };
  const setCanvaAccountId = vi.fn();
  const setCanvaDesignId = vi.fn();
  const setCanvaDesignUrl = vi.fn();
  const setCanvaHeadline = vi.fn();
  const setCanvaCaption = vi.fn();
  const setCanvaPublishMode = vi.fn();
  const setCanvaPublishAt = vi.fn();
  const onSubmitImport = vi.fn();
  const onApplyActiveBrandKit = vi.fn();
  const onRefreshImports = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  function renderPanel(overrides: Partial<React.ComponentProps<typeof CanvaBridgePanel>> = {}) {
    return render(
      <CanvaBridgePanel
        socialAccounts={socialAccounts}
        canvaAccountId="1"
        setCanvaAccountId={setCanvaAccountId}
        canvaDesignId="design_123456"
        setCanvaDesignId={setCanvaDesignId}
        canvaDesignUrl="https://www.canva.com/design/abc"
        setCanvaDesignUrl={setCanvaDesignUrl}
        canvaHeadline="Brand launch"
        setCanvaHeadline={setCanvaHeadline}
        canvaCaption="Launch caption"
        setCanvaCaption={setCanvaCaption}
        canvaPublishMode={'draft' as CanvaPublishMode}
        setCanvaPublishMode={setCanvaPublishMode}
        canvaPublishAt="2026-05-28T12:00"
        setCanvaPublishAt={setCanvaPublishAt}
        canvaImportBusy={false}
        canvaImportMessage="Imported Canva asset into scheduled post 88."
        canvaImports={canvaImports}
        inputStyle={inputStyle}
        activeBrandKitName="Summer Brand Kit"
        activeBrandKitColorsCount={3}
        activeBrandKitFontsCount={2}
        onSubmitImport={onSubmitImport}
        onApplyActiveBrandKit={onApplyActiveBrandKit}
        onRefreshImports={onRefreshImports}
        {...overrides}
      />
    );
  }

  it('renders the bridge and recent imports', () => {
    renderPanel();

    expect(screen.getByText('Canva bridge')).toBeTruthy();
    expect(screen.getByText('Summer Brand Kit')).toBeTruthy();
    expect(screen.getByText('design_123456')).toBeTruthy();
    expect(screen.getByText('imported · post 88')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Open canvas editor' }).getAttribute('href')).toBe('/studio/editor');
  });

  it('invokes bridge actions', () => {
    renderPanel();

    fireEvent.click(screen.getAllByRole('button', { name: 'Use active brand kit' })[0]);
    fireEvent.click(screen.getAllByRole('button', { name: 'Import Canva design' })[0]);
    fireEvent.click(screen.getAllByRole('button', { name: 'Refresh imports' })[0]);

    expect(onApplyActiveBrandKit).toHaveBeenCalledTimes(1);
    expect(onSubmitImport).toHaveBeenCalledTimes(1);
    expect(onRefreshImports).toHaveBeenCalledTimes(1);
  });

  it('forwards field changes to parent setters', () => {
    renderPanel();

    fireEvent.change(screen.getByLabelText('Connected account'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Design ID'), { target: { value: 'design_abc' } });
    fireEvent.change(screen.getByLabelText('Design URL'), { target: { value: 'https://www.canva.com/design/new' } });
    fireEvent.change(screen.getByLabelText('Headline'), { target: { value: 'Updated headline' } });
    fireEvent.change(screen.getByLabelText('Caption'), { target: { value: 'Updated caption' } });
    fireEvent.change(screen.getByLabelText('Publish mode'), { target: { value: 'auto' } });
    fireEvent.change(screen.getByLabelText('Publish at'), { target: { value: '2026-05-28T14:00' } });

    expect(setCanvaAccountId).toHaveBeenCalledWith('2');
    expect(setCanvaDesignId).toHaveBeenCalledWith('design_abc');
    expect(setCanvaDesignUrl).toHaveBeenCalledWith('https://www.canva.com/design/new');
    expect(setCanvaHeadline).toHaveBeenCalledWith('Updated headline');
    expect(setCanvaCaption).toHaveBeenCalledWith('Updated caption');
    expect(setCanvaPublishMode).toHaveBeenCalledWith('auto');
    expect(setCanvaPublishAt).toHaveBeenCalledWith('2026-05-28T14:00');
  });

  it('renders empty state when no imports or accounts exist', () => {
    const { container } = renderPanel({
      socialAccounts: [],
      canvaImports: [],
      activeBrandKitName: undefined,
      activeBrandKitColorsCount: undefined,
      activeBrandKitFontsCount: undefined,
      canvaImportMessage: '',
    });
    const scoped = within(container);

    expect(scoped.getByText('Connect a social account first')).toBeTruthy();
    expect(scoped.getByText('No Canva imports yet.')).toBeTruthy();
    expect(scoped.queryByText('Summer Brand Kit')).toBeNull();
  });

  it('disables publishing controls while importing', () => {
    renderPanel({ canvaImportBusy: true });

    const importButton = screen.getAllByRole('button', { name: 'Importing…' })[0] as HTMLButtonElement;
    const publishAtInput = screen.getByLabelText('Publish at') as HTMLInputElement;
    expect(importButton.disabled).toBe(true);
    expect(publishAtInput.disabled).toBe(true);
  });
});
