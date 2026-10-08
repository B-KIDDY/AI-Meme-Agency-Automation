import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
GENERATED_DIR = BASE_DIR / "generated_memes"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Database path – works on both Windows and Linux
DB_PATH = DATA_DIR / "meme_agency.db"

# Create dirs
for d in [TEMPLATES_DIR, GENERATED_DIR, DATA_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

RUN_MODE = os.getenv("RUN_MODE", "sim").lower()  # sim | live
MEMES_TO_GENERATE = int(os.getenv("MEMES_TO_GENERATE", "30"))
MEMES_TO_KEEP = int(os.getenv("MEMES_TO_KEEP", "30"))  # 30/day automation default

HUMOR_STYLES = [s.strip() for s in os.getenv(
    "HUMOR_STYLES",
    "relatable,dark,gaming,programming,anime,sarcastic"
).split(",")]

# Font paths (Windows + Linux)
FONT_PATHS = [
    # Windows
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\impact.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]
