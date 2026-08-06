import { z } from 'zod';

/** Shared validation for auth forms — a single source of truth so the
 * login/register UI and any future server-side echo of the same rules
 * can't drift apart. */

export const tenantIdSchema = z
  .string()
  .trim()
  .min(1, 'Tenant ID is required.')
  .max(128, 'Tenant ID is too long.');

export const emailSchema = z.string().trim().min(1, 'Email is required.').email('Enter a valid email address.');

export const loginPasswordSchema = z.string().min(8, 'Password must be at least 8 characters.');

export const loginSchema = z.object({
  tenantId: tenantIdSchema,
  email: emailSchema,
  password: loginPasswordSchema,
});

export type LoginInput = z.infer<typeof loginSchema>;

export const signupPasswordSchema = z
  .string()
  .min(10, 'Password must be at least 10 characters.')
  .regex(/[a-z]/, 'Password needs a lowercase letter.')
  .regex(/[A-Z]/, 'Password needs an uppercase letter.')
  .regex(/[0-9]/, 'Password needs a number.');

// Signup collects only what's needed to create the account. Company/DOB/
// mailing address were previously required here but belong in profile
// completion post-signup, not gating account creation — asking for a full
// postal address before someone has even seen the product is exactly the
// "overwhelm upfront" anti-pattern.
export const signupSchema = z
  .object({
    tenantId: tenantIdSchema,
    firstName: z.string().trim().min(1, 'First name is required.'),
    lastName: z.string().trim().min(1, 'Last name is required.'),
    company: z.string().trim().optional(),
    email: emailSchema,
    password: signupPasswordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match.',
    path: ['confirmPassword'],
  });

export type SignupInput = z.infer<typeof signupSchema>;

/** Flattens Zod's field-error map into the flat message list the existing
 * auth forms render (one bullet list of human-readable strings). */
export function flattenZodErrors(error: z.ZodError): string[] {
  return error.issues.map((issue) => issue.message);
}
