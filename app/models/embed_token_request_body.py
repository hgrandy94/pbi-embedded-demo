class EmbedTokenRequestBody:
    """Request body for the Power BI GenerateToken API."""

    datasets = None
    reports = None
    targetWorkspaces = None
    identities = None

    def __init__(self):
        self.datasets = []
        self.reports = []
        self.targetWorkspaces = []
        self.identities = []
