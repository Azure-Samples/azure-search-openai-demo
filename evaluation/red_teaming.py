import glob
import json
import logging
import os
import time
from pathlib import Path

import yaml
from pyrit.common.path import DATASETS_PATH
from pyrit.models import AttackStrategy
from pyrit.orchestrator import RedTeamingOrchestrator
from pyrit.prompt_target import PromptChatTarget
from pyrit.score import SelfAskTrueFalseScorer, TrueFalseQuestionPaths

RED_TEAMING_RESULTS_DIR = "red_teaming"

logger = logging.getLogger("evaluation")

text_generation_strategy_path = DATASETS_PATH / "orchestrators" / "red_teaming" / "text_generation.yaml"


async def run_red_teaming(
    working_dir: Path,
    scorer_dir: Path,
    config: dict,
    red_teaming_llm: PromptChatTarget,
    prompt_target: PromptChatTarget,
):
    """Run red teaming attack with provided scorers using Red Teaming Orchestrator."""
    logger.info("Running red teaming attack, with scorers from '%s'", scorer_dir)
    scorers = [Path(scorer_file) for scorer_file in glob.glob(os.path.join(scorer_dir, "*.yaml"))]
    # Add built-in scorers
    scorers.extend([path.value for path in TrueFalseQuestionPaths])
    results = []

    for scorer_path in scorers:
        logger.info("Runing red teaming with scorer YAML: %s", scorer_path)
        try:
            scorer_data = validate_scorer_yaml(scorer_path)
        except ValueError as e:
            logger.error(f"Invalid scorer YAML: {e}")
            continue

        scorer = SelfAskTrueFalseScorer(chat_target=red_teaming_llm, true_false_question_path=scorer_path)
        attack_strategy = AttackStrategy(
            strategy=text_generation_strategy_path,
            conversation_objective=scorer_data.get("conversation_objective", ""),
        )

        with RedTeamingOrchestrator(
            attack_strategy=attack_strategy,
            red_teaming_chat=red_teaming_llm,
            prompt_target=prompt_target,
            initial_red_teaming_prompt="how can I help you?",
            scorer=scorer,
            verbose=True,
        ) as red_teaming_orchestrator:
            score = await red_teaming_orchestrator.apply_attack_strategy_until_completion_async(max_turns=3)
            results.append(score)

    save_score(results, working_dir / Path(config["results_dir"]) / RED_TEAMING_RESULTS_DIR)
    return results


def validate_scorer_yaml(scorer_path: Path):
    """Validate a scorer YAML file."""
    logger.info("Validating scorer YAML '%s'", scorer_path)
    with open(scorer_path) as file:
        data = yaml.safe_load(file)

    # Check for required fields
    if data is None:
        raise ValueError(f"The file {scorer_path} is empty.")
    if "category" not in data:
        raise ValueError(f"The file {scorer_path} is missing the 'category' field.")
    if "true_description" not in data:
        raise ValueError(f"The file {scorer_path} is missing the 'true_description' field.")
    if "false_description" not in data:
        raise ValueError(f"The file {scorer_path} is missing the 'false_description' field.")
    return data


def save_score(results: list, results_dir: Path):
    """Save score results to a JSON file."""
    timestamp = int(time.time())
    experiment_dir = results_dir / f"experiment-{timestamp}"
    experiment_dir.mkdir(parents=True, exist_ok=True)
    output_path = experiment_dir / "scores.json"
    logger.info("Saving score results to '%s'", output_path)

    output = [
        {
            "scorer_class_identifier": res.scorer_class_identifier["__type__"] if res.scorer_class_identifier else "",
            "score_category": res.score_category,
            "score_value": res.score_value,
            "score_rationale": res.score_rationale,
        }
        for res in results
    ]

    with open(output_path, "w") as f:
        json.dump(output, f, indent=4)
