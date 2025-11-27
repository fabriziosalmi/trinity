# Documentation Consolidation Plan

## Current State
- **docs/** - 17 markdown files (legacy, plain markdown)
- **docs_v2/** - 8 markdown files (VitePress-powered, modern)

## Decision: Keep docs_v2/ (VitePress)

### Rationale
1. **Modern Stack**: VitePress provides search, navigation, theming
2. **Already Deployed**: GitHub Pages workflow configured for docs_v2/
3. **Better UX**: Interactive sidebar, search, dark mode
4. **Industry Standard**: VitePress is the standard for Vue/modern docs

### Migration Strategy

#### Step 1: Audit docs/ Content
- [ ] Identify unique content not in docs_v2/
- [ ] Identify deprecated/outdated content to delete
- [ ] Map legacy docs to new docs_v2 structure

#### Step 2: Migrate Valuable Content
Migrate these to docs_v2/:
- `ARCHITECTURE.md` → `docs_v2/1_Architecture/1.0_Overview.md`
- `ASYNC_GUIDE.md` → `docs_v2/3_Features/3.X_Async.md`
- `DOCKER.md` → `docs_v2/2_Development/2.X_Docker.md`
- `NEURAL_HEALER_INTEGRATION.md` → `docs_v2/3_Features/3.X_Neural_Healer.md`
- `MLOPS_SETUP.md` → `docs_v2/2_Development/2.X_MLOps.md`

Skip/Delete (obsolete or redundant):
- `PHASE1_REFACTORING.md` - Historical, not needed
- `PHASE6_ROADMAP.md` - Outdated roadmap
- `GUARDIAN_CODE_REVIEW_FIXES.md` - Historical fixes
- `RELEASE_v0.2.0.md` - Old release notes (keep in CHANGELOG.md)
- `CENTURIA_FACTORY_SUMMARY.md` - Already in docs_v2/

#### Step 3: Update References
- [ ] Update README.md links to point to docs_v2/
- [ ] Update CONTRIBUTING.md links
- [ ] Update package.json scripts
- [ ] Update .github/workflows/docs-quality.yml

#### Step 4: Archive Legacy docs/
- [ ] Move docs/ → docs_legacy/ (git mv)
- [ ] Add README.md to docs_legacy/ explaining deprecation
- [ ] Add note in root README.md: "See docs_v2/ for current documentation"

#### Step 5: Clean Up
- [ ] Remove docs_legacy/ in next major release (v0.8.0)
- [ ] Update all documentation paths in code comments
- [ ] Update .gitignore if needed

## Implementation

### Phase 1: Migrate Key Content (Now)
```bash
# Copy valuable content to docs_v2/
cp docs/DOCKER.md docs_v2/2_Development/2.3_Docker.md
cp docs/ASYNC_GUIDE.md docs_v2/3_Features/3.3_Async.md
# ... etc
```

### Phase 2: Archive Legacy (Now)
```bash
git mv docs docs_legacy
echo "# Legacy Documentation\n\n**DEPRECATED**: See docs_v2/ for current documentation." > docs_legacy/README.md
```

### Phase 3: Update References (Now)
Update all links in:
- README.md
- CONTRIBUTING.md
- *.md files in root

### Phase 4: Remove (v0.8.0)
```bash
git rm -r docs_legacy/
```

## Files to Update

### README.md
```diff
- <a href="docs/">📖 Documentation</a>
+ <a href="https://fabriziosalmi.github.io/trinity/">📖 Documentation</a>
```

### CONTRIBUTING.md
```diff
- See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
+ See [Documentation](https://fabriziosalmi.github.io/trinity/1_Architecture/)
```

### .github/workflows/docs-quality.yml
```diff
  paths:
    - '**.md'
-   - 'docs/**'
+   - 'docs_v2/**'
```

## Timeline
1. ✅ Create this plan
2. ⏳ Migrate key content to docs_v2/
3. ⏳ Archive docs/ → docs_legacy/
4. ⏳ Update all references
5. ⏳ (Future v0.8.0) Remove docs_legacy/
