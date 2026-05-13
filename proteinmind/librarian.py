from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Iterable, List, Protocol
import re


class ConstraintCategory(str, Enum):
    ACTIVE_SITE_CONTACTS = "active_site_contacts"
    GEOMETRY = "geometry"
    LIGAND_BINDING = "ligand_binding"
    BENEFICIAL_MUTATIONS = "beneficial_mutations"
    DELETERIOUS_MUTATIONS = "deleterious_mutations"
    CODON_CONTEXT = "codon_context"
    VALIDATION = "validation"


@dataclass(frozen=True)
class Paper:
    id: str
    title: str
    abstract: str
    source: str
    url: str | None = None


@dataclass(frozen=True)
class ConstraintItem:
    category: ConstraintCategory
    statement: str
    paper_id: str
    confidence: float
    residues: List[str] = field(default_factory=list)
    mutations: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ConstraintObject:
    query: str
    generated_at: str
    papers_analyzed: int
    constraints: Dict[str, List[Dict[str, object]]]
    conflicts: List[str]


class LiteratureProvider(Protocol):
    def search(self, query: str, max_results: int) -> List[Paper]:
        """Return papers matching the query."""


class LibrarianAgent:
    DEFAULT_CONFIDENCE = 0.7
    GEOMETRY_WITH_MEASUREMENT_CONFIDENCE = 0.85
    MUTATION_CONFIDENCE = 0.8

    _MUTATION_PATTERN = re.compile(r"\b([A-Z]\d+[A-Z])\b")
    _RESIDUE_PATTERN = re.compile(r"\b([A-Z][a-z]{2}\s?\d+|[A-Z]\d+(?![A-Z]))\b")
    _GEOMETRY_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s?(?:Å|A)\b")

    _CATEGORY_KEYWORDS: Dict[ConstraintCategory, Iterable[str]] = {
        ConstraintCategory.ACTIVE_SITE_CONTACTS: (
            "active site",
            "catalytic",
            "residue contact",
            "contact residue",
            "catalytic triad",
        ),
        ConstraintCategory.GEOMETRY: (
            "distance",
            "geometry",
            "angle",
            "spacing",
            "pocket volume",
        ),
        ConstraintCategory.LIGAND_BINDING: (
            "ligand",
            "substrate",
            "binding pocket",
            "affinity",
            "cofactor",
        ),
        ConstraintCategory.CODON_CONTEXT: (
            "codon",
            "gc content",
            "host strain",
            "expression host",
            "organism",
        ),
        ConstraintCategory.VALIDATION: (
            "validated",
            "assay",
            "kinetic",
            "kcat",
            "km",
            "in vivo",
            "in vitro",
            "crystal structure",
            "cryo-em",
        ),
    }

    _BENEFICIAL_KEYWORDS = (
        "improve",
        "improved",
        "increase",
        "increased",
        "enhance",
        "enhanced",
        "gain-of-function",
    )
    _DELETERIOUS_KEYWORDS = (
        "decrease",
        "decreased",
        "abolish",
        "abolished",
        "impair",
        "impaired",
        "loss-of-function",
        "inactive",
    )

    def __init__(self, providers: List[LiteratureProvider]):
        if not providers:
            raise ValueError("LibrarianAgent requires at least one literature provider")
        self.providers = providers

    def build_constraint_object(self, query: str, max_results: int = 10) -> ConstraintObject:
        papers = self._dedupe_papers(self._search_all(query=query, max_results=max_results))
        extracted = self._extract_constraints(papers)
        conflicts = self._detect_conflicts(extracted)

        grouped: Dict[str, List[Dict[str, object]]] = {
            category.value: [] for category in ConstraintCategory
        }
        for item in extracted:
            grouped[item.category.value].append(self._serialize_item(item))

        return ConstraintObject(
            query=query,
            generated_at=datetime.now(timezone.utc).isoformat(),
            papers_analyzed=len(papers),
            constraints=grouped,
            conflicts=conflicts,
        )

    def _search_all(self, query: str, max_results: int) -> List[Paper]:
        papers: List[Paper] = []
        for provider in self.providers:
            papers.extend(provider.search(query=query, max_results=max_results))
        return papers

    @staticmethod
    def _dedupe_papers(papers: List[Paper]) -> List[Paper]:
        unique: Dict[str, Paper] = {}
        for paper in papers:
            unique.setdefault(paper.id, paper)
        return list(unique.values())

    def _extract_constraints(self, papers: List[Paper]) -> List[ConstraintItem]:
        items: List[ConstraintItem] = []
        for paper in papers:
            for sentence in self._sentences(self._combine_title_and_abstract(paper.title, paper.abstract)):
                lower = sentence.lower()
                residues = self._RESIDUE_PATTERN.findall(sentence)
                mutations = self._MUTATION_PATTERN.findall(sentence)

                for category, keywords in self._CATEGORY_KEYWORDS.items():
                    if any(keyword in lower for keyword in keywords):
                        confidence = self.DEFAULT_CONFIDENCE
                        if category == ConstraintCategory.GEOMETRY and self._GEOMETRY_PATTERN.search(sentence):
                            confidence = self.GEOMETRY_WITH_MEASUREMENT_CONFIDENCE
                        items.append(
                            ConstraintItem(
                                category=category,
                                statement=sentence,
                                paper_id=paper.id,
                                confidence=confidence,
                                residues=residues,
                                mutations=mutations,
                            )
                        )

                if mutations:
                    if any(keyword in lower for keyword in self._BENEFICIAL_KEYWORDS):
                        items.append(
                            ConstraintItem(
                                category=ConstraintCategory.BENEFICIAL_MUTATIONS,
                                statement=sentence,
                                paper_id=paper.id,
                                confidence=self.MUTATION_CONFIDENCE,
                                residues=residues,
                                mutations=mutations,
                            )
                        )
                    if any(keyword in lower for keyword in self._DELETERIOUS_KEYWORDS):
                        items.append(
                            ConstraintItem(
                                category=ConstraintCategory.DELETERIOUS_MUTATIONS,
                                statement=sentence,
                                paper_id=paper.id,
                                confidence=self.MUTATION_CONFIDENCE,
                                residues=residues,
                                mutations=mutations,
                            )
                        )
        return items

    @staticmethod
    def _combine_title_and_abstract(title: str, abstract: str) -> str:
        title_clean = title.strip()
        abstract_clean = abstract.strip()
        if not title_clean:
            return abstract_clean
        if not abstract_clean:
            return title_clean
        if title_clean.endswith((".", "!", "?")):
            return f"{title_clean} {abstract_clean}"
        return f"{title_clean}. {abstract_clean}"

    @staticmethod
    def _serialize_item(item: ConstraintItem) -> Dict[str, object]:
        return {
            "category": item.category.value,
            "statement": item.statement,
            "paper_id": item.paper_id,
            "confidence": item.confidence,
            "residues": item.residues,
            "mutations": item.mutations,
        }

    @staticmethod
    def _sentences(text: str) -> List[str]:
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [part.strip() for part in parts if part.strip()]

    @staticmethod
    def _detect_conflicts(items: List[ConstraintItem]) -> List[str]:
        beneficial = set()
        deleterious = set()

        for item in items:
            if item.category == ConstraintCategory.BENEFICIAL_MUTATIONS:
                beneficial.update(item.mutations)
            elif item.category == ConstraintCategory.DELETERIOUS_MUTATIONS:
                deleterious.update(item.mutations)

        conflicts = sorted(beneficial.intersection(deleterious))
        return [
            f"Mutation {mutation} is reported as both beneficial and deleterious across sources"
            for mutation in conflicts
        ]
