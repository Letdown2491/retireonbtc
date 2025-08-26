# Changelog

All notable changes to **retireonbtc** are documented here.

This project loosely follows the spirit of Keep a Changelog and Semantic Versioning. Dates use `YYYY-MM-DD`. No formal version tags have been created yet; entries are grouped by date.

## 2025-08-26

### Changed
- Minor bugfixes.
- Update CHANGELOG.md
- Update README.md
- Customize fan chart colors
- Prevent Streamlit usage statistics from running.

## 2025-08-25

### Changed
- Use mempool prices

### Docs
- docs: clarify BTC need calculation

## 2025-08-24

### Changed
- Updated feature list in README.md.
- Fixed update_changelog.py logic to display commit description and use title as fallback.
- Update CHANGELOG.md
- Update update-changelog.yml
- Update install deps with git-python to remove subprocess warnings.
- Remove subprocess calls to address Bandit security warnings.
- Rebuild changelog so same day commits are merged under the same date instead of creating new entries.
- Update CHANGELOG.md when a commit is merged into main.
- Update CHANGELOG.md when a new commit is merged into the main branch.
- Rename CHANGELOG.MD to CHANGELOG.md
- Remove 0% growth rate option.
- Fix chart layout and spacing.
- Minor UI tweaks
- style line chart in progress visualization
- Vectorize holdings projection and add test

## 2025-08-23

### Changed
- Add quick-fail option for Bitcoin price and update callers
- Cache bitcoin price in session

## 2025-08-20

### Added
- **Retirement Health Score** (funding ratio & runway years) with helper functions and tests.
- Interactive calculator UX: expanders for Calculator/Results with stateful open/close behavior; auto-rerun after successful calculation to collapse the form.

### Changed
- Validation: reject plans where `retirement_age` exceeds `life_expectancy`; enforce non-negative years in future-value math.
- Config-driven ranges: age inputs derive min/max from `AGE_RANGE` in `config.py`.
- Visualization API simplified: `show_progress_visualization(...)` accepts a precomputed holdings series or derives it; infers ages when appropriate.
- Result rendering: compute holdings series once, feed to visualization, and surface health score metrics.
- Copy/units: normalized wording (“Bitcoin holdings”, “in current dollar terms”) and consistent **₿** units.

### Tests
- Coverage for health scoring, invalid retirement age, and future-value boundary checks; minor test harness updates.

## 2025-08-19

### Added
- BTC accumulation / progress visualization in charts.
- Helper for BTC holdings projection and integration into visualization pipeline.
- Docstrings and type annotations across modules for clarity and tooling.
- Jitter/backoff and constants for Bitcoin price retrieval to reduce request collisions.
- Streamlit caching for Bitcoin price to limit network calls.
- `RetirementPlan` dataclass and refactor to return structured results.
- Shared Bitcoin growth-rate options referenced in UI controls.
- **Security policy** (`SECURITY.md`) with reporting guidelines and scope.
- Automated dependency updates via **Dependabot** configuration.

### Changed / Refactored
- Split `main.py` into focused helper functions for readability and testability.
- Reused common inflation/growth factors to avoid duplication.
- Switched scenarios to a DataFrame structure and standardized column names.
- Centralized/strengthened input validation (including monthly spending).
- Optimized inflation-rate and holdings projection loops.
- Required exactly one growth parameter for future-value calculations.
- Improved `st.session_state` initialization and general state handling.
- Reworked HTTP request handling with session reuse and exponential backoff.
- Removed legacy price cache in favor of the new approach; updated callers.
- Cleaned up unused imports and minor code hygiene items.
- Plotly version range widened to allow latest 6.x (`>=5.24,<7`).

### Fixed
- Minimum spending validation edge case.
- Handling of malformed responses in `get_bitcoin_price`.
- Allow zero monthly investment while keeping validation strict.
- Safe handling for empty scenario comparisons in the compare function.

### Housekeeping
- Introduced initial `CHANGELOG.md`.
- Replaced old workflow-based Dependabot with root `.github/dependabot.yml`.

## 2025-08-18

### Added
- Timestamped cache for Bitcoin price; passed cached price through retirement calculations.
- Data/HTTP dependencies added to requirements.

### Changed / Refactored
- Centralized input validation across the app.

### Docs
- Fixed README setup instructions.

## 2025-08-17

### Added
- Initial code commit: Streamlit calculator, core modules, and config.
- Dev Container folder for consistent local development.
- Initial `requirements.txt` and baseline configuration.

### Docs
- Initial README created and refined.
