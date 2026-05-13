import unittest
import json
from typing import List

from proteinmind.librarian import LibrarianAgent, Paper


class FakeProvider:
    def __init__(self, papers: List[Paper]):
        self._papers = papers

    def search(self, query: str, max_results: int) -> List[Paper]:
        return self._papers[:max_results]


class LibrarianAgentTests(unittest.TestCase):
    def test_build_constraint_object_extracts_expected_categories(self):
        papers = [
            Paper(
                id="PMID:1",
                title="NanoLuc active site mapping",
                abstract=(
                    "The catalytic triad H57 D102 C176 defines active site geometry with 4.5 Å spacing. "
                    "Mutation H57A decreased activity in vitro assay. "
                    "Ligand affinity improved for mutant V120F in substrate binding pocket. "
                    "Codon usage in E. coli host strain increased expression."
                ),
                source="pubmed",
            )
        ]
        agent = LibrarianAgent(providers=[FakeProvider(papers)])

        result = agent.build_constraint_object("nanoluc")

        self.assertEqual(result.papers_analyzed, 1)
        self.assertTrue(result.constraints["active_site_contacts"])
        self.assertTrue(result.constraints["geometry"])
        self.assertTrue(result.constraints["ligand_binding"])
        self.assertTrue(result.constraints["deleterious_mutations"])
        self.assertTrue(result.constraints["beneficial_mutations"])
        self.assertTrue(result.constraints["codon_context"])
        self.assertTrue(result.constraints["validation"])
        all_residues = [
            residue
            for category_items in result.constraints.values()
            for item in category_items
            for residue in item["residues"]
        ]
        self.assertNotIn("H57A", all_residues)

    def test_conflict_detection_flags_opposite_mutation_labels(self):
        papers = [
            Paper(
                id="PMID:2",
                title="Paper A",
                abstract="Mutation R183K improved catalytic efficiency.",
                source="pubmed",
            ),
            Paper(
                id="PMID:3",
                title="Paper B",
                abstract="Mutation R183K abolished activity in vitro.",
                source="pubmed",
            ),
        ]
        agent = LibrarianAgent(providers=[FakeProvider(papers)])

        result = agent.build_constraint_object("cas12")

        self.assertEqual(len(result.conflicts), 1)
        self.assertIn("R183K", result.conflicts[0])

    def test_duplicate_papers_are_deduplicated_by_id(self):
        duplicated = Paper(
            id="PMID:4",
            title="Duplicate entry",
            abstract="Active site residues include S10 and H57.",
            source="pubmed",
        )
        agent = LibrarianAgent(providers=[FakeProvider([duplicated, duplicated])])

        result = agent.build_constraint_object("query")

        self.assertEqual(result.papers_analyzed, 1)

    def test_output_is_json_serializable(self):
        papers = [
            Paper(
                id="PMID:5",
                title="Geometry paper",
                abstract="The active site has 5.0 Å spacing.",
                source="pubmed",
            )
        ]
        agent = LibrarianAgent(providers=[FakeProvider(papers)])

        result = agent.build_constraint_object("geometry")

        serialized = json.dumps(result.constraints)
        self.assertIn("active_site_contacts", serialized)


if __name__ == "__main__":
    unittest.main()
