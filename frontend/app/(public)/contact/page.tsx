'use client';

import { useState } from 'react';
import { Mail } from 'lucide-react';
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
    <section className="mk-section pt-40">
      <div className="mk-container grid max-w-4xl grid-cols-1 gap-12 md:grid-cols-2">
        <div>
          <span className="mk-eyebrow mb-5">Contact</span>
          <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">Talk to our team</h1>
          <p className="mt-5 text-lg leading-relaxed text-zinc-400">
            Questions about plans, a security review, or just want to see Nuxtron on your own data? Send us a note
            and we&apos;ll get back to you within one business day.
          </p>
          <div className="mt-8 flex items-center gap-3 text-zinc-400">
            <Mail size={18} className="text-[#ef233c]" aria-hidden="true" />
            <span className="text-sm">hello@nuxtron.app</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mk-card space-y-5 p-8" noValidate>
          <div>
            <label htmlFor="contact-name" className="mb-1.5 block text-sm font-medium text-zinc-300">
              Name
            </label>
            <input
              id="contact-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-[15px] text-white outline-none transition placeholder:text-zinc-600 focus:border-[#ef233c]/60 focus:ring-2 focus:ring-[#ef233c]/20"
              placeholder="Jane Doe"
            />
          </div>
          <div>
            <label htmlFor="contact-email" className="mb-1.5 block text-sm font-medium text-zinc-300">
              Email <span className="text-[#ef233c]">*</span>
            </label>
            <input
              id="contact-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-[15px] text-white outline-none transition placeholder:text-zinc-600 focus:border-[#ef233c]/60 focus:ring-2 focus:ring-[#ef233c]/20"
              placeholder="you@company.com"
            />
          </div>
          <div>
            <label htmlFor="contact-message" className="mb-1.5 block text-sm font-medium text-zinc-300">
              Message
            </label>
            <textarea
              id="contact-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              className="w-full resize-none rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-[15px] text-white outline-none transition placeholder:text-zinc-600 focus:border-[#ef233c]/60 focus:ring-2 focus:ring-[#ef233c]/20"
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
            className="w-full rounded-lg bg-[#ef233c] px-4 py-3 text-sm font-bold uppercase tracking-wider text-white transition-all hover:bg-[#d81f36] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {busy ? 'Sending…' : 'Send message'}
          </button>
        </form>
      </div>
    </section>
  );
}
