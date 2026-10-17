"""Compare public analytics snapshots and update an already built Pages artifact."""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import time

from scripts.comment_refresh import published_json
from scripts.fetch_analytics import AnalyticsError, validate_snapshot
from scripts.fetch_comments import FeedError

ANALYTICS_PATH = "data/analytics.json"
MAX_SNAPSHOT_BYTES = 1024 * 1024
MAX_SITE_BYTES = 900_000_000


def read_snapshot(path: Path) -> dict:
    with path.open("rb") as handle:
        payload = handle.read(MAX_SNAPSHOT_BYTES + 1)
    if len(payload) > MAX_SNAPSHOT_BYTES:
        raise AnalyticsError("Analytics snapshot exceeds 1 MiB")
    try:
        snapshot = json.loads(payload)
    except (ValueError, UnicodeError) as error:
        raise AnalyticsError("Invalid analytics JSON") from error
    return validate_snapshot(snapshot)


def changed(fresh: dict, published: dict | None) -> bool:
    validate_snapshot(fresh)
    if published is None:
        return True
    validate_snapshot(published)
    substantive = lambda value: {key: item for key, item in value.items() if key != "updated_at"}
    return substantive(fresh) != substantive(published)


def _payload(snapshot: dict) -> bytes:
    validate_snapshot(snapshot)
    payload = (json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    if len(payload) > MAX_SNAPSHOT_BYTES:
        raise AnalyticsError("Analytics snapshot exceeds 1 MiB")
    return payload


def patch_dist(dist: Path, snapshot: dict) -> None:
    payload = _payload(snapshot)
    if dist.is_symlink() or not dist.is_dir() or not (dist / "index.html").is_file():
        raise AnalyticsError("Missing or unsafe built site directory")
    destination = dist / ANALYTICS_PATH
    total_bytes = len(payload)
    for path in dist.rglob("*"):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise AnalyticsError("Built site contains a link or unsupported file type")
        if path.is_file() and path != destination:
            total_bytes += path.stat().st_size
    if total_bytes >= MAX_SITE_BYTES:
        raise AnalyticsError("Static site reached the 900 MB deployment guard")
    if destination.exists() and not destination.is_file():
        raise AnalyticsError("Analytics destination must be a regular file")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".analytics-", delete=False) as target:
            temporary = Path(target.name)
            target.write(payload)
            target.flush()
            os.fsync(target.fileno())
        temporary.chmod(0o644)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _archive_path(member: tarfile.TarInfo) -> str:
    name = member.name
    if name in {".", "./"} and member.isdir():
        return "."
    if name.startswith("./"):
        name = name[2:]
    if member.isdir() and name.endswith("/"):
        name = name[:-1]
    if (not name or "\\" in name or ":" in name
            or any(ord(char) < 32 or ord(char) == 127 for char in name)
            or any(not part or part.startswith(".") for part in name.split("/"))):
        raise AnalyticsError(f"Unsafe or noncanonical archive path: {member.name!r}")
    return name


def patch_archive(path: Path, snapshot: dict) -> None:
    """Stream regular files to a new tar, replacing only the analytics entry."""
    payload = _payload(snapshot)
    if path.is_symlink() or not path.is_file():
        raise AnalyticsError("Missing or unsafe Pages archive")
    temporary = None
    try:
        with path.open("rb") as source:
            source.seek(0, os.SEEK_END)
            source_size = source.tell()
            source.seek(0)
            if source_size % tarfile.BLOCKSIZE:
                raise AnalyticsError("Truncated Pages archive: incomplete tar block")
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".analytics-", suffix=".tar", delete=False) as target:
                temporary = Path(target.name)
                seen, files, ancestors_seen = set(), set(), set()
                total_bytes, data_end = len(payload), 0
                with tarfile.open(fileobj=source, mode="r:") as archive, tarfile.open(fileobj=target, mode="w", format=tarfile.PAX_FORMAT) as output:
                    for member in archive:
                        if (member.type not in {tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE}
                                or member.sparse is not None or member.linkname
                                or member.size < 0 or (member.isdir() and member.size != 0)):
                            raise AnalyticsError(f"Unsupported Pages archive entry: {member.name!r}")
                        name = _archive_path(member)
                        if name in seen:
                            raise AnalyticsError(f"Duplicate Pages archive path: {name}")
                        seen.add(name)
                        ancestors = {"/".join(name.split("/")[:index])
                                     for index in range(1, len(name.split("/")))}
                        if ancestors & files or (member.isfile() and name in ancestors_seen):
                            raise AnalyticsError(f"Conflicting file and directory paths: {name}")
                        ancestors_seen.update(ancestors)
                        data_end = member.offset_data + ((member.size + 511) // 512) * 512
                        if data_end > source_size:
                            raise AnalyticsError("Truncated Pages archive: incomplete file content")
                        if name == ANALYTICS_PATH:
                            if not member.isfile():
                                raise AnalyticsError("Analytics archive entry must be a regular file")
                            files.add(name)
                            continue
                        if member.isdir():
                            output.addfile(member)
                            continue
                        files.add(name)
                        total_bytes += member.size
                        if total_bytes >= MAX_SITE_BYTES:
                            raise AnalyticsError("Static site reached the 900 MB deployment guard")
                        with archive.extractfile(member) as content:
                            output.addfile(member, content)
                    if "index.html" not in files:
                        raise AnalyticsError("Pages archive is missing index.html")
                    # Reject truncated trailers or hidden entries after tarfile's first terminator.
                    source.seek(data_end)
                    if source_size - data_end < 2 * tarfile.BLOCKSIZE:
                        raise AnalyticsError("Truncated Pages archive: missing tar terminator")
                    while chunk := source.read(1024 * 1024):
                        if chunk.strip(b"\0"):
                            raise AnalyticsError("Unexpected data after the Pages archive tar terminator")
                    analytics = tarfile.TarInfo(ANALYTICS_PATH)
                    analytics.size = len(payload)
                    analytics.mode = 0o644
                    analytics.mtime = int(time.time())
                    output.addfile(analytics, io.BytesIO(payload))
                target.flush()
                os.fsync(target.fileno())
        temporary.chmod(0o644)
        os.replace(temporary, path)
    except (tarfile.TarError, EOFError, UnicodeError, ValueError) as error:
        raise AnalyticsError("Invalid or truncated Pages archive") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def patch(snapshot: dict, dist: Path, archive: Path) -> None:
    validate_snapshot(snapshot)
    if (dist / "index.html").exists():
        patch_dist(dist, snapshot)
    elif archive.exists():
        patch_archive(archive, snapshot)
    else:
        raise AnalyticsError("No built site or Pages archive is available for analytics refresh")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["compare", "patch"])
    parser.add_argument("--feed", type=Path, default=Path("public/data/analytics.json"))
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--archive", type=Path, default=Path(".artifacts/artifact.tar"))
    args = parser.parse_args(argv)
    fresh = read_snapshot(args.feed)
    if args.action == "patch":
        patch(fresh, args.dist, args.archive)
        print("Updated public analytics in the existing Pages artifact.")
        return
    site = os.environ.get("PUBLIC_SITE_URL", "")
    base = os.environ.get("PUBLIC_BASE_PATH", "/")
    needs_publish = changed(fresh, published_json(site, base, ANALYTICS_PATH))
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
            handle.write(f"changed={str(needs_publish).lower()}\n")
    print("Analytics changed; publication required." if needs_publish else "Analytics content unchanged.")


if __name__ == "__main__":
    try:
        main()
    except (AnalyticsError, FeedError, OSError, ValueError) as error:
        raise SystemExit(f"Analytics refresh failed: {error}") from error
