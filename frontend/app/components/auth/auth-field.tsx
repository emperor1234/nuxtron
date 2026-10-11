'use client';

import { useId, useState, type ReactNode } from 'react';
import { Eye, EyeOff } from 'lucide-react';

type AuthFieldProps = {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  autoComplete?: string;
  inputMode?: 'text' | 'tel' | 'email';
  required?: boolean;
  error?: string;
  /** Leading icon (e.g. Mail, Lock) — purely visual, pairs with the label. */
  icon?: ReactNode;
  placeholder?: string;
};

/**
 * Labeled input. Label ABOVE the control, error BELOW it (never placeholder
 * as label). Light surface matching the auth shell's Salix-derived theme,
 * with an optional leading icon and a show/hide toggle for password fields.
 */
export function AuthField({
  label,
  name,
  value,
  onChange,
  type = 'text',
  autoComplete,
  inputMode,
  required,
  error,
  icon,
  placeholder,
}: AuthFieldProps) {
  const id = useId();
  const errorId = `${id}-error`;
  const isPassword = type === 'password';
  const [revealed, setRevealed] = useState(false);
  const resolvedType = isPassword ? (revealed ? 'text' : 'password') : type;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-ink-2">
        {label}
      </label>
      <div className="relative">
        {icon ? (
          <span className="pointer-events-none absolute inset-y-0 left-3.5 flex items-center text-ink-faint">
            {icon}
          </span>
        ) : null}
        <input
          id={id}
          name={name}
          type={resolvedType}
          inputMode={inputMode}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          required={required}
          placeholder={placeholder}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
          className={`w-full rounded-xl border bg-white py-2.5 text-[15px] text-ink outline-none transition placeholder:text-ink-faint focus:ring-2 focus:ring-brand/20 ${
            icon ? 'pl-10' : 'pl-3.5'
          } ${isPassword ? 'pr-11' : 'pr-3.5'} ${
            error ? 'border-rose-500/60 focus:border-rose-500' : 'border-line focus:border-brand/60'
          }`}
        />
        {isPassword ? (
          <button
            type="button"
            onClick={() => setRevealed((v) => !v)}
            className="absolute inset-y-0 right-1 flex min-w-10 items-center justify-center border-0 bg-transparent p-0 text-ink-faint transition-colors hover:text-ink-2"
            aria-label={revealed ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
            aria-pressed={revealed}
          >
            {revealed ? <EyeOff size={17} /> : <Eye size={17} />}
          </button>
        ) : null}
      </div>
      {error ? (
        <span id={errorId} className="text-sm text-rose-600">
          {error}
        </span>
      ) : null}
    </div>
  );
}
