"""YAML writer for from-maul suggestion drafts."""

from __future__ import annotations

from pathlib import Path

import yaml

from vigil.domain.errors import VigilError
from vigil.domain.suggestions import SuggestionDraft


class YamlSuggestionWriter:
    """Persist suggestion drafts as YAML for human review."""

    def write(self, path: Path, draft: SuggestionDraft) -> Path:
        """Write a draft policy suggestion document."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                yaml.safe_dump(draft.to_dict(), sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
        except OSError as error:
            msg = f"unable to write suggestion draft `{path}`: {error}"
            raise VigilError(msg) from error
        return path
