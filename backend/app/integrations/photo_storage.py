"""Private Supabase Storage adapter; no keys or photo bytes are logged."""

from datetime import timedelta


class PhotoStorage:
    def save(self, path: str, content: bytes, content_type: str) -> str:
        # TODO: accept sanitized bytes only; return a private object path, not a public URL.
        raise NotImplementedError("Private photo storage is not implemented.")

    def signed_url(self, path: str, expires: timedelta) -> str:
        # TODO: call only after moderation/author authorization checks.
        raise NotImplementedError("Private photo access is not implemented.")
