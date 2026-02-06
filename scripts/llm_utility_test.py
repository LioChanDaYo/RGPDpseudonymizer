#!/usr/bin/env python
"""LLM Utility Preservation Testing Script.

This script validates that pseudonymized documents maintain usefulness for LLM analysis
by comparing LLM responses on original vs pseudonymized versions of test documents.

Story 4.1: LLM Utility Preservation Testing
"""

import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class TestDocument:
    """Represents a test document pair (original + pseudonymized)."""

    name: str
    original_path: Path
    pseudonymized_path: Path
    doc_type: str  # "interview" or "business"


@dataclass
class LLMResponse:
    """Stores an LLM response with metadata."""

    document: str
    version: str  # "original" or "pseudonymized"
    prompt_type: str  # "themes", "relationships", "actions"
    prompt_text: str
    response_text: str
    model: str
    timestamp: str
    tokens_used: int


@dataclass
class EvaluationScore:
    """Stores evaluation scores for a response pair."""

    document: str
    prompt_type: str
    thematic_accuracy: int
    relationship_coherence: int
    factual_preservation: int
    overall_utility: int
    notes: str
    timestamp: str


# Standard prompts from Story 4.1 specification
PROMPTS = {
    "themes": "Summarize the main themes in this document. Provide a concise overview of the key topics discussed.",
    "relationships": "Identify key relationships between individuals mentioned in this document. Describe who interacts with whom and in what context.",
    "actions": "Extract action items and decisions made in this document. List specific tasks, deadlines, or resolutions if mentioned.",
}

# LLM-as-Judge prompt template
JUDGE_PROMPT_TEMPLATE = """You are evaluating the quality of LLM responses to pseudonymized documents compared to original documents.

ORIGINAL DOCUMENT RESPONSE:
{original_response}

PSEUDONYMIZED DOCUMENT RESPONSE:
{pseudonymized_response}

PROMPT USED: "{prompt_text}"

Score the pseudonymized response compared to the original on these dimensions (1-5 scale):
- Thematic Accuracy: Does it capture the same main themes? (5=identical, 1=completely different)
- Relationship Coherence: Are entity relationships correctly preserved? (5=perfect, 1=broken)
- Factual Preservation: Are facts/details accurately extracted? (5=all preserved, 1=major errors)
- Overall Utility: Would a researcher find this equally useful? (5=equivalent, 1=useless)

Respond in JSON format only, no other text:
{{"thematic_accuracy": X, "relationship_coherence": X, "factual_preservation": X, "overall_utility": X, "notes": "brief explanation if any score < 4"}}"""


class LLMUtilityTester:
    """Main class for LLM utility testing."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        rate_limit_delay: float = 1.0,
    ):
        """Initialize the tester.

        Args:
            api_key: Anthropic API key (defaults to env var)
            model: Model to use for testing
            rate_limit_delay: Seconds between API calls
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found")

        self.model = model
        self.rate_limit_delay = rate_limit_delay
        self.responses: list[LLMResponse] = []
        self.evaluations: list[EvaluationScore] = []

        # Initialize Anthropic client
        import anthropic

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def load_test_documents(self, base_path: Path) -> list[TestDocument]:
        """Load test document pairs from the test directory.

        Args:
            base_path: Base path to llm_test directory

        Returns:
            List of TestDocument objects
        """
        originals_dir = base_path / "originals"
        pseudo_dir = base_path / "pseudonymized"

        documents = []

        # Interview transcripts
        for i in [1, 3, 5, 7, 10]:
            name = f"interview_{i:02d}"
            orig = originals_dir / f"interview_{i:02d}.txt"
            pseudo = pseudo_dir / f"interview_{i:02d}_pseudonymized.txt"
            if orig.exists() and pseudo.exists():
                documents.append(
                    TestDocument(
                        name=name,
                        original_path=orig,
                        pseudonymized_path=pseudo,
                        doc_type="interview",
                    )
                )

        # Business documents
        for name in [
            "meeting_minutes",
            "email_chain",
            "incident_report",
            "hr_announcement",
            "contract_memo",
        ]:
            orig = originals_dir / f"{name}.txt"
            pseudo = pseudo_dir / f"{name}_pseudonymized.txt"
            if orig.exists() and pseudo.exists():
                documents.append(
                    TestDocument(
                        name=name,
                        original_path=orig,
                        pseudonymized_path=pseudo,
                        doc_type="business",
                    )
                )

        return documents

    def call_llm(self, document_content: str, prompt: str) -> tuple[str, int]:
        """Make an API call to Claude.

        Args:
            document_content: The document text
            prompt: The analysis prompt

        Returns:
            Tuple of (response_text, tokens_used)
        """
        full_prompt = f"""Please analyze the following document:

---
{document_content}
---

{prompt}"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": full_prompt}],
        )

        response_text = message.content[0].text  # type: ignore[union-attr]
        tokens_used = message.usage.input_tokens + message.usage.output_tokens

        return response_text, tokens_used

    def run_prompts_on_document(
        self, doc: TestDocument, version: str, content: str
    ) -> list[LLMResponse]:
        """Run all prompts on a document version.

        Args:
            doc: TestDocument object
            version: "original" or "pseudonymized"
            content: Document content

        Returns:
            List of LLMResponse objects
        """
        responses = []

        for prompt_type, prompt_text in PROMPTS.items():
            print(f"    Running prompt: {prompt_type}...", end=" ", flush=True)

            try:
                response_text, tokens = self.call_llm(content, prompt_text)

                response = LLMResponse(
                    document=doc.name,
                    version=version,
                    prompt_type=prompt_type,
                    prompt_text=prompt_text,
                    response_text=response_text,
                    model=self.model,
                    timestamp=datetime.now().isoformat(),
                    tokens_used=tokens,
                )
                responses.append(response)
                print(f"OK ({tokens} tokens)")

                # Rate limiting
                time.sleep(self.rate_limit_delay)

            except Exception as e:
                print(f"ERROR: {e}")
                raise

        return responses

    def process_all_documents(self, documents: list[TestDocument]) -> None:
        """Process all documents with all prompts.

        Args:
            documents: List of TestDocument objects
        """
        total = len(documents) * 2 * len(PROMPTS)  # docs * versions * prompts
        current = 0

        for doc in documents:
            print(f"\nProcessing: {doc.name} ({doc.doc_type})")

            # Original version
            print("  Original version:")
            orig_content = doc.original_path.read_text(encoding="utf-8")
            orig_responses = self.run_prompts_on_document(doc, "original", orig_content)
            self.responses.extend(orig_responses)
            current += len(PROMPTS)
            print(f"  Progress: {current}/{total}")

            # Pseudonymized version
            print("  Pseudonymized version:")
            pseudo_content = doc.pseudonymized_path.read_text(encoding="utf-8")
            pseudo_responses = self.run_prompts_on_document(
                doc, "pseudonymized", pseudo_content
            )
            self.responses.extend(pseudo_responses)
            current += len(PROMPTS)
            print(f"  Progress: {current}/{total}")

    def evaluate_response_pair(
        self, original_resp: LLMResponse, pseudo_resp: LLMResponse
    ) -> EvaluationScore:
        """Evaluate a pair of responses using LLM-as-judge.

        Args:
            original_resp: Response from original document
            pseudo_resp: Response from pseudonymized document

        Returns:
            EvaluationScore object
        """
        judge_prompt = JUDGE_PROMPT_TEMPLATE.format(
            original_response=original_resp.response_text,
            pseudonymized_response=pseudo_resp.response_text,
            prompt_text=original_resp.prompt_text,
        )

        message = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": judge_prompt}],
        )

        response_text = message.content[0].text  # type: ignore[union-attr]

        # Parse JSON from response
        try:
            # Clean up response - extract JSON
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                scores = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")

            return EvaluationScore(
                document=original_resp.document,
                prompt_type=original_resp.prompt_type,
                thematic_accuracy=int(scores.get("thematic_accuracy", 0)),
                relationship_coherence=int(scores.get("relationship_coherence", 0)),
                factual_preservation=int(scores.get("factual_preservation", 0)),
                overall_utility=int(scores.get("overall_utility", 0)),
                notes=str(scores.get("notes", "")),
                timestamp=datetime.now().isoformat(),
            )
        except (json.JSONDecodeError, ValueError) as e:
            print(f"WARNING: Failed to parse judge response: {e}")
            print(f"Raw response: {response_text}")
            return EvaluationScore(
                document=original_resp.document,
                prompt_type=original_resp.prompt_type,
                thematic_accuracy=0,
                relationship_coherence=0,
                factual_preservation=0,
                overall_utility=0,
                notes=f"Parse error: {e}",
                timestamp=datetime.now().isoformat(),
            )

    def evaluate_all_responses(self) -> None:
        """Evaluate all response pairs using LLM-as-judge."""
        # Group responses by document and prompt type
        response_map: dict[tuple[str, str], dict[str, LLMResponse]] = {}

        for resp in self.responses:
            key = (resp.document, resp.prompt_type)
            if key not in response_map:
                response_map[key] = {}
            response_map[key][resp.version] = resp

        total = len(response_map)
        current = 0

        print("\nEvaluating response pairs with LLM-as-judge...")

        for (doc_name, prompt_type), versions in response_map.items():
            current += 1
            print(f"  [{current}/{total}] {doc_name} - {prompt_type}...", end=" ")

            if "original" in versions and "pseudonymized" in versions:
                try:
                    score = self.evaluate_response_pair(
                        versions["original"], versions["pseudonymized"]
                    )
                    self.evaluations.append(score)
                    print(f"OK (utility: {score.overall_utility}/5)")

                    # Rate limiting for evaluation calls
                    time.sleep(self.rate_limit_delay)

                except Exception as e:
                    print(f"ERROR: {e}")
            else:
                print("SKIP (missing version)")

    def save_responses(self, output_path: Path) -> None:
        """Save all responses to JSON file.

        Args:
            output_path: Path to output JSON file
        """
        data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model": self.model,
                "total_responses": len(self.responses),
            },
            "responses": [
                {
                    "document": r.document,
                    "version": r.version,
                    "prompt_type": r.prompt_type,
                    "prompt_text": r.prompt_text,
                    "response_text": r.response_text,
                    "model": r.model,
                    "timestamp": r.timestamp,
                    "tokens_used": r.tokens_used,
                }
                for r in self.responses
            ],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Responses saved to: {output_path}")

    def save_evaluations(self, output_path: Path) -> None:
        """Save all evaluation scores to JSON file.

        Args:
            output_path: Path to output JSON file
        """
        data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model": self.model,
                "total_evaluations": len(self.evaluations),
            },
            "evaluations": [
                {
                    "document": e.document,
                    "prompt_type": e.prompt_type,
                    "thematic_accuracy": e.thematic_accuracy,
                    "relationship_coherence": e.relationship_coherence,
                    "factual_preservation": e.factual_preservation,
                    "overall_utility": e.overall_utility,
                    "notes": e.notes,
                    "timestamp": e.timestamp,
                }
                for e in self.evaluations
            ],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Evaluations saved to: {output_path}")

    def calculate_statistics(self) -> dict[str, Any]:
        """Calculate summary statistics from evaluations.

        Returns:
            Dictionary of statistics
        """
        if not self.evaluations:
            return {}

        # Overall scores
        all_utility = [
            e.overall_utility for e in self.evaluations if e.overall_utility > 0
        ]
        all_thematic = [
            e.thematic_accuracy for e in self.evaluations if e.thematic_accuracy > 0
        ]
        all_coherence = [
            e.relationship_coherence
            for e in self.evaluations
            if e.relationship_coherence > 0
        ]
        all_factual = [
            e.factual_preservation
            for e in self.evaluations
            if e.factual_preservation > 0
        ]

        def calc_stats(values: list[int]) -> dict[str, Any]:
            if not values:
                return {"mean": 0, "median": 0, "std": 0, "min": 0, "max": 0}
            n = len(values)
            mean = sum(values) / n
            sorted_vals = sorted(values)
            median = (
                sorted_vals[n // 2]
                if n % 2
                else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
            )
            variance = sum((x - mean) ** 2 for x in values) / n
            std = variance**0.5
            return {
                "mean": round(mean, 2),
                "median": median,
                "std": round(std, 2),
                "min": min(values),
                "max": max(values),
            }

        # By document type
        interview_utility = [
            e.overall_utility
            for e in self.evaluations
            if e.document.startswith("interview") and e.overall_utility > 0
        ]
        business_utility = [
            e.overall_utility
            for e in self.evaluations
            if not e.document.startswith("interview") and e.overall_utility > 0
        ]

        # By prompt type
        themes_utility = [
            e.overall_utility
            for e in self.evaluations
            if e.prompt_type == "themes" and e.overall_utility > 0
        ]
        relationships_utility = [
            e.overall_utility
            for e in self.evaluations
            if e.prompt_type == "relationships" and e.overall_utility > 0
        ]
        actions_utility = [
            e.overall_utility
            for e in self.evaluations
            if e.prompt_type == "actions" and e.overall_utility > 0
        ]

        return {
            "overall_utility": calc_stats(all_utility),
            "thematic_accuracy": calc_stats(all_thematic),
            "relationship_coherence": calc_stats(all_coherence),
            "factual_preservation": calc_stats(all_factual),
            "by_document_type": {
                "interview": calc_stats(interview_utility),
                "business": calc_stats(business_utility),
            },
            "by_prompt_type": {
                "themes": calc_stats(themes_utility),
                "relationships": calc_stats(relationships_utility),
                "actions": calc_stats(actions_utility),
            },
            "pass_threshold": 4.0,
            "passed": calc_stats(all_utility).get("mean", 0) >= 4.0,
            "total_evaluations": len(self.evaluations),
            "valid_evaluations": len(all_utility),
        }

    def print_summary(self, stats: dict[str, Any]) -> None:
        """Print a summary of the evaluation results.

        Args:
            stats: Statistics dictionary
        """
        print("\n" + "=" * 60)
        print("LLM UTILITY PRESERVATION TEST RESULTS")
        print("=" * 60)

        overall = stats.get("overall_utility", {})
        print(f"\nOVERALL UTILITY SCORE: {overall.get('mean', 0):.2f}/5.0")
        print(f"  Median: {overall.get('median', 0)}")
        print(f"  Std Dev: {overall.get('std', 0):.2f}")
        print(f"  Range: {overall.get('min', 0)} - {overall.get('max', 0)}")

        print(f"\nPASS THRESHOLD: {stats.get('pass_threshold', 4.0)}/5.0 (80%)")
        result = "PASS" if stats.get("passed") else "FAIL"
        print(f"RESULT: {result}")

        print("\nBY DIMENSION:")
        for dim in [
            "thematic_accuracy",
            "relationship_coherence",
            "factual_preservation",
        ]:
            dim_stats = stats.get(dim, {})
            print(
                f"  {dim.replace('_', ' ').title()}: {dim_stats.get('mean', 0):.2f}/5.0"
            )

        print("\nBY DOCUMENT TYPE:")
        for doc_type, doc_stats in stats.get("by_document_type", {}).items():
            print(f"  {doc_type.title()}: {doc_stats.get('mean', 0):.2f}/5.0")

        print("\nBY PROMPT TYPE:")
        for prompt_type, prompt_stats in stats.get("by_prompt_type", {}).items():
            print(f"  {prompt_type.title()}: {prompt_stats.get('mean', 0):.2f}/5.0")

        print(f"\nTotal evaluations: {stats.get('total_evaluations', 0)}")
        print(f"Valid evaluations: {stats.get('valid_evaluations', 0)}")
        print("=" * 60)


def main() -> int:
    """Main entry point."""
    # Paths
    project_root = Path(__file__).parent.parent
    test_dir = project_root / "tests" / "test_corpus" / "llm_test"
    qa_dir = project_root / "docs" / "qa"

    responses_path = qa_dir / "llm-test-responses.json"
    evaluations_path = qa_dir / "llm-evaluation-scores.json"

    print("=" * 60)
    print("LLM Utility Preservation Testing")
    print("Story 4.1 - GDPR Pseudonymizer Validation")
    print("=" * 60)

    # Initialize tester
    try:
        tester = LLMUtilityTester(rate_limit_delay=1.5)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1

    # Load documents
    print("\nLoading test documents...")
    documents = tester.load_test_documents(test_dir)
    print(f"Found {len(documents)} document pairs")

    if len(documents) != 10:
        print(f"WARNING: Expected 10 documents, found {len(documents)}")

    # Run prompts
    print("\nRunning LLM prompts on all documents...")
    tester.process_all_documents(documents)

    # Save responses
    tester.save_responses(responses_path)

    # Evaluate with LLM-as-judge
    tester.evaluate_all_responses()

    # Save evaluations
    tester.save_evaluations(evaluations_path)

    # Calculate and display statistics
    stats = tester.calculate_statistics()
    tester.print_summary(stats)

    # Save statistics to evaluations file (update)
    eval_data = json.loads(evaluations_path.read_text(encoding="utf-8"))
    eval_data["statistics"] = stats
    evaluations_path.write_text(
        json.dumps(eval_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return 0 if stats.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
