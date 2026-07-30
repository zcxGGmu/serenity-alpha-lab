from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from serenity_alpha_lab.evidence.report_renderer import RenderedResearchReport


INPUT_FETCH_REPORT_SECURITY_CONTRACT_VERSION = "security.input_fetch_report_hardening@1.0.0"
INPUT_FETCH_REPORT_SECURITY_SCHEMA_NAME = "security.input_fetch_report_hardening"
INPUT_FETCH_REPORT_SECURITY_SCHEMA_VERSION = "1.0.0"

_LOCAL_HOST_SUFFIXES = (".internal", ".local", ".localhost")
_DANGEROUS_HTML_TAG_RE = re.compile(r"<\s*(script|iframe|object|embed|meta|link|style|base)\b", re.IGNORECASE)
_DANGEROUS_HTML_ATTR_RE = re.compile(r"\s(on[a-z0-9_:-]+|srcdoc)\s*=", re.IGNORECASE)
_URL_ATTR_RE = re.compile(
    r"\s(?:href|src|action|formaction)\s*=\s*(?P<quote>['\"])(?P<url>.*?)(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)
_SCRIPT_SAMPLE_RE = re.compile(rb"(<\s*script\b|javascript\s*:|<\s*html\b|<\s*svg\b)", re.IGNORECASE)
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class InputFetchSecurityError(ValueError):
    """Raised when input/fetch/report security metadata is structurally invalid."""


class InputSecurityDecisionStatus(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"


class InputSecurityIssueCode(StrEnum):
    URL_SCHEME_FORBIDDEN = "url_scheme_forbidden"
    URL_CREDENTIALS_FORBIDDEN = "url_credentials_forbidden"
    URL_HOST_REQUIRED = "url_host_required"
    URL_LOCAL_HOST = "url_local_host"
    URL_PRIVATE_ADDRESS = "url_private_address"
    URL_HOST_FORBIDDEN = "url_host_forbidden"
    URL_DNS_RESOLUTION_REQUIRED = "url_dns_resolution_required"
    URL_REDIRECT_LIMIT_EXCEEDED = "url_redirect_limit_exceeded"
    RESPONSE_TOO_LARGE = "response_too_large"
    RESPONSE_CONTENT_TYPE_FORBIDDEN = "response_content_type_forbidden"
    FILENAME_UNSAFE = "filename_unsafe"
    FILE_SIZE_EXCEEDED = "file_size_exceeded"
    FILE_EXTENSION_FORBIDDEN = "file_extension_forbidden"
    FILE_CONTENT_TYPE_FORBIDDEN = "file_content_type_forbidden"
    FILE_SIGNATURE_FORBIDDEN = "file_signature_forbidden"
    REPORT_ACTIVE_CONTENT = "report_active_content"
    REPORT_UNSAFE_LINK = "report_unsafe_link"


@dataclass(frozen=True, slots=True)
class InputSecurityIssue:
    code: InputSecurityIssueCode | str
    message: str
    field_path: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", InputSecurityIssueCode(self.code))
        object.__setattr__(self, "message", _required_string("message", self.message))
        object.__setattr__(self, "field_path", _optional_string(self.field_path))

    def to_record(self) -> dict[str, str]:
        return _drop_none(
            {
                "code": self.code.value,
                "message": self.message,
                "field_path": self.field_path,
            }
        )


@dataclass(frozen=True, slots=True)
class UrlFetchHop:
    url: str
    resolved_ip_addresses: Sequence[str] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "url", _required_string("url", self.url))
        object.__setattr__(self, "resolved_ip_addresses", tuple(str(item) for item in self.resolved_ip_addresses))

    def to_record(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "canonical_url": _canonical_url_or_original(self.url),
            "resolved_ip_addresses": list(self.resolved_ip_addresses),
        }


@dataclass(frozen=True, slots=True)
class UrlFetchCandidate:
    request: UrlFetchHop
    redirects: Sequence[UrlFetchHop] = ()
    response_content_type: str | None = None
    response_size_bytes: int | None = None

    def __post_init__(self) -> None:
        if type(self.request) is not UrlFetchHop:
            raise InputFetchSecurityError("request must be a UrlFetchHop")
        redirects = tuple(self.redirects)
        for redirect in redirects:
            if type(redirect) is not UrlFetchHop:
                raise InputFetchSecurityError("redirects must contain UrlFetchHop objects")
        object.__setattr__(self, "redirects", redirects)
        object.__setattr__(self, "response_content_type", _optional_string(self.response_content_type))
        if self.response_size_bytes is not None:
            if type(self.response_size_bytes) is not int or self.response_size_bytes < 0:
                raise InputFetchSecurityError("response_size_bytes must be a non-negative integer")

    @property
    def hops(self) -> tuple[UrlFetchHop, ...]:
        return (self.request, *tuple(self.redirects))

    def to_record(self) -> dict[str, Any]:
        return _drop_none(
            {
                "request": self.request.to_record(),
                "redirects": [hop.to_record() for hop in self.redirects],
                "response_content_type": self.response_content_type,
                "response_size_bytes": self.response_size_bytes,
            }
        )


@dataclass(frozen=True, slots=True)
class UrlFetchPolicyDecision:
    candidate: UrlFetchCandidate
    status: InputSecurityDecisionStatus | str
    issues: Sequence[InputSecurityIssue]
    canonical_url: str | None
    effective_url: str | None
    max_redirects: int
    max_response_bytes: int
    allowed_hosts: Sequence[str]
    allowed_content_types: Sequence[str]
    contract_version: str = INPUT_FETCH_REPORT_SECURITY_CONTRACT_VERSION
    schema_name: str = INPUT_FETCH_REPORT_SECURITY_SCHEMA_NAME
    schema_version: str = INPUT_FETCH_REPORT_SECURITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.candidate) is not UrlFetchCandidate:
            raise InputFetchSecurityError("candidate must be a UrlFetchCandidate")
        object.__setattr__(self, "status", InputSecurityDecisionStatus(self.status))
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "allowed_hosts", tuple(self.allowed_hosts))
        object.__setattr__(self, "allowed_content_types", tuple(self.allowed_content_types))

    @property
    def decision_hash(self) -> str:
        return _hash_record(self.to_record(include_hash=False))

    def to_record(self, *, include_hash: bool = True) -> dict[str, Any]:
        record = _drop_none(
            {
                "contract_version": self.contract_version,
                "schema_name": self.schema_name,
                "schema_version": self.schema_version,
                "status": self.status.value,
                "candidate": self.candidate.to_record(),
                "canonical_url": self.canonical_url,
                "effective_url": self.effective_url,
                "issues": [issue.to_record() for issue in self.issues],
                "max_redirects": self.max_redirects,
                "max_response_bytes": self.max_response_bytes,
                "allowed_hosts": list(self.allowed_hosts),
                "allowed_content_types": list(self.allowed_content_types),
            }
        )
        if include_hash:
            record["decision_hash"] = self.decision_hash
        return record


@dataclass(frozen=True, slots=True)
class UrlFetchPolicy:
    allowed_hosts: Sequence[str]
    allowed_content_types: Sequence[str] = ("text/html", "text/plain", "application/json", "application/pdf")
    max_redirects: int = 3
    max_response_bytes: int = 5 * 1024 * 1024
    allow_http_urls: bool = False
    require_resolved_ips: bool = True

    @classmethod
    def default(
        cls,
        *,
        allowed_hosts: Sequence[str],
        max_redirects: int = 3,
        max_response_bytes: int = 5 * 1024 * 1024,
    ) -> UrlFetchPolicy:
        return cls(
            allowed_hosts=allowed_hosts,
            max_redirects=max_redirects,
            max_response_bytes=max_response_bytes,
        )

    def __post_init__(self) -> None:
        hosts = tuple(_normalize_host(host) for host in self.allowed_hosts)
        if not hosts:
            raise InputFetchSecurityError("allowed_hosts is required")
        object.__setattr__(self, "allowed_hosts", hosts)
        content_types = tuple(_normalize_content_type(item) for item in self.allowed_content_types)
        if not content_types:
            raise InputFetchSecurityError("allowed_content_types is required")
        object.__setattr__(self, "allowed_content_types", content_types)
        if type(self.max_redirects) is not int or self.max_redirects < 0:
            raise InputFetchSecurityError("max_redirects must be a non-negative integer")
        if type(self.max_response_bytes) is not int or self.max_response_bytes <= 0:
            raise InputFetchSecurityError("max_response_bytes must be a positive integer")

    def evaluate(self, candidate: UrlFetchCandidate) -> UrlFetchPolicyDecision:
        if type(candidate) is not UrlFetchCandidate:
            raise InputFetchSecurityError("candidate must be a UrlFetchCandidate")

        issues: list[InputSecurityIssue] = []
        if len(candidate.redirects) > self.max_redirects:
            issues.append(
                InputSecurityIssue(
                    InputSecurityIssueCode.URL_REDIRECT_LIMIT_EXCEEDED,
                    f"redirect count exceeds limit: {len(candidate.redirects)} > {self.max_redirects}",
                    field_path="redirects",
                )
            )

        for index, hop in enumerate(candidate.hops):
            path = "request.url" if index == 0 else f"redirects[{index - 1}].url"
            issues.extend(self._url_issues(hop, field_path=path))

        if candidate.response_size_bytes is not None and candidate.response_size_bytes > self.max_response_bytes:
            issues.append(
                InputSecurityIssue(
                    InputSecurityIssueCode.RESPONSE_TOO_LARGE,
                    "response size exceeds configured limit",
                    field_path="response_size_bytes",
                )
            )
        if candidate.response_content_type is not None:
            content_type = _normalize_content_type(candidate.response_content_type)
            if content_type not in set(self.allowed_content_types):
                issues.append(
                    InputSecurityIssue(
                        InputSecurityIssueCode.RESPONSE_CONTENT_TYPE_FORBIDDEN,
                        f"response content type is not allowed: {content_type}",
                        field_path="response_content_type",
                    )
                )

        canonical_url = _canonical_url_or_none(candidate.request.url)
        effective_url = _canonical_url_or_none(candidate.hops[-1].url)
        return UrlFetchPolicyDecision(
            candidate=candidate,
            status=InputSecurityDecisionStatus.DENIED if issues else InputSecurityDecisionStatus.ALLOWED,
            issues=tuple(issues),
            canonical_url=canonical_url,
            effective_url=effective_url,
            max_redirects=self.max_redirects,
            max_response_bytes=self.max_response_bytes,
            allowed_hosts=self.allowed_hosts,
            allowed_content_types=self.allowed_content_types,
        )

    def _url_issues(self, hop: UrlFetchHop, *, field_path: str) -> tuple[InputSecurityIssue, ...]:
        parsed = urlsplit(hop.url)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"}:
            return (
                InputSecurityIssue(
                    InputSecurityIssueCode.URL_SCHEME_FORBIDDEN,
                    "URL scheme must be http or https",
                    field_path=field_path,
                ),
            )
        issues: list[InputSecurityIssue] = []
        if scheme == "http" and not self.allow_http_urls:
            issues.append(InputSecurityIssue(InputSecurityIssueCode.URL_SCHEME_FORBIDDEN, "URL scheme must be https", field_path))
        if parsed.username or parsed.password:
            issues.append(
                InputSecurityIssue(
                    InputSecurityIssueCode.URL_CREDENTIALS_FORBIDDEN,
                    "URL credentials are forbidden",
                    field_path=field_path,
                )
            )
        host = (parsed.hostname or "").lower().rstrip(".")
        if not host:
            issues.append(InputSecurityIssue(InputSecurityIssueCode.URL_HOST_REQUIRED, "URL host is required", field_path))
            return tuple(issues)
        if host == "localhost" or host.endswith(_LOCAL_HOST_SUFFIXES):
            issues.append(
                InputSecurityIssue(InputSecurityIssueCode.URL_LOCAL_HOST, "local hostnames are forbidden", field_path)
            )
        host_is_private_or_local = _is_private_or_local_address(host)
        if host_is_private_or_local:
            issues.append(
                InputSecurityIssue(
                    InputSecurityIssueCode.URL_PRIVATE_ADDRESS,
                    "URL host resolves to a local or private address",
                    field_path=field_path,
                )
            )
        elif host not in set(self.allowed_hosts):
            issues.append(
                InputSecurityIssue(
                    InputSecurityIssueCode.URL_HOST_FORBIDDEN,
                    "URL host is not in the fetch allowlist",
                    field_path=field_path,
                )
            )
        if self.require_resolved_ips and not hop.resolved_ip_addresses:
            issues.append(
                InputSecurityIssue(
                    InputSecurityIssueCode.URL_DNS_RESOLUTION_REQUIRED,
                    "resolved IP addresses are required before fetching",
                    field_path=f"{field_path}.resolved_ip_addresses",
                )
            )
        for index, value in enumerate(hop.resolved_ip_addresses):
            if _is_private_or_local_address(value):
                issues.append(
                    InputSecurityIssue(
                        InputSecurityIssueCode.URL_PRIVATE_ADDRESS,
                        "resolved IP address is local, private or otherwise non-public",
                        field_path=f"{field_path}.resolved_ip_addresses[{index}]",
                    )
                )
        return tuple(issues)


@dataclass(frozen=True, slots=True)
class FileUploadCandidate:
    filename: str
    content_type: str
    size_bytes: int
    content_sample: bytes = b""

    def __post_init__(self) -> None:
        object.__setattr__(self, "filename", _required_string("filename", self.filename))
        object.__setattr__(self, "content_type", _required_string("content_type", self.content_type))
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise InputFetchSecurityError("size_bytes must be a non-negative integer")
        if type(self.content_sample) is not bytes:
            raise InputFetchSecurityError("content_sample must be bytes")

    @property
    def extension(self) -> str:
        name = self.filename.rsplit("/", maxsplit=1)[-1].rsplit("\\", maxsplit=1)[-1]
        if "." not in name:
            return ""
        return "." + name.rsplit(".", maxsplit=1)[-1].lower()


@dataclass(frozen=True, slots=True)
class FileUploadScanResult:
    candidate: FileUploadCandidate
    status: InputSecurityDecisionStatus | str
    issues: Sequence[InputSecurityIssue]
    sanitized_filename: str
    content_sha256: str
    max_size_bytes: int
    allowed_extensions: Sequence[str]
    allowed_content_types: Sequence[str]
    contract_version: str = INPUT_FETCH_REPORT_SECURITY_CONTRACT_VERSION
    schema_name: str = INPUT_FETCH_REPORT_SECURITY_SCHEMA_NAME
    schema_version: str = INPUT_FETCH_REPORT_SECURITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.candidate) is not FileUploadCandidate:
            raise InputFetchSecurityError("candidate must be a FileUploadCandidate")
        object.__setattr__(self, "status", InputSecurityDecisionStatus(self.status))
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "allowed_extensions", tuple(self.allowed_extensions))
        object.__setattr__(self, "allowed_content_types", tuple(self.allowed_content_types))

    @property
    def decision_hash(self) -> str:
        return _hash_record(self.to_record(include_hash=False))

    def to_record(self, *, include_hash: bool = True) -> dict[str, Any]:
        record = {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "filename": self.candidate.filename,
            "content_type": _normalize_content_type(self.candidate.content_type),
            "size_bytes": self.candidate.size_bytes,
            "sanitized_filename": self.sanitized_filename,
            "content_sha256": self.content_sha256,
            "max_size_bytes": self.max_size_bytes,
            "allowed_extensions": list(self.allowed_extensions),
            "allowed_content_types": list(self.allowed_content_types),
            "issues": [issue.to_record() for issue in self.issues],
        }
        if include_hash:
            record["decision_hash"] = self.decision_hash
        return record


@dataclass(frozen=True, slots=True)
class FileUploadPolicy:
    max_size_bytes: int = 10 * 1024 * 1024
    allowed_extensions: Sequence[str] = (".pdf", ".txt", ".csv", ".json")
    allowed_content_types: Sequence[str] = ("application/pdf", "text/plain", "text/csv", "application/json")

    @classmethod
    def default(cls, *, max_size_bytes: int = 10 * 1024 * 1024) -> FileUploadPolicy:
        return cls(max_size_bytes=max_size_bytes)

    def __post_init__(self) -> None:
        if type(self.max_size_bytes) is not int or self.max_size_bytes <= 0:
            raise InputFetchSecurityError("max_size_bytes must be a positive integer")
        object.__setattr__(self, "allowed_extensions", tuple(item.lower() for item in self.allowed_extensions))
        object.__setattr__(self, "allowed_content_types", tuple(_normalize_content_type(item) for item in self.allowed_content_types))

    def scan(self, candidate: FileUploadCandidate) -> FileUploadScanResult:
        if type(candidate) is not FileUploadCandidate:
            raise InputFetchSecurityError("candidate must be a FileUploadCandidate")
        issues: list[InputSecurityIssue] = []
        sanitized_filename = _sanitize_filename(candidate.filename)
        if not _is_safe_filename(candidate.filename):
            issues.append(
                InputSecurityIssue(
                    InputSecurityIssueCode.FILENAME_UNSAFE,
                    "filename must be a basename without traversal or control characters",
                    field_path="filename",
                )
            )
        if candidate.size_bytes > self.max_size_bytes:
            issues.append(
                InputSecurityIssue(
                    InputSecurityIssueCode.FILE_SIZE_EXCEEDED,
                    "file size exceeds configured limit",
                    field_path="size_bytes",
                )
            )
        if candidate.extension not in set(self.allowed_extensions):
            issues.append(
                InputSecurityIssue(
                    InputSecurityIssueCode.FILE_EXTENSION_FORBIDDEN,
                    f"file extension is not allowed: {candidate.extension or '<none>'}",
                    field_path="filename",
                )
            )
        content_type = _normalize_content_type(candidate.content_type)
        if content_type not in set(self.allowed_content_types):
            issues.append(
                InputSecurityIssue(
                    InputSecurityIssueCode.FILE_CONTENT_TYPE_FORBIDDEN,
                    f"content type is not allowed: {content_type}",
                    field_path="content_type",
                )
            )
        if _has_forbidden_file_signature(candidate.content_sample):
            issues.append(
                InputSecurityIssue(
                    InputSecurityIssueCode.FILE_SIGNATURE_FORBIDDEN,
                    "file sample contains executable, script or active markup signature",
                    field_path="content_sample",
                )
            )
        return FileUploadScanResult(
            candidate=candidate,
            status=InputSecurityDecisionStatus.DENIED if issues else InputSecurityDecisionStatus.ALLOWED,
            issues=tuple(issues),
            sanitized_filename=sanitized_filename,
            content_sha256=_sha256_bytes(candidate.content_sample),
            max_size_bytes=self.max_size_bytes,
            allowed_extensions=self.allowed_extensions,
            allowed_content_types=self.allowed_content_types,
        )


@dataclass(frozen=True, slots=True)
class ReportRenderSecurityDecision:
    status: InputSecurityDecisionStatus | str
    issues: Sequence[InputSecurityIssue]
    rendering_hash: str | None = None
    checked_value: str | None = None
    contract_version: str = INPUT_FETCH_REPORT_SECURITY_CONTRACT_VERSION
    schema_name: str = INPUT_FETCH_REPORT_SECURITY_SCHEMA_NAME
    schema_version: str = INPUT_FETCH_REPORT_SECURITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", InputSecurityDecisionStatus(self.status))
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "checked_value", _optional_string(self.checked_value))

    @property
    def decision_hash(self) -> str:
        return _hash_record(self.to_record(include_hash=False))

    def to_record(self, *, include_hash: bool = True) -> dict[str, Any]:
        record = _drop_none(
            {
                "contract_version": self.contract_version,
                "schema_name": self.schema_name,
                "schema_version": self.schema_version,
                "status": self.status.value,
                "rendering_hash": self.rendering_hash,
                "checked_value": self.checked_value,
                "issues": [issue.to_record() for issue in self.issues],
            }
        )
        if include_hash:
            record["decision_hash"] = self.decision_hash
        return record


@dataclass(frozen=True, slots=True)
class ReportRenderSecurityPolicy:
    allowed_link_schemes: Sequence[str] = ("https", "artifact")
    allowed_link_hosts: Sequence[str] = ()

    @classmethod
    def default(cls) -> ReportRenderSecurityPolicy:
        return cls()

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_link_schemes", tuple(item.lower() for item in self.allowed_link_schemes))
        object.__setattr__(self, "allowed_link_hosts", tuple(_normalize_host(item) for item in self.allowed_link_hosts))

    def validate(self, rendered_report: RenderedResearchReport) -> ReportRenderSecurityDecision:
        if type(rendered_report) is not RenderedResearchReport:
            raise InputFetchSecurityError("rendered_report must be a RenderedResearchReport")
        issues = list(_html_issues(rendered_report.html, link_policy=self, field_path="html"))
        return ReportRenderSecurityDecision(
            status=InputSecurityDecisionStatus.DENIED if issues else InputSecurityDecisionStatus.ALLOWED,
            issues=tuple(issues),
            rendering_hash=rendered_report.rendering_hash,
        )

    def validate_source_link(self, value: str | None) -> ReportRenderSecurityDecision:
        if value is None:
            return ReportRenderSecurityDecision(status=InputSecurityDecisionStatus.ALLOWED, issues=())
        if type(value) is not str or not value.strip():
            return ReportRenderSecurityDecision(
                status=InputSecurityDecisionStatus.DENIED,
                issues=(
                    InputSecurityIssue(
                        InputSecurityIssueCode.REPORT_UNSAFE_LINK,
                        "report source link must be a non-empty string",
                        field_path="source_link",
                    ),
                ),
                checked_value=str(value),
            )
        issue = self._unsafe_link_issue(value, field_path="source_link")
        issues = () if issue is None else (issue,)
        return ReportRenderSecurityDecision(
            status=InputSecurityDecisionStatus.DENIED if issues else InputSecurityDecisionStatus.ALLOWED,
            issues=issues,
            checked_value=value,
        )

    def _unsafe_link_issue(self, value: str, *, field_path: str) -> InputSecurityIssue | None:
        parsed = urlsplit(value.strip())
        scheme = parsed.scheme.lower()
        if scheme not in set(self.allowed_link_schemes):
            return InputSecurityIssue(
                InputSecurityIssueCode.REPORT_UNSAFE_LINK,
                "report link scheme is not allowed",
                field_path=field_path,
            )
        if scheme == "https":
            host = (parsed.hostname or "").lower().rstrip(".")
            if not host:
                return InputSecurityIssue(
                    InputSecurityIssueCode.REPORT_UNSAFE_LINK,
                    "report https link host is required",
                    field_path=field_path,
                )
            if _is_private_or_local_address(host) or host == "localhost" or host.endswith(_LOCAL_HOST_SUFFIXES):
                return InputSecurityIssue(
                    InputSecurityIssueCode.REPORT_UNSAFE_LINK,
                    "report link must not target local or private addresses",
                    field_path=field_path,
                )
            if self.allowed_link_hosts and host not in set(self.allowed_link_hosts):
                return InputSecurityIssue(
                    InputSecurityIssueCode.REPORT_UNSAFE_LINK,
                    "report link host is not in the allowlist",
                    field_path=field_path,
                )
        return None


def default_report_security_headers() -> dict[str, str]:
    return {
        "Content-Security-Policy": (
            "default-src 'none'; "
            "img-src 'self' data:; "
            "style-src 'self'; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'none'; "
            "form-action 'none'"
        ),
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "X-Frame-Options": "DENY",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }


def _html_issues(
    html: str,
    *,
    link_policy: ReportRenderSecurityPolicy,
    field_path: str,
) -> tuple[InputSecurityIssue, ...]:
    issues: list[InputSecurityIssue] = []
    if _DANGEROUS_HTML_TAG_RE.search(html) or _DANGEROUS_HTML_ATTR_RE.search(html):
        issues.append(
            InputSecurityIssue(
                InputSecurityIssueCode.REPORT_ACTIVE_CONTENT,
                "report HTML contains active tags or event handler attributes",
                field_path=field_path,
            )
        )
    for match in _URL_ATTR_RE.finditer(html):
        url = match.group("url").strip()
        issue = link_policy._unsafe_link_issue(url, field_path=f"{field_path}.{match.group(0).split('=', 1)[0].strip()}")
        if issue is not None:
            issues.append(issue)
    return tuple(issues)


def _canonical_url_or_none(value: str) -> str | None:
    try:
        return _canonicalize_url(value)
    except InputFetchSecurityError:
        return None


def _canonical_url_or_original(value: str) -> str:
    return _canonical_url_or_none(value) or value


def _canonicalize_url(value: str) -> str:
    url = _required_string("url", value).strip()
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise InputFetchSecurityError("url must use http(s)")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise InputFetchSecurityError("url host is required")
    try:
        port = parsed.port
    except ValueError as exc:
        raise InputFetchSecurityError("url port is invalid") from exc
    netloc = host
    if port is not None:
        netloc = f"{host}:{port}"
    path = quote(parsed.path or "/", safe="/:@-._~")
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def _normalize_host(value: str) -> str:
    host = _required_string("host", value).lower().rstrip(".")
    if "/" in host or "@" in host:
        raise InputFetchSecurityError("host allowlist entries must be hostnames only")
    return host


def _normalize_content_type(value: str) -> str:
    return _required_string("content_type", value).split(";", maxsplit=1)[0].strip().lower()


def _is_private_or_local_address(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value.strip("[]"))
    except ValueError:
        return False
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _is_safe_filename(value: str) -> bool:
    if not value or value != value.strip():
        return False
    if "/" in value or "\\" in value or "\x00" in value:
        return False
    if value in {".", ".."} or ".." in value:
        return False
    if any(ord(ch) < 32 for ch in value):
        return False
    return True


def _sanitize_filename(value: str) -> str:
    basename = value.rsplit("/", maxsplit=1)[-1].rsplit("\\", maxsplit=1)[-1].strip()
    sanitized = _SAFE_FILENAME_RE.sub("_", basename).strip("._")
    return sanitized or "upload"


def _has_forbidden_file_signature(sample: bytes) -> bool:
    lowered = sample[:512].lower()
    return (
        sample.startswith((b"MZ", b"\x7fELF"))
        or lowered.startswith(b"#!")
        or _SCRIPT_SAMPLE_RE.search(lowered) is not None
    )


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise InputFetchSecurityError(f"{field_name} is required")
    return value


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_string("optional string", value)


def _hash_record(record: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(record).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(_json_ready(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except TypeError as exc:
        raise InputFetchSecurityError("value must be JSON serializable") from exc


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, tuple | list):
        return [_json_ready(item) for item in value]
    if isinstance(value, StrEnum):
        return value.value
    return value


def _drop_none(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if value is not None}


__all__ = [
    "INPUT_FETCH_REPORT_SECURITY_CONTRACT_VERSION",
    "INPUT_FETCH_REPORT_SECURITY_SCHEMA_NAME",
    "INPUT_FETCH_REPORT_SECURITY_SCHEMA_VERSION",
    "FileUploadCandidate",
    "FileUploadPolicy",
    "FileUploadScanResult",
    "InputFetchSecurityError",
    "InputSecurityDecisionStatus",
    "InputSecurityIssue",
    "InputSecurityIssueCode",
    "ReportRenderSecurityDecision",
    "ReportRenderSecurityPolicy",
    "UrlFetchCandidate",
    "UrlFetchHop",
    "UrlFetchPolicy",
    "UrlFetchPolicyDecision",
    "default_report_security_headers",
]
