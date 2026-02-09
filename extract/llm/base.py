from typing import Protocol

class LLMRefiner(Protocol):
    def refine(self, result: dict, full_text: str) -> dict:
        ...
