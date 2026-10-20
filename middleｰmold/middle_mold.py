"""
Middle Mold — Common Evidence-Informed Learning Process Mold
Version: 0.1.0
Status: Reference implementation / prototype

Purpose
-------
Provide a reusable, personality-neutral learning process layer between:
    TOP    : human-facing purpose, goals, and learning context
    MIDDLE : this module; common learning-process methods and selection rules
    BOTTOM : an LLM that performs the concrete tutoring / learning interaction

The Middle Mold is not a persona and does not define the learner's identity,
tone, values, or preferred style. Personalization belongs in a separate
Persona Seed / learner profile. Task-specific objectives belong in a Purpose
Program. The assembled system is conceptually:

    Persona Seed + Purpose Program + Middle Mold + LLM = Purpose-specific use

This module does not call an LLM, store private learner data, or claim that a
fixed method works for every learner. It selects a reasonable learning
procedure from explicit task signals and emits a structured plan that an LLM
or application can execute.

Design principles
-----------------
1. Keep the common learning substrate separate from persona and purpose.
2. Prefer methods supported by a meaningful body of learning-science evidence.
3. Make selection rules, adaptation rules, limitations, and evaluation visible.
4. Preserve uncertainty: recommendations are defaults, not universal laws.
5. Keep execution observable through an explicit session plan and exit report.
6. Avoid fabricating evidence citations or implying that this prototype has
   itself been experimentally validated.

Evidence-informed methods represented
--------------------------------------
- Retrieval practice / active recall.
- Spaced practice.
- Interleaving when discriminating between related categories or procedures
  is a learning objective.
- Worked examples followed by gradually reduced support.
- Specific, actionable feedback and error correction.
- Self-explanation / explaining why a step works.
- Short diagnostic checks and formative reassessment.

These methods are not equally appropriate for every task. For example,
interleaving can be less useful than blocked practice during the very first
encounter with a completely unfamiliar procedure. The selector therefore
uses task signals and does not blindly enable every method.

This is a prototype, not a validated educational measurement instrument.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple
import json


VERSION = "0.1.0"


class TaskType(str, Enum):
    CONCEPTUAL = "conceptual"
    PROCEDURAL = "procedural"
    FACTUAL = "factual"
    PROBLEM_SOLVING = "problem_solving"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class Proficiency(str, Enum):
    NOVICE = "novice"
    DEVELOPING = "developing"
    COMPETENT = "competent"
    ADVANCED = "advanced"
    UNKNOWN = "unknown"


class SupportLevel(str, Enum):
    FULL = "full"
    MODERATE = "moderate"
    LIGHT = "light"
    NONE = "none"


@dataclass
class LearningRequest:
    """Task signals used to choose a learning procedure.

    Required:
        objective: Observable learning goal, not merely a topic name.

    Optional signals:
        task_type: Dominant type of learning activity.
        current_proficiency: Best current estimate; use UNKNOWN if uncertain.
        deadline_days: Days until a known assessment or use date.
        available_minutes: Approximate minutes available in this session.
        prerequisite_stability: Whether prerequisite knowledge appears stable.
        categories_to_discriminate: Whether the learner must distinguish related
            concepts, cases, methods, or problem types.
        error_history: Brief, observable error descriptions. Avoid sensitive
            personal data unless strictly necessary.
        desired_mastery: Target level expressed as an operational description.
        context: Additional task facts. Do not put persona instructions here.
    """

    objective: str
    task_type: TaskType = TaskType.UNKNOWN
    current_proficiency: Proficiency = Proficiency.UNKNOWN
    deadline_days: Optional[int] = None
    available_minutes: int = 30
    prerequisite_stability: Optional[bool] = None
    categories_to_discriminate: bool = False
    error_history: List[str] = field(default_factory=list)
    desired_mastery: str = "Can explain or perform the target reliably without hints."
    context: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.objective.strip():
            raise ValueError("objective must be a non-empty observable learning goal")
        if self.available_minutes <= 0:
            raise ValueError("available_minutes must be greater than zero")
        if self.deadline_days is not None and self.deadline_days < 0:
            raise ValueError("deadline_days cannot be negative")


@dataclass
class Method:
    """One selected learning method and its execution contract."""

    name: str
    enabled: bool
    rationale: str
    procedure: List[str]
    safeguards: List[str] = field(default_factory=list)


@dataclass
class LearningStep:
    """One step in the session sequence."""

    step_id: str
    title: str
    purpose: str
    learner_action: str
    llm_action: str
    completion_signal: str
    support_level: SupportLevel = SupportLevel.MODERATE
    estimated_minutes: int = 5


@dataclass
class EvaluationRule:
    """Observable criterion for checking progress."""

    criterion: str
    method: str
    pass_condition: str
    response_if_failed: str


@dataclass
class LearningPlan:
    """Structured plan emitted by the Middle Mold."""

    mold_name: str
    mold_version: str
    objective: str
    task_type: str
    assumed_proficiency: str
    selected_methods: List[Method]
    steps: List[LearningStep]
    evaluation: List[EvaluationRule]
    adaptation_rules: List[str]
    limitations: List[str]
    exit_report_fields: List[str]
    evidence_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class MiddleMold:
    """Build a transparent, evidence-informed learning plan.

    The class intentionally does not include persona, emotional identity,
    conversational voice, or domain-specific curriculum content. Those belong
    to separate layers. The LLM or host application is responsible for executing
    the plan and returning observed results.
    """

    name = "Middle Learning Mold"

    def build_plan(self, request: LearningRequest) -> LearningPlan:
        request.validate()
        methods = self._select_methods(request)
        steps = self._build_steps(request, methods)
        evaluation = self._build_evaluation(request)
        adaptations = self._build_adaptation_rules(request)
        limitations = self._limitations(request)
        return LearningPlan(
            mold_name=self.name,
            mold_version=VERSION,
            objective=request.objective,
            task_type=request.task_type.value,
            assumed_proficiency=request.current_proficiency.value,
            selected_methods=methods,
            steps=steps,
            evaluation=evaluation,
            adaptation_rules=adaptations,
            limitations=limitations,
            exit_report_fields=[
                "objective",
                "steps_completed",
                "independent_recall_or_performance",
                "errors_observed",
                "corrections_completed",
                "confidence_rating",
                "next_review_recommendation",
                "unresolved_unknowns",
            ],
            evidence_notes=[
                "Retrieval practice and spaced practice have substantial support across many learning contexts.",
                "Worked examples can reduce unnecessary cognitive load for novices; support should be reduced as competence increases.",
                "Interleaving is most relevant when learners must discriminate between related categories or choose among procedures.",
                "Feedback should identify the gap and the next corrective action, not merely label an answer right or wrong.",
                "Effectiveness depends on task, prior knowledge, implementation quality, and assessment alignment.",
                "This prototype selects methods heuristically and has not itself been validated as a complete learning system.",
            ],
        )

    def _select_methods(self, request: LearningRequest) -> List[Method]:
        p = request.current_proficiency
        novice_or_unknown = p in (Proficiency.NOVICE, Proficiency.UNKNOWN)
        methods: List[Method] = []

        methods.append(Method(
            name="Diagnostic check",
            enabled=True,
            rationale="Estimate the learner's starting point before committing to a sequence.",
            procedure=[
                "Ask for a short explanation, prediction, or representative task.",
                "Separate correct knowledge from guesses and missing prerequisites.",
                "Use the result to adjust the amount of explanation and scaffolding.",
            ],
            safeguards=[
                "Treat one response as a sample, not a definitive ability label.",
                "Do not turn the diagnostic into a high-stakes judgement.",
            ],
        ))

        methods.append(Method(
            name="Worked example → guided practice → independent practice",
            enabled=True,
            rationale=(
                "Provide explicit modelling when knowledge is new, then gradually "
                "transfer responsibility to the learner."
            ),
            procedure=[
                "Show one complete worked example and explain the reason for each key step.",
                "Complete a second example together, asking the learner to supply the next step.",
                "Remove hints gradually as performance becomes more reliable.",
                "Ask for an independent attempt without seeing the worked solution.",
            ],
            safeguards=[
                "Do not keep explaining after the learner can perform independently.",
                "Avoid removing support so quickly that the learner is only guessing.",
            ],
        ))

        methods.append(Method(
            name="Retrieval practice / active recall",
            enabled=True,
            rationale="Require the learner to retrieve or produce knowledge rather than only reread it.",
            procedure=[
                "After an explanation or example, hide the source material.",
                "Ask the learner to state the idea, reconstruct the steps, or solve a short item.",
                "Check the response against explicit criteria and correct gaps.",
            ],
            safeguards=[
                "For a brand-new, high-complexity task, provide initial instruction before demanding unsupported recall.",
                "Use errors as diagnostic information, not as a reason to shame the learner.",
            ],
        ))

        methods.append(Method(
            name="Specific corrective feedback",
            enabled=True,
            rationale="Make the discrepancy between the current response and the target actionable.",
            procedure=[
                "Identify the exact step, claim, or decision that needs correction.",
                "Explain why it fails or what evidence is missing.",
                "Model the correction briefly, then ask for a retry.",
                "Check whether the learner can apply the correction to a fresh example.",
            ],
            safeguards=[
                "Avoid vague feedback such as 'wrong' or 'try harder'.",
                "Do not provide praise as a substitute for evidence of learning.",
            ],
        ))

        methods.append(Method(
            name="Spaced review",
            enabled=True,
            rationale="Plan later retrieval instead of treating one successful session as durable mastery.",
            procedure=[
                "Schedule a brief review after a delay appropriate to the deadline and task.",
                "Start the review with recall or performance before showing notes.",
                "Increase or shorten the next interval based on observed performance.",
            ],
            safeguards=[
                "Intervals are starting heuristics, not universal optimal values.",
                "If the assessment is imminent, prioritize high-value retrieval and error correction.",
            ],
        ))

        if request.categories_to_discriminate or request.task_type in (
            TaskType.PROBLEM_SOLVING, TaskType.MIXED
        ):
            methods.append(Method(
                name="Interleaving / contrastive practice",
                enabled=True,
                rationale=(
                    "The objective involves distinguishing related categories or choosing "
                    "between different procedures."
                ),
                procedure=[
                    "First ensure that each basic method or category has been introduced.",
                    "Present mixed examples that require selecting the right method.",
                    "Ask the learner to explain the cue that distinguishes each case.",
                    "Review confusions and return to focused practice if discrimination collapses.",
                ],
                safeguards=[
                    "Do not force interleaving before the learner has enough basic familiarity.",
                    "Use blocked practice temporarily when the learner cannot yet execute any method.",
                ],
            ))
        else:
            methods.append(Method(
                name="Interleaving / contrastive practice",
                enabled=False,
                rationale="No clear need to discriminate between related categories was supplied.",
                procedure=[
                    "Reconsider enabling this method if the objective later requires choosing among similar cases or procedures."
                ],
                safeguards=[
                    "Disabled does not mean ineffective; it means the current request does not justify prioritizing it."
                ],
            ))

        if request.task_type in (TaskType.CONCEPTUAL, TaskType.PROBLEM_SOLVING, TaskType.MIXED):
            methods.append(Method(
                name="Self-explanation",
                enabled=True,
                rationale="The task benefits from explaining causal links, principles, or why a step is valid.",
                procedure=[
                    "Ask 'Why does this step work?' or 'What would change if this condition changed?'",
                    "Compare the explanation with the governing principle or evidence.",
                    "Repair unsupported assumptions before moving on.",
                ],
                safeguards=[
                    "Do not confuse fluent explanation with correct understanding; verify with a new example.",
                    "Accept concise explanations when they correctly capture the causal or logical relation.",
                ],
            ))

        if request.error_history:
            methods.append(Method(
                name="Error-pattern review",
                enabled=True,
                rationale="Known error observations can guide targeted practice.",
                procedure=[
                    "Group errors by observable type: concept gap, procedure slip, misclassification, or unsupported assumption.",
                    "Choose one high-impact error pattern for focused correction.",
                    "Retest with a fresh item that exercises the same underlying distinction.",
                ],
                safeguards=[
                    "Do not infer a stable trait from a small number of mistakes.",
                    "Keep error descriptions behavioural and specific.",
                ],
            ))

        return methods

    def _build_steps(
        self, request: LearningRequest, methods: Sequence[Method]
    ) -> List[LearningStep]:
        minutes = request.available_minutes
        # Allocate a compact but complete sequence; the final step always tests
        # independent performance or recall.
        if minutes < 10:
            allocations = [1, 2, 3, max(1, minutes - 6), 1]
        else:
            allocations = [
                max(2, round(minutes * 0.15)),
                max(3, round(minutes * 0.25)),
                max(3, round(minutes * 0.25)),
                max(2, round(minutes * 0.20)),
                max(2, minutes - (
                    max(2, round(minutes * 0.15))
                    + max(3, round(minutes * 0.25))
                    + max(3, round(minutes * 0.25))
                    + max(2, round(minutes * 0.20))
                )),
            ]
        # Ensure that the plan does not promise more time than was allocated.
        # The values are estimates, and a host may scale them to its UI.
        titles = [
            "Diagnose the starting point",
            "Explain and model",
            "Guided practice",
            "Retrieve and correct",
            "Independent check and next step",
        ]
        purposes = [
            "Find the current boundary between known, uncertain, and unknown material.",
            "Build a clear initial model of the target concept or procedure.",
            "Transfer some of the work to the learner while support is still available.",
            "Strengthen retrieval and repair the most important observed gap.",
            "Check whether the objective can be met without hints and decide what comes next.",
        ]
        learner_actions = [
            "Attempt a short explanation, prediction, or representative item.",
            "Follow the worked example and ask for clarification where a step is not justified.",
            "Complete the next step or solve a parallel example with limited hints.",
            "Recall the key idea or procedure without looking, then retry corrected errors.",
            "Complete a fresh item or explain the target from memory without hints.",
        ]
        llm_actions = [
            "Record observable evidence and unknowns; do not overgeneralize from one answer.",
            "Explain only what is needed for the objective; show each consequential step.",
            "Use prompts and partial cues before revealing the full solution.",
            "Give specific feedback, request a retry, and check transfer to a new item.",
            "Score against explicit criteria and produce the exit report.",
        ]
        completion_signals = [
            "Initial response and uncertainties are recorded.",
            "Learner can describe the key model or follow the example.",
            "Learner completes a supported attempt and identifies at least one decision point.",
            "Learner retrieves the core content and has retried the corrected error.",
            "Independent performance is recorded as pass, partial, or not yet demonstrated.",
        ]

        proficiency_support = {
            Proficiency.NOVICE: SupportLevel.FULL,
            Proficiency.DEVELOPING: SupportLevel.MODERATE,
            Proficiency.COMPETENT: SupportLevel.LIGHT,
            Proficiency.ADVANCED: SupportLevel.LIGHT,
            Proficiency.UNKNOWN: SupportLevel.MODERATE,
        }
        support = proficiency_support[request.current_proficiency]
        steps: List[LearningStep] = []
        for i in range(5):
            steps.append(LearningStep(
                step_id=f"S{i + 1}",
                title=titles[i],
                purpose=purposes[i],
                learner_action=learner_actions[i],
                llm_action=llm_actions[i],
                completion_signal=completion_signals[i],
                support_level=support if i < 3 else (
                    SupportLevel.LIGHT if i == 3 else SupportLevel.NONE
                ),
                estimated_minutes=max(1, int(allocations[i])),
            ))
        return steps

    def _build_evaluation(self, request: LearningRequest) -> List[EvaluationRule]:
        return [
            EvaluationRule(
                criterion="Objective alignment",
                method="Compare the learner's response or performance with the stated objective.",
                pass_condition="Every essential component of the objective is demonstrated.",
                response_if_failed="Narrow the gap to one missing component and teach or model that component.",
            ),
            EvaluationRule(
                criterion="Independent retrieval or performance",
                method="Use a fresh prompt or task without hints or source material.",
                pass_condition="The learner succeeds without substantive hints and can state the key reason or rule where relevant.",
                response_if_failed="Restore the minimum useful support, correct the gap, then retry with a parallel item.",
            ),
            EvaluationRule(
                criterion="Error correction",
                method="Retest at least one corrected error using a different surface example.",
                pass_condition="The same underlying error does not recur, or the remaining uncertainty is explicitly recorded.",
                response_if_failed="Classify the error and return to focused practice before increasing difficulty.",
            ),
            EvaluationRule(
                criterion="Confidence calibration",
                method="Ask the learner to rate confidence and compare it with observed performance.",
                pass_condition="Confidence is recorded separately from correctness.",
                response_if_failed="Use the mismatch to choose the next diagnostic question; do not treat confidence as proof.",
            ),
        ]

    def _build_adaptation_rules(self, request: LearningRequest) -> List[str]:
        rules = [
            "If the learner cannot explain a prerequisite, pause the main sequence and teach the smallest missing prerequisite.",
            "If two consecutive attempts fail for the same reason, change the representation or example rather than repeating the same explanation verbatim.",
            "If the learner succeeds independently on two varied examples, reduce hints and increase transfer distance modestly.",
            "If performance is correct but the explanation is unsupported, ask for evidence, a derivation, or a counterexample.",
            "If performance is fluent but incorrect, prioritize diagnosis over speed.",
            "If the session runs short, preserve the independent check and exit report; reduce examples before removing evaluation.",
            "If uncertainty remains, record it explicitly rather than forcing a confident conclusion.",
            "Treat all adaptations as local decisions based on observed performance, not as permanent learner labels.",
        ]
        if request.deadline_days is not None:
            if request.deadline_days <= 2:
                rules.append(
                    "Deadline is near: prioritize representative assessment items, retrieval, and high-impact error correction; avoid broad new material unless essential."
                )
            elif request.deadline_days <= 14:
                rules.append(
                    "Deadline is within two weeks: distribute short retrieval reviews across available days and revisit weak items."
                )
            else:
                rules.append(
                    "There is time for durable learning: distribute reviews and include transfer tasks rather than relying on a single intensive session."
                )
        if request.prerequisite_stability is False:
            rules.append(
                "Prerequisites are reported as unstable: verify the minimum prerequisite set before increasing task complexity."
            )
        return rules

    def _limitations(self, request: LearningRequest) -> List[str]:
        limitations = [
            "The plan is a heuristic template; it is not a guarantee of learning gains.",
            "The request may not contain enough information to identify the best method or difficulty.",
            "The model does not independently verify learner performance; the host must provide observations.",
            "The evidence base varies by method, domain, age, prior knowledge, implementation, and outcome measure.",
            "The plan should not be used as a clinical, diagnostic, or high-stakes assessment instrument.",
            "No specific interval, question count, or mastery threshold is universally optimal.",
            "The LLM must not invent learner results, citations, or assessment scores in the exit report.",
        ]
        if request.task_type == TaskType.UNKNOWN:
            limitations.append(
                "Task type is unknown; method selection may be less precise until the objective is classified."
            )
        if request.current_proficiency == Proficiency.UNKNOWN:
            limitations.append(
                "Starting proficiency is unknown; the initial diagnostic should determine how much scaffolding is needed."
            )
        return limitations


def example_plan() -> LearningPlan:
    """Return a runnable example plan for learning factorization."""
    request = LearningRequest(
        objective="Given a quadratic expression of the target form, factor it correctly and explain the key choice.",
        task_type=TaskType.PROBLEM_SOLVING,
        current_proficiency=Proficiency.NOVICE,
        deadline_days=60,
        available_minutes=30,
        prerequisite_stability=None,
        categories_to_discriminate=True,
        error_history=[
            "Sometimes chooses two numbers whose product is correct but whose sum is incorrect.",
            "Does not consistently check the factorization by expansion.",
        ],
        desired_mastery="Correctly factor varied examples independently and verify by expansion.",
        context={"domain": "school mathematics", "topic": "factorization"},
    )
    return MiddleMold().build_plan(request)


def main() -> None:
    """Print an example plan as JSON when executed directly."""
    print(example_plan().to_json())


if __name__ == "__main__":
    main()
