from pathlib import Path


# Project root
BASE_DIR = Path(__file__).resolve().parent.parent


# Drive to scan
DRIVE = "C:"

# Database
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "storage_index.db"


# MFT safety
MIN_AVAILABLE_RAM_MB = 1024


# Database insertion
BATCH_SIZE = 10_000

# ============================================================
# AI PROVIDER SETTINGS
# ============================================================

# API Keys
#
# Development / diagnostic only.
# Before distributing the application, API keys should be
# stored securely through APIKeyStore or OS credential storage.

GROQ_API_KEY = ""

GEMINI_API_KEY = ""

OPENROUTER_API_KEY = ""


# Default AI provider
AI_DEFAULT_PROVIDER = "groq"


# Provider fallback order
AI_FALLBACK_PROVIDERS = [
    "gemini",
    "openrouter",
]


# ============================================================
# AI EXECUTION SETTINGS
# ============================================================

# Maximum AI batches processed concurrently.
AI_MAX_WORKERS = 6

# Maximum simultaneous requests to one provider.
AI_PROVIDER_MAX_CONCURRENT_REQUESTS = 3


# ============================================================
# AI BATCH SETTINGS
# ============================================================

# Complex / deeply drilled clusters per AI request.
AI_DEEP_BATCH_SIZE = 3

# Simpler / shallow clusters per AI request.
AI_SHALLOW_BATCH_SIZE = 5

# A cluster at or above this drill depth is considered deep.
AI_DEEP_DRILL_THRESHOLD = 2


# ============================================================
# ITERATIVE AI ANALYSIS
# ============================================================

AI_MAX_ANALYSIS_ROUNDS = 4

AI_MINIMUM_CHILD_SIZE = (
    50 * 1024 * 1024
)

AI_MAX_CHILDREN_PER_EXPANSION = 10