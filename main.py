from dotenv import load_dotenv
from src.discord_bot import run
import os

if __name__ == "__main__":
    # Load variables from .env into environment
    load_dotenv()
    # Optionally prepend extra LaTeX bin directories to PATH (semicolon-separated on Windows)
    extra = os.environ.get("LATEXBIN_DIRS")
    if extra:
        sep = os.pathsep
        os.environ["PATH"] = extra + sep + os.environ.get("PATH", "")
    run()
