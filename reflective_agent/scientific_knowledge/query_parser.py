from __future__ import annotations

import re

from reflective_agent.models import ScientificQuery


class QueryParser:
    """Heuristic parser that extracts property, entity, conditions, and source hints."""

    PROPERTY_PATTERNS = [
        ("boiling_point", [r"boiling point", r"沸点"]),
        ("melting_point", [r"melting point", r"熔点"]),
        ("molar_mass", [r"molar mass", r"molecular weight", r"分子量", r"摩尔质量"]),
        ("formula", [r"\bformula\b", r"化学式"]),
        ("canonical_smiles", [r"smiles"]),
        ("band_gap", [r"band gap", r"带隙"]),
        ("formation_energy_per_atom", [r"formation energy", r"形成能"]),
    ]
    CONSTANT_PATTERNS = [
        r"avogadro constant",
        r"avogadro number",
        r"boltzmann constant",
        r"planck constant",
        r"gas constant",
        r"阿伏伽德罗常数",
        r"玻尔兹曼常数",
        r"普朗克常数",
        r"气体常数",
    ]

    def parse(self, current_input: str, task_goal: str) -> ScientificQuery:
        raw_text = f"{current_input} {task_goal}".strip()
        normalized = raw_text.lower()
        property_name = self._detect_property(normalized)
        query_type = "constant" if self._detect_constant(normalized) else "entity_property"
        if property_name == "general" and query_type == "constant":
            property_name = "constant_value"
        requested_unit = self._detect_requested_unit(normalized)
        condition = self._detect_condition(normalized)
        entity_candidates = self._detect_entity_candidates(current_input)
        source_hints = self._detect_source_hints(normalized)
        return ScientificQuery(
            raw_text=current_input,
            normalized_text=normalized,
            query_type=query_type,
            entity_candidates=entity_candidates,
            property_name=property_name,
            requested_unit=requested_unit,
            condition=condition,
            source_hints=source_hints,
        )

    def _detect_property(self, normalized_text: str) -> str:
        for property_name, patterns in self.PROPERTY_PATTERNS:
            if any(re.search(pattern, normalized_text) for pattern in patterns):
                return property_name
        return "general"

    def _detect_constant(self, normalized_text: str) -> bool:
        return any(re.search(pattern, normalized_text) for pattern in self.CONSTANT_PATTERNS)

    def _detect_requested_unit(self, normalized_text: str) -> str | None:
        if re.search(r"\b(c|degc|celsius)\b", normalized_text) or "摄氏" in normalized_text:
            return "C"
        if re.search(r"\b(k|kelvin)\b", normalized_text):
            return "K"
        if "kg/mol" in normalized_text:
            return "kg/mol"
        if "g/mol" in normalized_text:
            return "g/mol"
        return None

    def _detect_condition(self, normalized_text: str) -> dict[str, float]:
        condition: dict[str, float] = {}
        pressure_match = re.search(r"(\d+(?:\.\d+)?)\s*atm", normalized_text)
        if pressure_match:
            condition["pressure_atm"] = float(pressure_match.group(1))
        elif "1 atm" in normalized_text or "standard pressure" in normalized_text or "标准大气压" in normalized_text:
            condition["pressure_atm"] = 1.0
        return condition

    def _detect_entity_candidates(self, current_input: str) -> list[str]:
        quoted = re.findall(r'"([^"]+)"', current_input)
        tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9]{0,15}\b", current_input)
        candidates = quoted + tokens
        stopwords = {
            "what", "which", "show", "find", "lookup", "get", "is", "the", "of", "at", "for", "please",
            "查询", "获取", "请", "给出", "是多少"
        }
        return [item for item in candidates if item.lower() not in stopwords]

    def _detect_source_hints(self, normalized_text: str) -> list[str]:
        hints: list[str] = []
        if "nist" in normalized_text:
            hints.append("nist_webbook")
        if "materials project" in normalized_text:
            hints.append("materials_project")
        if "pubchem" in normalized_text or "chebi" in normalized_text:
            hints.append("pubchem_chebi")
        return hints
