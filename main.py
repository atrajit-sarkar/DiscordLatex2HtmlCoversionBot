from dotenv import load_dotenv
import os

# Load variables from .env before importing the bot so decorators can see env (e.g., DISCORD_GUILD_ID)
load_dotenv()
from src.discord_bot import run

if __name__ == "__main__":
    # Optionally prepend extra LaTeX bin directories to PATH (semicolon-separated on Windows)
    extra = os.environ.get("LATEXBIN_DIRS")
    if extra:
        sep = os.pathsep
        os.environ["PATH"] = extra + sep + os.environ.get("PATH", "")
    run()
