import json
import logging
import os
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from uuid import UUID, NAMESPACE_DNS, uuid5
from urllib.parse import quote

from aiohttp import ClientError, ClientSession, ClientTimeout

from database import crud
from database.models import User, VpnProfile

logger = logging.getLogger(__name__)


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


_VLESS_HOST = _env("VLESS_HOST", "example.com") or "example.com"
_VLESS_PORT = int(_env("VLESS_PORT", "443") or 443)
_VLESS_TRANSPORT = _env("VLESS_TRANSPORT", "ws") or "ws"
_VLESS_SECURITY = _env("VLESS_SECURITY", "tls") or "tls"
_VLESS_FLOW = _env("VLESS_FLOW")
_VLESS_PATH = _env("VLESS_WS_PATH", "/facevpn")
_VLESS_SNI = _env("VLESS_SNI", _VLESS_HOST)
_VLESS_LABEL_TEMPLATE = _env("VLESS_LABEL_TEMPLATE") or _env("VLESS_LABEL", "FaceVPN {tg_id}") or "FaceVPN {tg_id}"
_VLESS_ALPN_RAW = _env("VLESS_ALPN", "h2,http/1.1") or "h2,http/1.1"
_VLESS_ALPN = [entry.strip() for entry in _VLESS_ALPN_RAW.split(",") if entry.strip()]
if not _VLESS_ALPN:
    _VLESS_ALPN = ["h2", "http/1.1"]

_VLESS_PROVISION_URL = _env("VLESS_PROVISION_URL")
_VLESS_PROVISION_TOKEN = _env("VLESS_PROVISION_TOKEN")
try:
    _VLESS_PROVISION_TIMEOUT = float(_env("VLESS_PROVISION_TIMEOUT", "20") or 20)
except ValueError:
    _VLESS_PROVISION_TIMEOUT = 20.0

_UUID_NAMESPACE_SEED = _env("VLESS_UUID_NAMESPACE", "facevpn") or "facevpn"
try:
    _UUID_NAMESPACE = UUID(_UUID_NAMESPACE_SEED)
except ValueError:
    _UUID_NAMESPACE = uuid5(NAMESPACE_DNS, _UUID_NAMESPACE_SEED)


@dataclass(slots=True)
class ProvisionResult:
    remote_id: Optional[str]
    overrides: Dict[str, Any]
    raw: Optional[Dict[str, Any]]
    error: Optional[str]


@dataclass(slots=True)
class VlessProfileData:
    user_id: int
    uuid: str
    label: str
    server: str
    port: int
    transport: str
    security: str
    flow: Optional[str]
    sni: Optional[str]
    path: Optional[str]

    @classmethod
    def from_model(cls, model: VpnProfile) -> "VlessProfileData":
        return cls(
            user_id=model.user_id,
            uuid=model.uuid,
            label=model.label,
            server=model.server,
            port=model.port,
            transport=model.transport,
            security=model.security,
            flow=model.flow,
            sni=model.sni,
            path=model.path,
        )

    def to_payload(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "label": self.label,
            "server": self.server,
            "port": self.port,
            "transport": self.transport,
            "security": self.security,
            "flow": self.flow,
            "sni": self.sni,
            "path": self.path,
        }

    def as_db_kwargs(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "uuid": self.uuid,
            "label": self.label,
            "server": self.server,
            "port": self.port,
            "transport": self.transport,
            "security": self.security,
            "flow": self.flow,
            "sni": self.sni,
            "path": self.path,
        }

    def apply_overrides(self, overrides: Dict[str, Any]) -> "VlessProfileData":
        if not overrides:
            return self

        def _pick(*keys: str) -> Optional[Any]:
            for key in keys:
                if key in overrides and overrides[key] not in (None, ""):
                    return overrides[key]
            return None

        uuid_value = _pick("uuid", "id")
        label_value = _pick("label", "remark", "name")
        server_value = _pick("server", "address", "host")
        port_value = _pick("port")
        transport_value = _pick("transport", "type")
        security_value = _pick("security")
        flow_value = _pick("flow")
        sni_value = _pick("sni", "serverName", "host")
        path_value = _pick("path", "serviceName")

        return replace(
            self,
            uuid=str(uuid_value) if uuid_value else self.uuid,
            label=str(label_value) if label_value else self.label,
            server=str(server_value) if server_value else self.server,
            port=int(port_value) if port_value is not None else self.port,
            transport=str(transport_value) if transport_value else self.transport,
            security=str(security_value) if security_value else self.security,
            flow=_normalize_optional(flow_value),
            sni=_normalize_optional(sni_value),
            path=_normalize_path(path_value, transport=str(transport_value) if transport_value else self.transport),
        )

    def build_uri(self) -> str:
        params = [
            ("encryption", "none"),
            ("security", self.security),
            ("type", self.transport),
        ]
        if self.sni:
            params.extend([("sni", self.sni), ("host", self.sni)])
        if self.path:
            params.append(("path", self.path))
        if self.flow:
            params.append(("flow", self.flow))

        query = "&".join(
            f"{key}={quote(str(value), safe='/@:~+_-')}"
            for key, value in params
            if value not in (None, "")
        )
        label = quote(self.label, safe='@:+-_= ')
        return f"vless://{self.uuid}@{self.server}:{self.port}?{query}#{label}"

    def to_nekobox_profile(self) -> Dict[str, Any]:
        headers: Dict[str, Any] = {}
        if self.sni:
            headers["Host"] = self.sni
        transport_payload: Dict[str, Any] = {"type": self.transport}
        if self.transport == "ws":
            transport_payload["path"] = self.path or "/"
            if headers:
                transport_payload["headers"] = headers
        else:
            if self.path:
                transport_payload["path"] = self.path
            if headers:
                transport_payload["headers"] = headers

        tls_enabled = self.security.lower() in {"tls", "reality"}
        profile = {
            "remark": self.label,
            "type": "VLESS",
            "address": self.server,
            "port": self.port,
            "id": self.uuid,
            "encryption": "none",
            "flow": self.flow or "",
            "udp": True,
            "transport": transport_payload,
            "tls": {
                "enabled": tls_enabled,
                "alpn": _VLESS_ALPN,
                "serverName": self.sni or self.server,
                "insecure": False,
            },
        }
        return profile


def _normalize_optional(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).strip()
    return text or None


def _normalize_path(value: Optional[Any], transport: str) -> Optional[str]:
    normalized = _normalize_optional(value)
    if not normalized:
        return None
    if transport == "ws" and not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized


def build_profile_for_user(user: User) -> VlessProfileData:
    try:
        label = _VLESS_LABEL_TEMPLATE.format(
            tg_id=user.tg_id,
            username=user.username or user.tg_id,
            full_name=user.full_name or user.tg_id,
        )
    except KeyError as exc:
        logger.warning("Invalid VLESS_LABEL_TEMPLATE: missing key %s", exc)
        label = f"FaceVPN {user.tg_id}"

    uuid_value = str(uuid5(_UUID_NAMESPACE, str(user.tg_id)))
    return VlessProfileData(
        user_id=user.id,
        uuid=uuid_value,
        label=label,
        server=_VLESS_HOST,
        port=_VLESS_PORT,
        transport=_VLESS_TRANSPORT,
        security=_VLESS_SECURITY,
        flow=_normalize_optional(_VLESS_FLOW),
        sni=_normalize_optional(_VLESS_SNI),
        path=_normalize_path(_VLESS_PATH, transport=_VLESS_TRANSPORT),
    )


class VlessProvisioner:
    def __init__(self) -> None:
        self._url = _VLESS_PROVISION_URL
        self._token = _VLESS_PROVISION_TOKEN
        self._timeout = ClientTimeout(total=_VLESS_PROVISION_TIMEOUT)

    @property
    def configured(self) -> bool:
        return bool(self._url)

    async def provision(self, user: User, profile: VlessProfileData, *, force: bool = False) -> ProvisionResult:
        if not self._url:
            logger.warning("VLESS provisioning endpoint is not configured.")
            return ProvisionResult(remote_id=None, overrides={}, raw=None, error="Provisioning service is not configured.")

        payload = {
            "telegram_id": user.tg_id,
            "username": user.username,
            "full_name": user.full_name,
            "force": force,
            "profile": profile.to_payload(),
        }

        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            async with ClientSession(timeout=self._timeout) as session:
                async with session.post(self._url, json=payload, headers=headers) as response:
                    text = await response.text()
                    if response.status >= 400:
                        logger.error("Provisioning request failed: %s %s", response.status, text)
                        return ProvisionResult(
                            remote_id=None,
                            overrides={},
                            raw=None,
                            error=f"HTTP {response.status}: {text}",
                        )
                    data = None
                    if text.strip():
                        try:
                            data = json.loads(text)
                        except json.JSONDecodeError:
                            logger.error("Provisioning returned invalid JSON: %s", text)
                            return ProvisionResult(
                                remote_id=None,
                                overrides={},
                                raw=None,
                                error="Provisioning service returned invalid JSON.",
                            )
        except ClientError as exc:
            logger.error("Provisioning request error: %s", exc)
            return ProvisionResult(remote_id=None, overrides={}, raw=None, error=str(exc))

        if data is None:
            return ProvisionResult(remote_id=None, overrides={}, raw=None, error=None)

        error = _extract_error(data)
        overrides = _extract_profile_overrides(data)
        remote_id = _extract_remote_id(data)
        return ProvisionResult(remote_id=remote_id, overrides=overrides, raw=data, error=error)


def _extract_error(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return "Unexpected provisioning response structure."

    if payload.get("ok") is False or payload.get("success") is False:
        return str(payload.get("error") or payload.get("message") or payload.get("detail") or "Provisioning failed.")

    status = payload.get("status")
    if isinstance(status, str) and status.lower() in {"error", "failed", "failure"}:
        return str(payload.get("message") or payload.get("error") or "Provisioning failed.")

    if "error" in payload and payload.get("ok") is None and payload.get("success") is None:
        error_value = payload.get("error")
        if error_value:
            return str(error_value)

    return None


def _extract_profile_overrides(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    for key in ("profile", "result", "data", "payload"):
        value = payload.get(key)
        if isinstance(value, dict):
            if "profile" in value and isinstance(value["profile"], dict):
                return value["profile"]
            return value
    return {}


def _extract_remote_id(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None

    keys = {"remote_id", "profile_id", "id"}
    stack = [payload]
    seen: set[int] = set()

    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            marker = id(item)
            if marker in seen:
                continue
            seen.add(marker)
            for key, value in item.items():
                if key in keys and value not in (None, ""):
                    return str(value)
                if isinstance(value, (dict, list, tuple)):
                    stack.append(value)
        elif isinstance(item, (list, tuple)):
            stack.extend(item)

    return None


async def ensure_vless_profile(user: User, *, force: bool = False) -> Tuple[VlessProfileData, bool, bool, Optional[str]]:
    existing = await crud.get_vpn_profile_by_user_id(user.id)
    created = False

    if existing:
        profile = VlessProfileData.from_model(existing)
    else:
        profile = build_profile_for_user(user)
        created = True

    should_sync = force or existing is None or existing.remote_id is None or existing.last_sync_error
    provision_result: Optional[ProvisionResult] = None

    if should_sync:
        provisioner = VlessProvisioner()
        provision_result = await provisioner.provision(user, profile, force=force)
        if provision_result.overrides:
            profile = profile.apply_overrides(provision_result.overrides)

        synced = provision_result.error is None
        remote_id = provision_result.remote_id or (existing.remote_id if existing else None)
        last_synced_at = datetime.utcnow() if synced else (existing.last_synced_at if existing else None)

        saved = await crud.save_vpn_profile(
            user_id=user.id,
            uuid=profile.uuid,
            label=profile.label,
            server=profile.server,
            port=profile.port,
            transport=profile.transport,
            security=profile.security,
            flow=profile.flow,
            sni=profile.sni,
            path=profile.path,
            remote_id=remote_id,
            last_synced_at=last_synced_at,
            last_sync_error=provision_result.error,
        )
        profile = VlessProfileData.from_model(saved)
        existing = saved
    else:
        provision_result = ProvisionResult(
            remote_id=existing.remote_id,
            overrides={},
            raw=None,
            error=existing.last_sync_error,
        )
        synced = existing.last_sync_error is None

    return profile, created, synced, provision_result.error
