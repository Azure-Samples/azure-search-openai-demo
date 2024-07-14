class CompatibilityWrapper:
    def __init__(self, event):
        self.event = event

        if hasattr(self.event, "model_dump"):
            self.event = self.event.model_dump()

    def __getattr__(self, item):
        try:
            # Attempt to access the attribute directly (for data class approach)
            return getattr(self.event, item)
        except AttributeError:
            # Fallback to dictionary-style access
            if item in self.event:
                return self.event[item]
            else:
                raise AttributeError(f"'{type(self.event).__name__}' object has no attribute '{item}'")
