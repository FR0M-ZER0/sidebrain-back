from __future__ import annotations

from typing import Protocol

import tiktoken


class Tokenizer(Protocol):
    def count(self, text: str) -> int: ...

    def encode(self, text: str) -> list[int] | list[str]: ...

    def decode(self, tokens: list[int] | list[str]) -> str: ...


class RagTokenizer:
    def __init__(self, encoding_name: str = "cl100k_base"):
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.encoding_name = encoding_name

    def encode(self, text: str) -> list[int]:
        return self.encoding.encode(text, disallowed_special=())

    def decode(self, tokens: list[int] | list[str]) -> str:
        return self.encoding.decode(tokens)

    def count(self, text: str) -> int:
        return len(self.encode(text))
