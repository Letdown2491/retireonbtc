# Security Policy

This document explains how to report security issues for **Retire On BTC** and how we handle them.  
**License alignment:** This policy is informational. Nothing here limits, conditions, or alters the rights granted by the GNU GPL v3.0; in particular, it does **not** impose any additional restrictions on copying, modifying, or redistributing the software (GPLv3 §10). Requests below are cooperative, not contractual. 

## Supported Versions

We generally support the latest release (if any) and `main`.

| Version | Supported |
|-------:|:---------:|
| main   | ✅        |
| latest release | ✅ |

> Security fixes are backported to the latest release only. Older releases may receive fixes at our discretion.

## How to Report a Vulnerability

- **Preferred:** Open a **Private Security Advisory** in GitHub  
  *(GitHub → Security → Advisories → “Report a vulnerability”)*

Please include:
- Clear description and potential impact
- Minimal PoC/repro steps
- Affected commit/branch and environment
- Relevant logs/stack traces (redact secrets)

### Triage Targets
- **Acknowledgement:** within **3 business days**
- **Initial assessment / severity:** within **7 days**
- **Fix ETA:** shared after triage, based on severity and complexity

## Coordinated Vulnerability Disclosure (CVD)

We follow CVD best practices. We **request** (not require) up to **90 days** for remediation before public disclosure; critical issues may be addressed faster. We ask that you coordinate public discussion until a fix is released and users have a reasonable update window. These are cooperative requests only and do **not** restrict your GPL rights.

## Scope

**In scope**
- This repository and code deployed from it (Streamlit app, Python modules)
- CI workflows and configuration in `.github/`

**Out of scope** (unless a clear, exploitable impact is demonstrated)
- Third-party services/APIs (report upstream)
- Pure DoS via high-rate traffic or automated scanning
- Best-practice nits without security impact (e.g., missing non-auth headers on non-prod)
- Social engineering, physical attacks, spam/DMARC issues

## Safe Harbor

If you act in good faith and within this policy’s intent:
- We will not pursue legal action for your research.
- Limit testing to **your own accounts/data** and use **non-destructive** methods.
- Do not exfiltrate data, pivot to other systems, or degrade service.

## Security Practices (Project)

- **No secrets in git.** Use `st.secrets` or environment variables; `.streamlit/secrets.toml` is git-ignored.
- **Automated checks.** We run GitHub code scanning (CodeQL) and static analysis (Bandit) on PRs and on a weekly schedule; results appear in the Security tab.
- **Dependencies.** We keep dependencies current (e.g., Dependabot) and review security advisories.
- **Networking.** Outbound calls use timeouts/retries and strict response parsing.

## Reporting Guidelines (What Helps Most)

1. Vulnerability type (e.g., injection, auth bypass, SSRF) and affected area
2. Attack scenario and impact
3. Minimal steps to reproduce
4. Suggested remediation/patch (if known)

We use **CVSS 3.1** as guidance for severity.

## Remediation & Credit

- We’ll confirm when a fix is available and reference it in release notes.
- With your consent, we’ll credit you in the changelog/security notes.
- We don’t operate a paid bounty at this time.

## License Compatibility

This project is licensed under **GPL-3.0**. Nothing in this policy shall be construed to:
- Add any further restrictions to the rights granted by GPL-3.0; or
- Create confidentiality or non-disclosure obligations that would limit your ability to exercise GPL-granted freedoms.

## History

- **2025-08-27:** Clarified CVD as a **request**, added explicit GPL-3.0 compatibility note, tuned automation language.
- **2025-08-19:** Initial publication of SECURITY.md
