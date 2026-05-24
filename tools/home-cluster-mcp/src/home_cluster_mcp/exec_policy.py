from __future__ import annotations

from dataclasses import asdict, dataclass
from urllib.parse import urlparse

from .config import ExecSettings


Risk = str

DENIED_COMMANDS = {
    "apk",
    "apt",
    "apt-get",
    "ash",
    "base64",
    "bash",
    "chgrp",
    "chmod",
    "chown",
    "cp",
    "dd",
    "dnf",
    "env",
    "ftp",
    "flux",
    "helm",
    "kill",
    "killall",
    "kubectl",
    "mkfs",
    "mount",
    "mv",
    "nc",
    "ncat",
    "npm",
    "openssl",
    "pip",
    "pip3",
    "pkill",
    "pnpm",
    "printenv",
    "rm",
    "rsync",
    "scp",
    "sh",
    "socat",
    "ssh",
    "tar",
    "telnet",
    "tftp",
    "umount",
    "yum",
    "zsh",
}

LOW_RISK_COMMANDS = {
    "df",
    "dig",
    "getent",
    "id",
    "netstat",
    "nslookup",
    "ps",
    "pwd",
    "ss",
    "whoami",
}

MEDIUM_RISK_COMMANDS = {
    "cat",
    "find",
    "ls",
}

METACHARACTERS = ("|", ">", "<", "&&", "||", "`", "$(", ";")
SECRET_PATHS = (
    "/var/run/secrets",
    "/run/secrets",
    "/etc/kubernetes",
    "/etc/rancher",
    "/etc/shadow",
)

CURL_DENIED_FLAGS = {
    "-d",
    "--data",
    "--data-raw",
    "--data-binary",
    "-F",
    "--form",
    "-T",
    "--upload-file",
    "-o",
    "-O",
    "--output",
    "--remote-name",
    "--proxy",
    "--connect-to",
}
WGET_DENIED_FLAGS = {
    "--post-data",
    "--post-file",
    "-O",
    "--output-document",
    "--proxy",
}


@dataclass(frozen=True)
class ExecDecision:
    allowed: bool
    risk: Risk
    reasons: list[str]
    namespace: str
    command: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def classify_exec(namespace: str, argv: list[str], settings: ExecSettings) -> ExecDecision:
    reasons: list[str] = []
    command = [str(item) for item in argv] if isinstance(argv, list) else []

    if not command:
        return _deny(namespace, command, "argv must be a non-empty list")

    if not settings.is_allowed_namespace(namespace):
        return _deny(namespace, command, f"namespace {namespace!r} is not exec-allowed")

    binary = _basename(command[0])
    if binary in DENIED_COMMANDS:
        return _deny(namespace, command, f"command {binary!r} is denied")

    for token in command:
        token_str = str(token)
        if any(marker in token_str for marker in METACHARACTERS):
            return _deny(namespace, command, f"argument contains shell metacharacter: {token_str!r}")
        if _contains_secret_path(token_str):
            return _deny(namespace, command, f"argument references a protected path: {token_str!r}")

    if binary in LOW_RISK_COMMANDS:
        reasons.append(f"{binary!r} is a read-only diagnostic command")
        return ExecDecision(True, "low", reasons, namespace, command)

    if binary == "curl":
        return _classify_curl(namespace, command)

    if binary == "wget":
        return _classify_wget(namespace, command)

    if binary == "cat":
        return _classify_cat(namespace, command)

    if binary == "find":
        return _classify_find(namespace, command)

    if binary in MEDIUM_RISK_COMMANDS:
        reasons.append(f"{binary!r} can inspect filesystem metadata and requires approval")
        return ExecDecision(True, "medium", reasons, namespace, command)

    reasons.append("unknown app command; allowed only as medium-risk approved diagnostic exec")
    return ExecDecision(True, "medium", reasons, namespace, command)


def _classify_curl(namespace: str, command: list[str]) -> ExecDecision:
    for arg in command[1:]:
        if arg in CURL_DENIED_FLAGS:
            return _deny(namespace, command, f"curl flag {arg!r} can write or exfiltrate data")

    methods = _flag_values(command, "-X", "--request")
    for method in methods:
        if method.upper() not in {"GET", "HEAD"}:
            return _deny(namespace, command, f"curl method {method!r} is not read-only")

    urls = _urls_in_args(command[1:])
    external_urls = [url for url in urls if not _is_internal_url(url)]
    if external_urls:
        return _deny(namespace, command, f"external URL is not allowed: {external_urls[0]!r}")

    if urls:
        return ExecDecision(
            True,
            "low",
            ["curl probe targets localhost, cluster DNS, or an internal service URL"],
            namespace,
            command,
        )
    return ExecDecision(True, "low", ["curl without URL, likely version/help check"], namespace, command)


def _classify_wget(namespace: str, command: list[str]) -> ExecDecision:
    for arg in command[1:]:
        if arg in WGET_DENIED_FLAGS:
            return _deny(namespace, command, f"wget flag {arg!r} can write or exfiltrate data")
    urls = _urls_in_args(command[1:])
    external_urls = [url for url in urls if not _is_internal_url(url)]
    if external_urls:
        return _deny(namespace, command, f"external URL is not allowed: {external_urls[0]!r}")
    return ExecDecision(True, "low", ["wget probe is constrained to internal URLs"], namespace, command)


def _classify_cat(namespace: str, command: list[str]) -> ExecDecision:
    allowed_paths = {"/etc/resolv.conf", "/etc/hosts", "/proc/mounts", "/proc/net/route"}
    paths = [arg for arg in command[1:] if not arg.startswith("-")]
    if paths and all(path in allowed_paths for path in paths):
        return ExecDecision(True, "low", ["cat is limited to known-safe diagnostic files"], namespace, command)
    return ExecDecision(True, "medium", ["cat requires approval and protected paths are denied"], namespace, command)


def _classify_find(namespace: str, command: list[str]) -> ExecDecision:
    if "-exec" in command or "-delete" in command:
        return _deny(namespace, command, "find -exec and -delete are denied")
    if not any(arg == "-maxdepth" for arg in command):
        return ExecDecision(
            True,
            "medium",
            ["find without -maxdepth can be expensive and requires approval"],
            namespace,
            command,
        )
    return ExecDecision(True, "medium", ["find is constrained and requires approval"], namespace, command)


def _flag_values(command: list[str], *flags: str) -> list[str]:
    values: list[str] = []
    for index, arg in enumerate(command):
        if arg in flags and index + 1 < len(command):
            values.append(command[index + 1])
    return values


def _urls_in_args(args: list[str]) -> list[str]:
    return [arg for arg in args if arg.startswith(("http://", "https://"))]


def _is_internal_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return (
        host in {"localhost", "127.0.0.1", "::1"}
        or host.endswith(".svc")
        or host.endswith(".svc.cluster.local")
        or host.endswith(".cluster.local")
        or "." not in host
    )


def _contains_secret_path(value: str) -> bool:
    return any(path in value for path in SECRET_PATHS)


def _basename(command: str) -> str:
    return command.rsplit("/", 1)[-1]


def _deny(namespace: str, command: list[str], reason: str) -> ExecDecision:
    return ExecDecision(False, "denied", [reason], namespace, command)
