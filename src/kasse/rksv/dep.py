"""Export des Datenerfassungsprotokolls (DEP7) laut RKSV."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ..db import einstellung


def dep_export(con: sqlite3.Connection) -> dict:
    gruppen: list[dict] = []
    aktuelle: dict | None = None
    for row in con.execute("SELECT zertifikat_serie, jws FROM belege ORDER BY belegnummer"):
        if aktuelle is None or aktuelle["_serie"] != row["zertifikat_serie"]:
            info = json.loads(einstellung(con, f"zertifikat:{row['zertifikat_serie']}") or "{}")
            aktuelle = {
                "_serie": row["zertifikat_serie"],
                "Signaturzertifikat": info.get("zertifikat", ""),
                "Zertifizierungsstellen": info.get("stellen", []),
                "Belege-kompakt": [],
            }
            gruppen.append(aktuelle)
        aktuelle["Belege-kompakt"].append(row["jws"])
    for g in gruppen:
        del g["_serie"]
    return {"Belege-Gruppe": gruppen}


def dep_export_datei(con: sqlite3.Connection, ziel: Path | str) -> Path:
    ziel = Path(ziel)
    ziel.write_text(json.dumps(dep_export(con), indent=2, ensure_ascii=False), encoding="utf-8")
    return ziel
