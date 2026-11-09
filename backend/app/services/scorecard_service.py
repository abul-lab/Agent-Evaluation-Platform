"""Service layer orchestrating trace evaluation and scorecard generation."""

from app.domain.models import CanonicalTrace
from app.scorecard.aggregator import ScorecardAggregator
from app.scorecard.score_models import Scorecard
from app.services.deterministic_evaluator import DeterministicEvaluationService


class ScorecardService:
    """Coordinates deterministic trace evaluation and scorecard synthesis."""

    def __init__(
        self,
        eval_service: DeterministicEvaluationService | None = None,
        aggregator: type[ScorecardAggregator] = ScorecardAggregator,
    ) -> None:
        self.eval_service = eval_service or DeterministicEvaluationService()
        self.aggregator = aggregator

    def evaluate_and_generate_scorecard(self, trace: CanonicalTrace) -> Scorecard:
        """Run deterministic evaluation on a CanonicalTrace and return the resulting Scorecard."""
        eval_result = self.eval_service.evaluate_trace(trace)
        return self.aggregator.aggregate(eval_result)
