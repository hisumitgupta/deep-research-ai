from dotenv import load_dotenv


load_dotenv()

# Current MVP model route.
# Mistral is active across planner, intent, synthesis, critic, and social text.
# Gemini is not enabled because the free tier can return quota exhausted errors.
MISTRAL_MODEL = "mistral-small-latest"
PLANNER_MODEL = MISTRAL_MODEL
RESEARCHER_MODEL = MISTRAL_MODEL
SYNTHESIS_MODEL = MISTRAL_MODEL
CRITIC_MODEL = MISTRAL_MODEL

# Research settings
MAX_SOURCES_PER_AGENT = 3
MIN_SOURCES_REQUIRED = 8
MAX_RETRIES = 2
MAX_REPORT_WORDS = 1500

# Token optimization
WEB_SNIPPET_LIMIT = 500
PAPER_ABSTRACT_LIMIT = 800
YOUTUBE_TRANSCRIPT_LIMIT = 1000
SCRAPED_CONTENT_LIMIT = 2000
