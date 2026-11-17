from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from sidebrain_back.rag.rag_tokenizer import RagTokenizer, Tokenizer

_FENCE_START = re.compile(r"^\s*(```+|~~~+)(.*)$")
_SIMHASH_TOKEN = re.compile(r"[\w$]+", re.UNICODE)


@dataclass(frozen=True)
class RagSection:
    section_path: str
    text: str


@dataclass
class RagChunk:
    chunk_id: str
    content_hash: str
    text: str
    body_text: str
    section_path: str
    language: str
    content_type: str
    code_language: str | None
    code_hash: str | None
    duplicate_fingerprint: str
    duplicate_group_id: str | None = None
    attributions: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class _Block:
    text: str
    is_code: bool
    code_language: str | None = None


class RagChunker:
    def __init__(
        self,
        tokenizer: Tokenizer | None = None,
        target_tokens: int = 500,
        overlap_ratio: float = 0.12,
        chunker_version: str = "1",
    ):
        if target_tokens < 1:
            raise ValueError("target_tokens must be positive")
        if not 0 <= overlap_ratio < 0.5:
            raise ValueError("overlap_ratio must be between 0 and 0.5")
        self.tokenizer = tokenizer or RagTokenizer()
        self.target_tokens = target_tokens
        self.overlap_ratio = overlap_ratio
        self.chunker_version = chunker_version

    def chunk_document(
        self,
        *,
        title: str,
        sections: list[RagSection],
        attribution: dict[str, Any],
    ) -> list[RagChunk]:
        chunks: list[RagChunk] = []
        for section in sections:
            prefix = f"Document: {title}\nSection: {section.section_path}\n\n"
            blocks = self._prepare_blocks(section.text)
            chunks.extend(
                self._pack_section(
                    title=title,
                    section=section,
                    prefix=prefix,
                    blocks=blocks,
                    attribution=attribution,
                )
            )
        return chunks

    def _prepare_blocks(self, content: str) -> list[_Block]:
        blocks: list[_Block] = []
        plain_lines: list[str] = []
        lines = content.splitlines(keepends=True)
        index = 0
        while index < len(lines):
            match = _FENCE_START.match(lines[index].rstrip("\r\n"))
            if match is None:
                plain_lines.append(lines[index])
                index += 1
                continue

            if plain_lines:
                blocks.extend(self._split_prose("".join(plain_lines)))
                plain_lines = []

            fence = match.group(1).strip()
            info = match.group(2).strip()
            code_lines = [lines[index]]
            index += 1
            while index < len(lines):
                line = lines[index]
                code_lines.append(line)
                index += 1
                if line.strip().startswith(fence):
                    break
            code_language = info.split(maxsplit=1)[0] if info else None
            blocks.append(
                _Block(
                    text="".join(code_lines).rstrip("\r\n"),
                    is_code=True,
                    code_language=code_language,
                )
            )

        if plain_lines:
            blocks.extend(self._split_prose("".join(plain_lines)))
        return [block for block in blocks if block.text.strip()]

    def _split_prose(self, text: str) -> list[_Block]:
        result: list[_Block] = []
        for paragraph in re.split(r"\n\s*\n", text):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            tokens = self.tokenizer.encode(paragraph)
            if len(tokens) <= self.target_tokens:
                result.append(_Block(paragraph, is_code=False))
                continue
            for start in range(0, len(tokens), self.target_tokens):
                piece = self.tokenizer.decode(
                    tokens[start : start + self.target_tokens]
                )
                if piece.strip():
                    result.append(_Block(piece.strip(), is_code=False))
        return result

    def _pack_section(
        self,
        *,
        title: str,
        section: RagSection,
        prefix: str,
        blocks: list[_Block],
        attribution: dict[str, Any],
    ) -> list[RagChunk]:
        chunks: list[RagChunk] = []
        current: list[_Block] = []

        def flush(*, keep_overlap: bool = True) -> None:
            nonlocal current
            if not current:
                return
            chunks.append(
                self._make_chunk(
                    title=title,
                    section=section,
                    prefix=prefix,
                    blocks=current,
                    attribution=attribution,
                )
            )
            old_blocks = current
            current = self._overlap_tail(old_blocks) if keep_overlap else []

        for block in blocks:
            combined = [*current, block]
            combined_text = "\n\n".join(item.text for item in combined)
            combined_size = self.tokenizer.count(prefix + combined_text)

            if current and combined_size > self.target_tokens:
                # Preserve the explanation with the code block even when that
                # makes a chunk exceed the target. The block itself is atomic.
                if block.is_code and not any(item.is_code for item in current):
                    current.append(block)
                    flush(keep_overlap=False)
                    continue
                flush()
                combined = [*current, block]
                combined_text = "\n\n".join(item.text for item in combined)
                combined_size = self.tokenizer.count(prefix + combined_text)

            current.append(block)
            if block.is_code and combined_size > self.target_tokens:
                flush(keep_overlap=False)

        flush(keep_overlap=False)
        return chunks

    def _overlap_tail(self, blocks: list[_Block]) -> list[_Block]:
        target = int(self.target_tokens * self.overlap_ratio)
        if target <= 0:
            return []
        result: list[_Block] = []
        size = 0
        for block in reversed(blocks):
            if block.is_code:
                continue
            block_size = self.tokenizer.count(block.text)
            if size + block_size > target:
                break
            result.insert(0, block)
            size += block_size
        return result

    def _make_chunk(
        self,
        *,
        title: str,
        section: RagSection,
        prefix: str,
        blocks: list[_Block],
        attribution: dict[str, Any],
    ) -> RagChunk:
        body_text = "\n\n".join(block.text for block in blocks).strip()
        content_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()
        chunk_id = hashlib.sha256(
            f"{self.chunker_version}:{content_hash}".encode()
        ).hexdigest()
        code_blocks = [block for block in blocks if block.is_code]
        code_content = "\n".join(block.text for block in code_blocks)
        code_hash = (
            hashlib.sha256(code_content.encode("utf-8")).hexdigest()
            if code_blocks
            else None
        )
        attributions = dict(attribution)
        attributions["title"] = title
        attributions["section_path"] = section.section_path
        return RagChunk(
            chunk_id=chunk_id,
            content_hash=content_hash,
            text=f"{prefix}{body_text}",
            body_text=body_text,
            section_path=section.section_path,
            language=str(attributions["language"]),
            content_type=("code_example" if code_blocks else "concept"),
            code_language=next(
                (
                    block.code_language
                    for block in code_blocks
                    if block.code_language
                ),
                None,
            ),
            code_hash=code_hash,
            duplicate_fingerprint=simhash(body_text),
            attributions=[attributions],
        )


def simhash(text: str, bits: int = 64) -> str:
    if bits < 1 or bits > 128:
        raise ValueError("bits must be between 1 and 128")
    vector = [0] * bits
    tokens = _SIMHASH_TOKEN.findall(text.casefold())
    for token in tokens:
        digest = hashlib.blake2b(
            token.encode("utf-8"), digest_size=16
        ).digest()
        value = int.from_bytes(digest, byteorder="big") >> (128 - bits)
        for position in range(bits):
            vector[position] += 1 if value & (1 << position) else -1
    fingerprint = sum(
        1 << position for position, weight in enumerate(vector) if weight >= 0
    )
    return f"{fingerprint:0{(bits + 3) // 4}x}"


def deduplicate_exact(chunks: list[RagChunk]) -> tuple[list[RagChunk], int]:
    by_hash: dict[str, RagChunk] = {}
    removed = 0
    for chunk in chunks:
        existing = by_hash.get(chunk.content_hash)
        if existing is None:
            by_hash[chunk.content_hash] = chunk
            continue
        existing_keys = {
            (
                item.get("doc_id"),
                item.get("source_url"),
                item.get("section_path"),
                item.get("license"),
            )
            for item in existing.attributions
        }
        for attribution in chunk.attributions:
            key = (
                attribution.get("doc_id"),
                attribution.get("source_url"),
                attribution.get("section_path"),
                attribution.get("license"),
            )
            if key not in existing_keys:
                existing.attributions.append(attribution)
                existing_keys.add(key)
        removed += 1
    return list(by_hash.values()), removed


def approximate_duplicate_groups(
    chunks: list[RagChunk], max_hamming_distance: int
) -> list[list[RagChunk]]:
    groups: list[list[RagChunk]] = []
    assigned: set[str] = set()
    for index, chunk in enumerate(chunks):
        if chunk.chunk_id in assigned:
            continue
        group = [chunk]
        fingerprint = int(chunk.duplicate_fingerprint, 16)
        for candidate in chunks[index + 1 :]:
            if candidate.chunk_id in assigned:
                continue
            if candidate.language != chunk.language:
                continue
            if candidate.code_hash != chunk.code_hash:
                continue
            distance = fingerprint ^ int(candidate.duplicate_fingerprint, 16)
            if distance.bit_count() <= max_hamming_distance:
                group.append(candidate)
                assigned.add(candidate.chunk_id)
        if len(group) > 1:
            assigned.add(chunk.chunk_id)
            groups.append(group)
    return groups
