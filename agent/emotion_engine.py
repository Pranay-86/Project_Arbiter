from core.logger import get_logger

logger = get_logger("emotion_engine")


class EmotionEngine:
    """
    Detects emotion in user input using a HuggingFace classifier.
    Model is lazy-loaded on first use to avoid slowing startup.
    Gracefully degrades if transformers is not installed.
    """

    _MODEL_NAME = "j-hartmann/emotion-english-distilroberta-base"

    def __init__(self):
        self._classifier = None

    def _load(self):
        if self._classifier is not None:
            return
        try:
            from transformers import pipeline
            self._classifier = pipeline(
                "text-classification",
                model=self._MODEL_NAME,
            )
            logger.info("EmotionEngine loaded model: %s", self._MODEL_NAME)
        except ImportError:
            logger.warning("transformers not installed — EmotionEngine disabled.")
            self._classifier = False  # sentinel: attempted but unavailable

    def detect(self, text: str) -> dict:
        self._load()
        if not self._classifier:
            return {"label": "unknown", "score": 0.0}
        result = self._classifier(text)[0]
        return {"label": result["label"], "score": result["score"]}
