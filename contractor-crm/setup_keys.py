"""Interactive setup for API keys. Run: python setup_keys.py"""
import getpass
from pathlib import Path

ENV_PATH = Path(__file__).parent / ".env"


def main():
    print("\n--- Contractor CRM: API Key Setup ---\n")
    print("Keys are stored in .env (gitignored, never sent to the browser).\n")

    existing = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    anthropic = existing.get("ANTHROPIC_API_KEY", "")
    openai = existing.get("OPENAI_API_KEY", "")

    masked_a = f"...{anthropic[-4:]}" if len(anthropic) > 4 else "(not set)"
    masked_o = f"...{openai[-4:]}" if len(openai) > 4 else "(not set)"

    print(f"  Anthropic key: {masked_a}")
    print(f"  OpenAI key:    {masked_o}\n")

    new_anthropic = getpass.getpass("Anthropic API key (Enter to keep current): ").strip()
    new_openai = getpass.getpass("OpenAI API key   (Enter to keep current): ").strip()

    if new_anthropic:
        existing["ANTHROPIC_API_KEY"] = new_anthropic
    if new_openai:
        existing["OPENAI_API_KEY"] = new_openai

    if not existing.get("ANTHROPIC_API_KEY") and not existing.get("OPENAI_API_KEY"):
        print("\nNo keys configured. AI features will be disabled.")
        return

    ENV_PATH.write_text(
        "\n".join(f"{k}={v}" for k, v in existing.items()) + "\n"
    )
    print(f"\nSaved to {ENV_PATH}")
    print("Restart the server for changes to take effect.\n")


if __name__ == "__main__":
    main()
