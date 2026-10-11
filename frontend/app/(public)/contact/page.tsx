'use client';

import { useState } from 'react';
import { Mail } from 'lucide-react';
import { Reveal } from '../_components/reveal';
import { apiPost, DEFAULT_TENANT_ID } from '@/app/lib/api-client';

export default function ContactPage() {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [message, setMessage] = useState('');
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim()) return;
    setError('');
    setBusy(true);
    try {
      await apiPost(
        '/email/contacts',
        {
          email: email.trim(),
          name: name.trim() || email.trim().split('@')[0],
          tags: ['contact-form'],
          properties: message.trim() ? { message: message.trim() } : undefined,
        },
        tenantId
      );
      setDone(true);
      setEmail('');
      setName('');
      setMessage('');
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : 'Could not send your message. Please try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mk-section mk-pt-hero">
      <div className="mk-container grid max-w-4xl grid-cols-1 gap-12 md:grid-cols-2">
        <Reveal>
          <span className="mk-eyebrow mb-5">Contact</span>
          <h1 className="text-4xl font-semibold tracking-tight text-ink sm:text-5xl">Talk to our team</h1>
          <p className="mt-5 text-lg leading-relaxed text-ink-2">
            Questions about plans, a security review, or just want to see Nuxtron on your own data? Send us a note
            and we&apos;ll get back to you within one business day.
          </p>
          <div className="mt-8 flex items-center gap-3 text-ink-2">
            <Mail size={18} className="text-brand" aria-hidden="true" />
            <span className="text-sm">hello@nuxtron.app</span>
          </div>
        </Reveal>

        <form
          onSubmit={handleSubmit}
          className="mk-card flex flex-col gap-5 p-8"
        >
          <div>
            <label htmlFor="contact-name" className="mb-1.5 block text-sm font-medium text-ink-2">
              Name
            </label>
            <input
              id="contact-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
              className="w-full rounded-lg border border-line bg-line-soft px-3.5 py-2.5 text-[15px] text-ink outline-none transition placeholder:text-ink-faint focus:border-brand/60 focus:ring-2 focus:ring-brand/20"
              placeholder="Jane Doe"
            />
          </div>
          <div>
            <label htmlFor="contact-email" className="mb-1.5 block text-sm font-medium text-ink-2">
              Email <span className="text-brand">*</span>
            </label>
            <input
              id="contact-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              className="w-full rounded-lg border border-line bg-line-soft px-3.5 py-2.5 text-[15px] text-ink outline-none transition placeholder:text-ink-faint focus:border-brand/60 focus:ring-2 focus:ring-brand/20"
              placeholder="you@company.com"
            />
          </div>
          <div>
            <label htmlFor="contact-message" className="mb-1.5 block text-sm font-medium text-ink-2">
              Message
            </label>
            <textarea
              id="contact-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              className="w-full resize-none rounded-lg border border-line bg-line-soft px-3.5 py-2.5 text-[15px] text-ink outline-none transition placeholder:text-ink-faint focus:border-brand/60 focus:ring-2 focus:ring-brand/20"
              placeholder="What are you trying to solve?"
            />
          </div>

          <div aria-live="polite" role="status">
            {error ? <p className="text-sm text-rose-400">{error}</p> : null}
            {done ? <p className="text-sm text-emerald-400">Thanks — we&apos;ll be in touch shortly.</p> : null}
          </div>

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-ink px-4 py-3 text-sm font-bold uppercase tracking-wider text-white transition-colors hover:bg-black disabled:cursor-not-allowed disabled:opacity-60 active:scale-[0.98]"
          >
            {busy ? 'Sending…' : 'Send message'}
          </button>
        </form>
      </div>
    </section>
  );
}
