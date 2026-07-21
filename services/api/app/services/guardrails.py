import re
from dataclasses import dataclass, field

# Reason codes only, never the matched excerpt: injected/untrusted text must
# not be echoed back into audit metadata or logs (docs/SECURITY_MODEL.md
# "documents are untrusted data"; "never copy detected secret values into logs").
PROMPT_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ignore_previous_instructions",
        re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    ),
    ("reveal_system_prompt", re.compile(r"reveal\s+(the\s+)?system\s+prompt", re.I)),
    ("bypass_access_control", re.compile(r"bypass\s+access\s+control", re.I)),
    ("act_as_admin", re.compile(r"act\s+as\s+admin", re.I)),
    ("disregard_all_rules", re.compile(r"disregard\s+all\s+rules", re.I)),
    ("show_hidden_data", re.compile(r"show\s+hidden\s+data", re.I)),
]

SENSITIVE_DATA_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"(?<!\d)(\+?\d{1,2}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)"),
    "ssn": re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
    "api_key": re.compile(r"\b(sk|pk|api|token)[-_][A-Za-z0-9]{16,}\b", re.I),
    "credential_assignment": re.compile(r"\b(password|secret|api_key|token)\s*=\s*\S+", re.I),
    "private_key_header": re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
}

# High-confidence credentials block ingestion outright (SECURITY_MODEL.md
# "quarantine: prevent indexing until reviewed"). email/phone are lower-risk
# general PII: flagged per chunk and reported, but do not block ingestion,
# since masking/redaction itself is a later phase, not this one.
HIGH_RISK_SENSITIVE_CATEGORIES = {"ssn", "api_key", "credential_assignment", "private_key_header"}


@dataclass
class InjectionScanResult:
    reason_codes: list[str] = field(default_factory=list)

    @property
    def is_high_risk(self) -> bool:
        return bool(self.reason_codes)


@dataclass
class SensitiveDataScanResult:
    categories: list[str] = field(default_factory=list)

    @property
    def has_findings(self) -> bool:
        return bool(self.categories)

    @property
    def has_high_risk_findings(self) -> bool:
        return any(category in HIGH_RISK_SENSITIVE_CATEGORIES for category in self.categories)


def scan_prompt_injection(content: str) -> InjectionScanResult:
    reason_codes = [code for code, pattern in PROMPT_INJECTION_PATTERNS if pattern.search(content)]
    return InjectionScanResult(reason_codes=reason_codes)


def scan_sensitive_data(content: str) -> SensitiveDataScanResult:
    categories = [
        name for name, pattern in SENSITIVE_DATA_PATTERNS.items() if pattern.search(content)
    ]
    return SensitiveDataScanResult(categories=categories)
