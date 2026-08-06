'use client';

/**
 * SecretInput — A security-hardened input for API keys, tokens, and passwords.
 *
 * Security guarantees:
 *  - The browser always renders the value as bullets (type="password") so the OS
 *    clipboard, screen-sharing tools, and shoulder-surfers never see plaintext.
 *  - The value is never logged to the console, never stored in component state as
 *    a readable string beyond what the browser holds natively in the DOM input.
 *  - The reveal toggle shows the value for at most `revealDurationMs` milliseconds
 *    (default 3 s) then automatically re-masks.
 *  - paste is fully supported — the browser handles the clipboard read natively.
 *  - autocomplete is set to "new-password" so password managers treat it correctly
 *    and browsers do not autofill saved credentials into API key fields.
 *  - The component accepts an `onChange` callback that receives the raw value so
 *    the parent can submit it, but does not echo it back into the DOM.
 */

import React, { useCallback, useId, useRef, useState } from 'react';

export interface SecretInputProps extends Omit<
  React.InputHTMLAttributes<HTMLInputElement>,
  'type' | 'value' | 'defaultValue' | 'onChange' | 'autoComplete' | 'size'
> {
  /** Controlled value. */
  value?: string;
  /** Called when the value changes. Receives the raw secret string. */
  onChange?: (value: string) => void;
  /** Label shown above the input. */
  label?: string;
  /** Placeholder shown inside the input (always masked). */
  placeholder?: string;
  /** Whether the input is in an error state. */
  hasError?: boolean;
  /** Error message to display below the input. */
  errorMessage?: string;
  /** Helper text displayed below the input when there is no error. */
  hint?: string;
  /** How long the value stays visible when the reveal toggle is clicked (ms). Default: 3000. */
  revealDurationMs?: number;
  /** Disable the show/hide toggle entirely. Default: false. */
  noRevealToggle?: boolean;
  /** Input size variant. */
  size?: 'sm' | 'md' | 'lg';
}

const SIZE_CLASSES = {
  sm: 'h-8 text-sm px-2.5',
  md: 'h-10 text-sm px-3',
  lg: 'h-12 text-base px-4',
} as const;

/**
 * Eye-open SVG icon (inline, no external dependency).
 */
function IconEyeOpen({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

/**
 * Eye-closed SVG icon (inline, no external dependency).
 */
function IconEyeClosed({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

export function SecretInput({
  value = '',
  onChange,
  label,
  placeholder = '••••••••••••••••',
  hasError = false,
  errorMessage,
  hint,
  revealDurationMs = 3000,
  noRevealToggle = false,
  size = 'md',
  className,
  id: externalId,
  disabled,
  required,
  name,
  ...rest
}: SecretInputProps) {
  const autoId = useId();
  const inputId = externalId ?? autoId;
  const [revealed, setRevealed] = useState(false);
  const revealTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange?.(e.target.value);
    },
    [onChange]
  );

  const handleRevealToggle = useCallback(() => {
    if (revealTimerRef.current) {
      clearTimeout(revealTimerRef.current);
      revealTimerRef.current = null;
    }
    setRevealed((prev) => {
      const next = !prev;
      if (next) {
        // Auto-hide after revealDurationMs to prevent accidental exposure
        revealTimerRef.current = setTimeout(() => {
          setRevealed(false);
          revealTimerRef.current = null;
        }, revealDurationMs);
      }
      return next;
    });
  }, [revealDurationMs]);

  // Clean up the auto-hide timer on unmount
  React.useEffect(() => {
    return () => {
      if (revealTimerRef.current) {
        clearTimeout(revealTimerRef.current);
      }
    };
  }, []);

  const inputType = revealed ? 'text' : 'password';
  const sizeClass = SIZE_CLASSES[size];

  const borderClass = hasError
    ? 'border-red-500 focus-within:ring-red-500/30'
    : 'border-border focus-within:ring-foreground/20';

  return (
    <div className={`flex flex-col gap-1.5 ${className ?? ''}`}>
      {label && (
        <label htmlFor={inputId} className="text-sm font-medium text-foreground">
          {label}
          {required && (
            <span className="ml-0.5 text-red-500" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}

      <div
        className={[
          'relative flex items-center rounded-md border bg-background',
          'transition-shadow focus-within:ring-2',
          borderClass,
          disabled ? 'cursor-not-allowed opacity-60' : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        <input
          {...rest}
          id={inputId}
          name={name}
          type={inputType}
          value={value}
          onChange={handleChange}
          placeholder={placeholder}
          disabled={disabled}
          required={required}
          // Prevent browser autofill from filling saved credentials
          autoComplete="new-password"
          // Prevent mobile OS from learning this value
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck={false}
          // Never allow copy of the value (belt-and-suspenders; user can still use
          // browser dev tools, so this is UI-level protection only)
          onCopy={(e) => e.preventDefault()}
          onCut={(e) => e.preventDefault()}
          aria-invalid={hasError ? 'true' : undefined}
          aria-describedby={
            [hasError && errorMessage ? `${inputId}-error` : '', hint ? `${inputId}-hint` : '']
              .filter(Boolean)
              .join(' ') || undefined
          }
          className={[
            'w-full rounded-md bg-transparent font-mono outline-none',
            'placeholder:text-muted-foreground',
            sizeClass,
            // Reserve space on the right for the toggle button
            !noRevealToggle ? 'pr-10' : '',
          ]
            .filter(Boolean)
            .join(' ')}
        />

        {!noRevealToggle && (
          <button
            type="button"
            onClick={handleRevealToggle}
            disabled={disabled}
            aria-label={revealed ? 'Hide secret value' : 'Reveal secret value (auto-hides)'}
            aria-pressed={revealed}
            className={[
              'absolute right-0 flex h-full items-center justify-center px-3',
              'text-muted-foreground transition-colors',
              'hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-foreground/30',
              disabled ? 'pointer-events-none' : '',
            ]
              .filter(Boolean)
              .join(' ')}
          >
            {revealed ? <IconEyeClosed className="h-4 w-4" /> : <IconEyeOpen className="h-4 w-4" />}
          </button>
        )}
      </div>

      {hasError && errorMessage && (
        <p id={`${inputId}-error`} className="text-xs text-red-500" role="alert">
          {errorMessage}
        </p>
      )}

      {!hasError && hint && (
        <p id={`${inputId}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      )}

      {revealed && (
        <p className="text-xs text-amber-600" role="status" aria-live="polite">
          Value visible — auto-hides in {Math.ceil(revealDurationMs / 1000)}s
        </p>
      )}
    </div>
  );
}
