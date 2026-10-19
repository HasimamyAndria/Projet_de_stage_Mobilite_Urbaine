# -*- coding: utf-8 -*-
"""Applique une migration SQL une seule fois.

La version et l'empreinte du fichier sont enregistrées dans schema_migrations,
dans la même transaction que le script. Une seconde exécution de la même
empreinte ne rejoue pas le SQL. Une empreinte différente est refusée :
il faut une nouvelle version, pas une réécriture silencieuse.

Usage, depuis backend/ :

    venv\\Scripts\\python.exe scripts\\apply_sql_migration.py 30_mobility_contract
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
SQL_DIR = Path(__file__).resolve().parent / "sql"

MIGRATIONS = {
    "30_mobility_contract": {
        "file": "30_mobility_contract.sql",
        "description": (
            "Contrat des déplacements individuels : datasets, places, persons, "
            "purposes, modes, trips, surveys, import_batches, import_rows"
        ),
    }
}

ADVISORY_LOCK_KEY = 804302026


def load_env() -> None:
    """backend/.env prime sur le .env Compose de la racine."""
    load_dotenv(ROOT / ".env")
    load_dotenv(REPO / ".env")


def connection_target() -> dict[str, str]:
    import os

    host = os.getenv("DB_HOST") or ""
    if host == "db" and not Path("/.dockerenv").exists():
        raise SystemExit(
            "DB_HOST=db est le nom du service Compose. Le démon Docker n'est pas "
            "utilisé par ce script sur l'hôte. backend/.env doit indiquer "
            "l'instance locale qui contient déjà les données (DB_HOST=localhost)."
        )
    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise SystemExit("Variables manquantes : " + ", ".join(missing))
    return {
        "host": os.environ["DB_HOST"],
        "port": os.environ["DB_PORT"],
        "name": os.environ["DB_NAME"],
        "user": os.environ["DB_USER"],
    }


def make_engine() -> Engine:
    import os

    target = connection_target()
    url = (
        f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{target['host']}:{target['port']}/{target['name']}"
    )
    return create_engine(url, connect_args={"client_encoding": "utf8"})


def file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_sql(script: str) -> list[str]:
    """Découpe le script sur les points-virgules hors chaînes, commentaires et dollars."""
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    length = len(script)
    dollar_tag: str | None = None

    while i < length:
        if dollar_tag is not None:
            if script.startswith(dollar_tag, i):
                buf.append(dollar_tag)
                i += len(dollar_tag)
                dollar_tag = None
                continue
            buf.append(script[i])
            i += 1
            continue

        if script.startswith("--", i):
            end = script.find("\n", i)
            i = length if end == -1 else end + 1
            buf.append("\n")
            continue

        if script.startswith("/*", i):
            end = script.find("*/", i + 2)
            if end == -1:
                raise ValueError("Commentaire bloc non terminé")
            i = end + 2
            continue

        if script[i] == "'":
            buf.append(script[i])
            i += 1
            while i < length:
                buf.append(script[i])
                if script[i] == "'":
                    if i + 1 < length and script[i + 1] == "'":
                        buf.append(script[i + 1])
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue

        if script[i] == "$":
            end = i + 1
            while end < length and (script[end].isalnum() or script[end] == "_"):
                end += 1
            if end < length and script[end] == "$":
                dollar_tag = script[i : end + 1]
                buf.append(dollar_tag)
                i = end + 1
                continue

        if script[i] == ";":
            statement = "".join(buf).strip()
            if statement:
                statements.append(statement)
            buf = []
            i += 1
            continue

        buf.append(script[i])
        i += 1

    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def execute_sql_script(connection: Connection, script: str) -> int:
    statements = split_sql(script)
    for statement in statements:
        try:
            connection.execute(text(statement))
        except Exception as exc:
            first = statement.splitlines()[0][:120]
            raise RuntimeError(f"Échec SQL près de « {first} » : {exc}") from exc
    return len(statements)


def _recorded_checksum(connection: Connection, version: str) -> str | None:
    present = connection.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'schema_migrations'
            """
        )
    ).scalar()
    if not present:
        return None
    row = connection.execute(
        text("SELECT checksum FROM schema_migrations WHERE version = :version"),
        {"version": version},
    ).first()
    return None if row is None else str(row[0])


def apply_migration(version: str, engine: Engine | None = None) -> dict[str, str | int]:
    if version not in MIGRATIONS:
        known = ", ".join(sorted(MIGRATIONS))
        raise SystemExit(f"Migration inconnue : {version}. Connues : {known}")

    spec = MIGRATIONS[version]
    path = SQL_DIR / str(spec["file"])
    if not path.is_file():
        raise SystemExit(f"Fichier absent : {path}")

    checksum = file_checksum(path)
    own_engine = engine is None
    engine = engine or make_engine()
    script = path.read_text(encoding="utf-8")

    try:
        with engine.begin() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(CAST(:key AS bigint))"),
                {"key": ADVISORY_LOCK_KEY},
            )
            recorded = _recorded_checksum(connection, version)
            if recorded == checksum:
                return {
                    "status": "skipped",
                    "version": version,
                    "checksum": checksum,
                    "statements": 0,
                }
            if recorded is not None:
                raise SystemExit(
                    f"La version {version} est déjà appliquée avec une autre empreinte. "
                    "Créez une migration suivante au lieu de modifier celle-ci."
                )

            statements = execute_sql_script(connection, script)
            connection.execute(
                text(
                    """
                    INSERT INTO schema_migrations (version, description, checksum)
                    VALUES (:version, :description, :checksum)
                    """
                ),
                {
                    "version": version,
                    "description": spec["description"],
                    "checksum": checksum,
                },
            )
            return {
                "status": "applied",
                "version": version,
                "checksum": checksum,
                "statements": statements,
            }
    finally:
        if own_engine:
            engine.dispose()


def main(argv: list[str]) -> int:
    load_env()
    if len(argv) != 2:
        print("Usage: python scripts/apply_sql_migration.py <version>", file=sys.stderr)
        return 1
    target = connection_target()
    print(
        f"target host={target['host']} port={target['port']} "
        f"db={target['name']} user={target['user']}"
    )
    result = apply_migration(argv[1])
    print(
        f"status={result['status']} version={result['version']} "
        f"statements={result['statements']} checksum={result['checksum']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except SystemExit:
        raise
    except Exception as exc:
        print(f"ERREUR {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
