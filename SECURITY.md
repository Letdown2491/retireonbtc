# Security Policy

This document describes how to report security issues for **Retire On BTC** and how we handle them.

## Supported Versions

We follow semantic versioning. Unless otherwise noted, we support only the latest stable release and the `main` branch.

| Version | Supported |
|--------:|:---------:|
| main    | ✅        |
| v0.x    | ✅ (latest release only) |

> Security fixes are backported to the latest release only. Older releases may receive fixes at our discretion.

## How to Report a Vulnerability

- **Preferred:** Open a **Private Security Advisory** in GitHub  
  *(GitHub → Security → Advisories → “Report a vulnerability”)*  
- **Alternate:** Email **[security@yourdomain.com]** (PGP key below, if you use one)

Please include:
- A clear description and potential impact
- A minimal proof-of-concept (PoC)
- Affected commit/branch and environment
- Any logs or stack traces (redact secrets)

### Triage & Response Targets

- **Acknowledgement:** within **3 business days**
- **Initial assessment / severity:** within **7 days**
- **Fix ETA:** shared after triage, based on severity

### Coordinated Disclosure

We practice **Coordinated Vulnerability Disclosure (CVD)**:
- We request **up to 90 days** to remediate before public disclosure.
- Critical issues may be addressed faster; we’ll coordinate timelines with you.
- Please do not disclose or discuss publicly until a fix is released and users have a reasonable update window.

## Scope

In scope:
- This repository and code deployed from it (Streamlit app, Python modules)
- CI workflows and configuration in `.github/`

Out of scope (unless a clear exploit is demonstrated):
- Third-party APIs/services (e.g., price data providers)
- Denial-of-Service via excessive traffic or automated scanning
- Best-practice gaps without security impact (e.g., missing security headers on non-prod)
- Social engineering, physical attacks, stolen devices, spam/DMARC only
- Vulnerabilities in dependencies not introduced by our usage (report upstream)

## Safe Harbor

If you follow this policy in good faith:
- We will not pursue legal action for your research.
- Activities should be limited to **your own accounts/data** and **non-destructive** testing.
- Do not exfiltrate data, pivot to other systems, or degrade service.

## Security Practices (Project)

- **Secrets:** No secrets in git. Use `st.secrets` or environment variables. `.streamlit/secrets.toml` is git-ignored.
- **Dependencies:** We run automated checks (e.g., pip-audit, Bandit). Please also report supply-chain concerns.
- **HTTP requests:** Outbound calls use timeouts/retries and strict parsing; endpoints are allow-listed.
- **CI:** Security workflows run on PRs and weekly; findings appear in the Security tab.

## Reporting Guidelines

When possible, provide:
1. **Vulnerability type** (e.g., injection, auth bypass, SSRF)
2. **Attack scenario** and **impact**
3. **Steps to reproduce** with minimal PoC
4. **Suggested remediation** (if known)

We classify severity using **CVSS 3.1** as guidance (Critical/High/Medium/Low).

## Remediation & Credit

- We will confirm when a fix is available and reference it in release notes.
- With your consent, we will credit you in the changelog/security notes.
- We do not run a paid bug-bounty program at this time.

## Version History

- **2025-08-19:** Initial publication of SECURITY.md
