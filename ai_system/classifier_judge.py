from pathlib import Path
from typing import Literal

from crewai import Agent, Crew, Process, Task
from pydantic import BaseModel, Field

CLASSIFIER_MODEL = "gemini/gemini-3.8-flash"
JUDGE_MODEL = "gemini/gemini-3.8-flash"

PROMPTS_DIR = Path(__file__).parent / "prompts"

Label = Literal["positive", "negative"]


class Classification(BaseModel):
    label: Label
    confidence: float = Field(ge=0, le=1, description="Confidence between 0 and 1")
    evidence: list[str] = Field(description="Verbatim quotes from the review that support the label")
    reasoning: str = Field(description="Brief explanation, 1-2 sentences")


class Verdict(BaseModel):
    agrees: bool = Field(description="True if the judge confirms the classifier's label")
    final_label: Label
    score: int = Field(ge=1, le=10, description="Quality of the classification according to the rubric")
    reason: str = Field(description="Why the judge confirms or corrects, 1-2 sentences")


def load_prompt(name: str) -> str:
    """Read a task prompt from prompts/<name>.txt ({review} is filled in by the crew)."""
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()


classifier = Agent(
    role="Sentiment classifier",
    goal="Classify movie reviews as positive or negative, with textual evidence",
    backstory=(
        "You are an opinion analyst with years of experience reading film reviews. "
        "You separate the author's overall opinion from isolated remarks, "
        "and you detect sarcasm and mixed reviews."
    ),
    llm=CLASSIFIER_MODEL,
    allow_delegation=False,
)

judge = Agent(
    role="Classification judge",
    goal="Audit the classifier's label and correct it only when there is clear evidence",
    backstory=(
        "You are a skeptical but fair reviewer. You do not change a label over a minor doubt: "
        "you only correct it when the text of the review clearly contradicts the classifier."
    ),
    llm=JUDGE_MODEL,
    allow_delegation=False,
)

classification_task = Task(
    description=load_prompt("classifier"),
    expected_output="Label (positive/negative), confidence from 0 to 1, evidence quotes and brief reasoning.",
    agent=classifier,
    output_pydantic=Classification,
)

judge_task = Task(
    description=load_prompt("judge"),
    expected_output="Agreement (yes/no), final label, score from 1 to 10 and a brief reason.",
    agent=judge,
    context=[classification_task],  # the judge receives the classifier's output
    output_pydantic=Verdict,
)

crew = Crew(
    agents=[classifier, judge],
    tasks=[classification_task, judge_task],
    process=Process.sequential,
)


def classify(review: str) -> dict:
    """Run classifier + judge on one review and return both outputs."""
    # Flask handlers under gunicorn's sync worker have no event loop, so the sync kickoff is used here
    result = crew.kickoff(inputs={"review": review})
    classification: Classification = result.tasks_output[0].pydantic
    verdict: Verdict = result.pydantic  # output of the last task
    return {
        "classifier": classification.model_dump(),
        "judge": verdict.model_dump(),
    }
