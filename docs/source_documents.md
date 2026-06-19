# Source Documents

This register pins the v1 corpus for the BNM Compliance Onboarding Assistant. Raw PDFs are stored locally in `data/raw/` and are not committed to Git.

Access date: 2026-06-19

| Corpus label | Document title | Issuer | Version / date | Source URL | Local filename | SHA-256 |
|---|---|---|---|---|---|---|
| `rmit` | Risk Management in Technology (RMiT) Policy Document | Bank Negara Malaysia | 28 November 2025 | https://www.bnm.gov.my/documents/20124/938039/pd-rmit-nov25.pdf | `data/raw/pd-rmit-nov25.pdf` | `064FFDD45FA2C3FAE16847ED87B9FCAE3EFAECB465D47046C33A5740F155076C` |
| `amlcft_fi` | Anti-Money Laundering, Countering Financing of Terrorism, Countering Proliferation Financing and Targeted Financial Sanctions for Financial Institutions | Bank Negara Malaysia | February 2024 v2 | https://amlcft.bnm.gov.my/documents/6312201/13444269/PD_AMLCFTCPF_TFS_FI_Feb2024_v2.pdf | `data/raw/pd-AMLCFTCPF-TFS-FI-Feb2024-v2.pdf` | `2B16A338C333E94FE4716E1B42EFADCD017761BC6CD8DB6A95E9A67F6FB01109` |

## Inclusion Decision

The v1 corpus includes only documents addressed to financial institutions:

- RMiT is the technology risk baseline for the assistant.
- AML/CFT/CPF/TFS for FIs is the financial-crime compliance baseline.

The v1 corpus excludes DNFBP/NBFI AML/CFT documents, older RMiT versions, RMiT FAQs, and payment-services-specific technology requirements. Those can be added later as explicitly labeled supplemental corpora.

## Ingestion Notes

- Use the `Corpus label` values as stable document identifiers in processed chunks.
- Preserve clause numbers, section titles, appendices, and Standard (S) / Guidance (G) tags where present.
- Record parser-specific issues found during manual PDF inspection in this file or in ingestion documentation once ingestion begins.
