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
 * as label). Light surface matching the auth shell's white/blue theme, with
 * an optional leading icon and a show/hide toggle for password fields.
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
      <label htmlFor={id} className="text-sm font-medium text-[#33475b]">
        {label}
      </label>
      <div className="relative">
        {icon ? (
          <span className="pointer-events-none absolute inset-y-0 left-3.5 flex items-center text-[#8595a8]">
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
          className={`w-full rounded-xl border bg-white py-2.5 text-[15px] text-[#0b1b2b] outline-none transition placeholder:text-[#a7b4c3] focus:ring-2 focus:ring-[#0ea5e9]/20 ${
            icon ? 'pl-10' : 'pl-3.5'
          } ${isPassword ? 'pr-11' : 'pr-3.5'} ${
            error ? 'border-rose-500/60 focus:border-rose-500' : 'border-[#dbe6ee] focus:border-[#0ea5e9]/60'
          }`}
        />
        {isPassword ? (
          <button
            type="button"
            onClick={() => setRevealed((v) => !v)}
            className="absolute inset-y-0 right-3 flex items-center text-[#8595a8] transition-colors hover:text-[#33475b]"
            aria-label={revealed ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
            tabIndex={-1}
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
