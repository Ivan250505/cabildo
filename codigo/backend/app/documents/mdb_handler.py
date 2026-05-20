"""
Detección y manejo de archivos MDB / Access (Sprint Drive D).

Por ahora NO se intenta convertir automáticamente — la conversión real
requiere binarios del SO (mdbtools en Linux/Mac, pyodbc + driver Access en
Windows) que no son portables a nuestro despliegue actual.

Lo que sí hacemos:
  - Detectar la extensión.
  - Devolver un mensaje claro al usuario explicando cómo proceder.

Cuando se decida soportar conversión, este módulo expondrá try_convert_to_csv()
y se enganchará en pipeline_v2.
"""
from __future__ import annotations

from pathlib import Path


MDB_EXTENSIONS = {".mdb", ".accdb"}


_MENSAJE_BLOQUEO = (
    "Este archivo es una base de datos Access (.mdb/.accdb), formato que "
    "actualmente no se procesa de manera automática. Para incluirlo en el "
    "estudio: ábrelo en Access o LibreOffice Base, exporta cada tabla relevante "
    "como Excel (.xlsx) o CSV, y vuelve a subir esos archivos al corpus."
)


def is_mdb(path: str | Path) -> bool:
    return Path(path).suffix.lower() in MDB_EXTENSIONS


def get_mdb_block_message() -> str:
    return _MENSAJE_BLOQUEO
