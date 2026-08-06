# ESLint Remediation Roadmap

## Current Status: 234 open issues (from 284)

### Session Progress

- ✅ Configured modern ESLint v9 with React/TypeScript support
- ✅ Added 40+ global type definitions
- ✅ Auto-fixed 4 early warnings
- ✅ Eliminated 50 issues (18% reduction) with configuration fixes
- ✅ Identified clear patterns for remaining issues

---

## Issue Breakdown & Remediation Strategy

### 1. **@typescript-eslint/no-unused-vars (113 issues)**

**Impact**: Medium | **Difficulty**: High | **Recommended**: Staged Review

These are legitimate unused imports/variables. Two approaches:

**Option A: Prefix with underscore (Quick)**

```typescript
// Before: const unused = 42;
// After:  const _unused = 42;  // Suppress warning
```

**Option B: Remove entirely (Correct)**
Requires careful code review to ensure they're not needed.

**Recommendation**: Start with import scanning, remove unused imports, use `_` prefix for temporarily needed vars.

---

### 2. **react-hooks/set-state-in-effect (44 issues)**

**Impact**: High | **Difficulty**: High | **Recommended**: Refactor

**Pattern**: setState called synchronously inside useEffect

```typescript
// ❌ Current (triggers cascading renders)
useEffect(() => {
  setError('');
  loadData();
}, []);

// ✅ Better (callback-based)
useEffect(() => {
  let active = true;
  loadData().catch((err) => {
    if (active) setError(err.message);
  });
  return () => {
    active = false;
  };
}, []);
```

**Files affected**: `account/wallet`, `benchmarks`, `billing`, `workflows`, `platform/*`
**Recommendation**: Use `useCallback` or move setState to async handler.

---

### 3. **react-hooks/exhaustive-deps (17 issues)**

**Impact**: Medium | **Difficulty**: Medium | **Recommended**: Review

Missing dependencies in effect hooks. Either:

- Add the dependency, OR
- Use `// eslint-disable-next-line` if dependency is intentionally omitted

**Recommendation**: Review each case individually.

---

### 4. **react/no-unescaped-entities (19 issues)**

**Impact**: Low | **Difficulty**: Low | **Recommended**: Auto-fix

Replace HTML entities in JSX:

- `"` → `&quot;`
- `—` → `&mdash;`
- `'` → `&#39;`

**Affected files**: Multiple `page.tsx` files in seo/ and platform/
**Recommendation**: Automated replacement or manual fixes (takes ~5 min).

---

### 5. **no-undef (23 remaining issues)**

**Impact**: Low | **Difficulty**: Low | **Recommended**: Add globals

Missing type definitions for:

- DOM APIs (Storage, IndexedDB)
- Timers (setImmediate)
- Custom types

**Recommendation**: Add remaining globals to eslint.config.js

---

### 6. **Other Issues (18 issues)**

- 3x no-console
- 2x no-empty
- 2x react-hooks/purity
- 4x react-hooks/preserve-manual-memoization
- 3x react/no-unknown-property
- 1x sonarjs/cognitive-complexity
- 1x sonarjs/no-nested-template-literals
- 1x eqeqeq
- 1x @typescript-eslint/no-explicit-any

---

## Implementation Order (by ROI)

### Phase 1: Quick Wins (30 min → -70 issues)

1. ✅ Add remaining DOM globals → -23
2. ⏳ Auto-replace HTML entities → -19
3. ⏳ Suppress no-console in appropriate files → -3
4. ⏳ Review and add exhaustive-deps → -17

### Phase 2: Architectural Fixes (2-3 hours → -100+ issues)

1. Refactor setState in effects → -44
2. Remove unused imports → Depends on review

### Phase 3: Code Review (Ongoing)

1. Verify React component patterns
2. Document architectural constraints

---

## Quick Commands

```powershell
# See all issues with details
node show-issues.js

# Auto-fix simple issues
npx eslint app --fix

# Check progress
npx eslint app 2>&1 | findstr /R "problems"

# TypeScript verification
npx tsc --noEmit
```

---

## Success Criteria

- [ ] 0 errors (down from 222)
- [ ] <20 warnings (down from 18)
- [ ] TypeScript: ✅ Clean
- [ ] No React hook violations
- [ ] Documented architectural patterns

---

## Notes

- **SonarQube Local**: Not reliable for this monorepo. ESLint + TypeScript is the source of truth.
- **SonarCloud**: Could use `.properties` suppressions if needed later.
- **Next.js**: Pages router means large components are expected; focus on code quality, not component size.
