class GenerationError(Exception):
    def __init__(
        self,
        code: str,
        detail: str = "Não foi possível gerar a trilha.",
    ):
        super().__init__(detail)
        self.code = code
        self.detail = detail


class GenerationValidationError(GenerationError):
    def __init__(self):
        super().__init__("generation_validation_failed")


class GenerationInputError(GenerationError):
    def __init__(self):
        super().__init__("generation_input_invalid")


class GenerationPersistenceError(GenerationError):
    def __init__(self):
        super().__init__("generation_persistence_failed")


class GenerationTransientError(GenerationError):
    def __init__(self):
        super().__init__("generation_transient_failed")
