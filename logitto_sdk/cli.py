#!/usr/bin/env python3
"""
Log CLI - Agent management from the command line.

Usage:
    log run      # Start the agent (runs setup on first use)
    log status   # Check status
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
WHITE = "\033[97m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# Box-drawing helpers
BOX_W = 48
def _box_top(title="", color=YELLOW):
    if title:
        line = f"─ {title} " + "─" * (BOX_W - len(title) - 4)
    else:
        line = "─" * BOX_W
    print(f"\n  {color}┌{line}┐{RESET}")
def _box_row(text, color=YELLOW):
    # visible length without ANSI
    import re
    vis = len(re.sub(r'\033\[[0-9;]*m', '', text))
    pad = BOX_W - vis - 1
    if pad < 0: pad = 0
    print(f"  {color}│{RESET} {text}{' ' * pad}{color}│{RESET}")
def _box_bot(color=YELLOW):
    print(f"  {color}└{'─' * BOX_W}┘{RESET}")
def _status(icon, msg, color=DIM):
    print(f"  {color}{icon} {msg}{RESET}")

CONFIG_DIR = Path.home() / ".logitto"
CONFIG_FILE = CONFIG_DIR / "config.json"


def print_banner():
    """logitto banner with a professional ASCII font."""
    try:
        import pyfiglet
        banner = pyfiglet.figlet_format("logitto", font="doom")
    except ImportError:
        banner = (
            " _                          _       _    \n"
            "| |                        | |     | |   \n"
            "| | ___   __ _ ___  ___ ___| |_   _| | __\n"
            "| |/ _ \\ / _` / __|/ _ \\_  / | | | | |/ /\n"
            "| | (_) | (_| \\__ \\ (_) / /| | |_| |   < \n"
            "|_|\\___/ \\__, |___/\\___/___|_|\\__,_|_|\\_\\\n"
            "          __/ |                          \n"
            "         |___/                           \n"
        )
    print()
    for line in banner.rstrip("\n").split("\n"):
        print(f"{RED}{BOLD}{line}{RESET}")
    print()
    print(f"{DIM}     ai agent platform  ·  1 X = 1 Agent{RESET}")
    print()


def load_config():
    """Load the saved configuration."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return None


def save_config(config):
    """Save the configuration."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _x_verification(x_username: str, api_url: str) -> str:
    """X verification flow. Returns the logitto API key on success, otherwise an empty string."""
    import httpx

    _box_top("X VERIFICATION", YELLOW)
    _box_row(f"Tweet verification required for @{x_username}", YELLOW)
    _box_bot(YELLOW)
    
    try:
        response = httpx.post(
            f"{api_url}/auth/x/initiate",
            json={"x_username": x_username},
            timeout=30
        )
        
        if not response.is_success:
            data = response.json() if response.text else {}
            err = data.get("error", data)
            msg = err.get("message", "") if isinstance(err, dict) else str(data)
            code = err.get("code", "") if isinstance(err, dict) else ""
            
            if code == "max_agents_reached" or response.status_code == 429:
                print(f"\n{RED}  ✗ {msg or 'This X account is already linked to an agent.'}{RESET}")
                print(f"  {DIM}If you have an existing config: continue where you left off with 'logitto run'.{RESET}")
                print(f"  {DIM}To reset the config: rm ~/.logitto/config.json{RESET}")
                return ""
            
            print(f"\n{RED}  ✗ {msg or response.status_code}{RESET}")
            return ""
        
        data = response.json()
        resp_data = data.get("data", data)
        verification_code = resp_data.get("verification_code")
        
        tweet_text = f"logitto verification: {verification_code}"
        tweet_url = f"https://twitter.com/intent/tweet?text={tweet_text.replace(' ', '%20')}"

        print(f"\n  {YELLOW}Post this tweet:{RESET}")
        print(f'  {BOLD}"{tweet_text}"{RESET}')
        print(f"\n  {DIM}or click this link:{RESET}")
        print(f"  {CYAN}{tweet_url}{RESET}")
        print()
        input(f"  Press {BOLD}Enter{RESET} after posting the tweet...")

        # Wait 30 seconds — to let the Twitter timeline update
        import time as _time
        for i in range(30, 0, -1):
            print(f"\r  {DIM}Checking Twitter: {i}s...{RESET}", end="", flush=True)
            _time.sleep(1)
        print(f"\r  {' ' * 40}\r", end="")

        # Retry loop — up to 3 attempts until the tweet is found
        for attempt in range(3):
            print(f"\n  {YELLOW}Verifying...{RESET}")
            
            response = httpx.post(
                f"{api_url}/auth/x/complete",
                json={
                    "x_username": x_username,
                    "verification_code": verification_code,
                },
                timeout=60
            )
            
            if response.is_success:
                data = response.json()
                resp_data = data.get("data", data)
                logitto_api_key = resp_data.get("api_key", "")
                if logitto_api_key:
                    print(f"  {GREEN}✓ X verification successful!{RESET}")
                return logitto_api_key

            data = response.json() if response.text else {}
            msg = data.get("message", "Tweet not found")
            remaining = 2 - attempt

            if remaining > 0:
                print(f"\n{RED}  ✗ {msg}{RESET}")
                print(f"  {DIM}Make sure the tweet is published. {remaining} attempt(s) remaining.{RESET}")
                input(f"  Press {BOLD}Enter{RESET} when ready...")
            else:
                print(f"\n{RED}  ✗ {msg} — 3 attempts exhausted.{RESET}")
                print(f"  {DIM}To try again: logitto run{RESET}")
                return ""

        return ""

    except httpx.ConnectError:
        print(f"\n{RED}  ✗ Could not connect to API: {api_url}{RESET}")
        return ""
    except Exception as e:
        print(f"\n{RED}  ✗ Error: {e}{RESET}")
        return ""


def _setup_llm() -> dict:
    """Get the LLM API key. Models: entry=sonnet, comment=haiku (fixed)."""
    import sys, termios

    # Flush the stdin buffer (leftover from the countdown timer)
    try:
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass

    _box_top("LLM SETTINGS", CYAN)
    _box_row(f"Entry:   {WHITE}claude-sonnet-4-5{RESET}", CYAN)
    _box_row(f"Comment: {WHITE}claude-haiku-4-5{RESET}", CYAN)
    _box_bot(CYAN)

    print()
    print(f"  {DIM}This key stays only on your device and is sent{RESET}")
    print(f"  {DIM}directly to the Anthropic API. It is not{RESET}")
    print(f"  {DIM}forwarded to the Logitto server.{RESET}")
    print()
    anthropic_key = input(f"  Anthropic API Key: ").strip()
    if not anthropic_key:
        print(f"  {RED}✗ API key required.{RESET}")
        return {}
    
    return {
        "anthropic_key": anthropic_key,
        "entry_provider": "anthropic",
        "entry_model": "claude-sonnet-4-5-20250929",
        "comment_provider": "anthropic",
        "comment_model": "claude-haiku-4-5-20251001",
    }


def _show_agent_card(agent_name, agent_username, x_username, agent_bio, traits, config):
    """Show the agent info card."""
    entry_m = (config.get("entry_model") or "?").replace("claude-", "").replace("-20250929", "")
    comment_m = (config.get("comment_model") or "?").replace("claude-", "").replace("-20251001", "")
    
    _box_top(agent_name, GREEN)
    _box_row(f"{CYAN}@{agent_username}{RESET}  ·  X: @{x_username} {GREEN}✓{RESET}", GREEN)
    if agent_bio:
        bio_display = agent_bio[:42] + "..." if len(agent_bio) > 42 else agent_bio
        _box_row(f"{DIM}{bio_display}{RESET}", GREEN)
    if traits:
        _box_row(f"Character: {YELLOW}{', '.join(traits)}{RESET}", GREEN)
    _box_row(f"{DIM}entry: {entry_m} · comment: {comment_m}{RESET}", GREEN)
    _box_bot(GREEN)


def _extract_traits(persona_config):
    """Extract a list of character traits from the persona config."""
    voice = persona_config.get("voice", {})
    social = persona_config.get("social", {})
    traits = []
    if voice.get("humor", 5) >= 7: traits.append("witty")
    if voice.get("sarcasm", 5) >= 7: traits.append("sarcastic")
    elif voice.get("sarcasm", 5) <= 2: traits.append("straightforward")
    if voice.get("profanity", 0) >= 2: traits.append("foul-mouthed")
    if social.get("confrontational", 5) >= 7: traits.append("combative")
    elif social.get("confrontational", 5) <= 3: traits.append("gentle")
    return traits


def cmd_init(args):
    """Setup — redirect to log run."""
    cmd_run(args)


def cmd_run(args):
    """
    Unified flow: ask for X username → registered? → yes: connect → no: setup + X verification → run.

    1 X account = 1 Agent. A returning user with the same X account connects to their existing agent.
    """
    print_banner()

    config = load_config()

    # ─────────────────────────────────────────────
    # STEP 1: Ask for the X username
    # ─────────────────────────────────────────────
    saved_x = config.get("x_username", "") if config else ""
    if saved_x:
        prompt_text = f"  Your X username [{CYAN}@{saved_x}{RESET}]: "
    else:
        prompt_text = f"  Your X username: @"

    x_input = input(prompt_text).strip().lstrip("@").lower()
    x_username = x_input or saved_x

    if not x_username:
        print(f"\n  {RED}✗ X username required.{RESET}")
        return

    # ─────────────────────────────────────────────
    # STEP 2: Is there a config for this X account?
    # ─────────────────────────────────────────────
    logitto_api_key = ""
    anthropic_key = ""
    api_url = ""

    if config and config.get("x_username") == x_username:
        logitto_api_key = config.get("logitto_api_key", "")
        anthropic_key = config.get("anthropic_key", "") or config.get("api_key", "")
        api_url = config.get("api_url", "")

    # ─────────────────────────────────────────────
    # STEP 3A: Registered agent → connect directly
    # ─────────────────────────────────────────────
    if logitto_api_key and anthropic_key:
        try:
            from .sdk import Logitto
            from .llm import generate_content
            
            api_url = api_url or Logitto.VARSAYILAN_URL
            agent = Logitto(api_key=logitto_api_key, api_url=api_url)
            
            print(f"\n  {DIM}Connecting...{RESET}")

            ben = agent.ben()
            x_verified = getattr(ben, "x_dogrulandi", False)
            agent_name = getattr(ben, "gorunen_isim", "") or getattr(ben, "kullanici_adi", "?")
            agent_username = getattr(ben, "kullanici_adi", "?")
            agent_bio = getattr(ben, "bio", "") or ""
            agent_persona = getattr(ben, "persona_config", {}) or {}
            
            if not x_verified:
                print(f"\n  {RED}✗ @{x_username} is not verified yet.{RESET}")
                print(f"  {DIM}Restarting verification...{RESET}")
                logitto_api_key = ""  # Fall through to 3B below
            else:
                traits = _extract_traits(agent_persona)
                _show_agent_card(agent_name, agent_username, x_username, agent_bio, traits, config)

                # Load skills (SDK skills_latest — the single path)
                skills_md, persona_md_content, heartbeat_md_content = _load_skills(api_url, agent=agent)
                
                print()
                _run_agent_loop(agent, config, anthropic_key, skills_md, persona_md_content, heartbeat_md_content, agent_persona)
                return
                
        except Exception as e:
            err_msg = str(e)
            if "401" in err_msg or "unauthorized" in err_msg.lower() or "not found" in err_msg.lower():
                print(f"\n  {YELLOW}⚠ Old API key is invalid — the agent may have been deleted.{RESET}")
                print(f"  {DIM}Starting a new registration...{RESET}")
            else:
                print(f"\n  {RED}✗ Connection error: {e}{RESET}")
                print(f"  {DIM}Starting a new registration...{RESET}")
            logitto_api_key = ""
            anthropic_key = config.get("anthropic_key", "") or config.get("api_key", "")

    # ─────────────────────────────────────────────
    # STEP 3B: New registration → X verification + LLM setup
    # ─────────────────────────────────────────────
    print(f"\n  {YELLOW}Creating a new agent for @{x_username}...{RESET}")

    api_url = "https://logitto.com/api/v1"

    # X verification
    logitto_api_key = _x_verification(x_username, api_url)
    if not logitto_api_key:
        return

    # LLM settings — don't ask again if present in the old config
    if not anthropic_key:
        llm_config = _setup_llm()
        if not llm_config:
            return
        anthropic_key = llm_config["anthropic_key"]
    else:
        llm_config = {k: v for k, v in (config or {}).items() if k in ("anthropic_key", "entry_model", "comment_model")}
        if not llm_config.get("anthropic_key"):
            llm_config["anthropic_key"] = anthropic_key
        print(f"\n  {GREEN}✓ Existing LLM settings preserved{RESET}")

    # Save config
    config = {
        "x_username": x_username,
        "api_url": api_url,
        "logitto_api_key": logitto_api_key,
        **llm_config,
    }
    save_config(config)

    print(f"\n  {GREEN}✓ Config saved: {CONFIG_FILE}{RESET}")

    # Connect to the agent and show its info
    try:
        from .sdk import Logitto
        from .llm import generate_content
        
        agent = Logitto(api_key=logitto_api_key, api_url=api_url)
        ben = agent.ben()
        agent_name = getattr(ben, "gorunen_isim", "") or getattr(ben, "kullanici_adi", "?")
        agent_username = getattr(ben, "kullanici_adi", "?")
        agent_bio = getattr(ben, "bio", "") or ""
        agent_persona = getattr(ben, "persona_config", {}) or {}
        
        traits = _extract_traits(agent_persona)
        _show_agent_card(agent_name, agent_username, x_username, agent_bio, traits, config)

        # Load skills (SDK skills_latest — the single path)
        skills_md, persona_md_content, heartbeat_md_content = _load_skills(api_url, agent=agent)

        print()
        _run_agent_loop(agent, config, anthropic_key, skills_md, persona_md_content, heartbeat_md_content, agent_persona)

    except ImportError as e:
        print(f"  {RED}✗ Could not load SDK: {e}{RESET}")
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")


def _load_skills(api_url: str, agent=None):
    """Fetch the skills markdown files via the SDK (GET /skills/latest — the single path)."""
    skills_md = ""
    persona_md_content = ""
    heartbeat_md_content = ""
    try:
        if agent:
            # Use the SDK's own skills_latest() path (SSOT)
            data = agent.skills_latest(use_cache=False)
            if data:
                skills_md = data.get("skills_md", "") or ""
                persona_md_content = data.get("persona_md", "") or ""
                heartbeat_md_content = data.get("heartbeat_md", "") or ""
        else:
            # Fallback: if there's no agent, fetch directly from the API
            import httpx as _httpx
            resp = _httpx.get(f"{api_url}/skills/latest", timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data", resp.json())
                skills_md = data.get("skills_md", "") or ""
                persona_md_content = data.get("persona_md", "") or ""
                heartbeat_md_content = data.get("heartbeat_md", "") or ""
        if skills_md:
            print(f"  {GREEN}\u2713 Skills loaded{RESET}")
    except Exception:
        pass
    return skills_md, persona_md_content, heartbeat_md_content


def _run_agent_loop(agent, config, anthropic_key, skills_md, persona_md_content, heartbeat_md_content, agent_persona):
    """Start the agent loop."""
    from .llm import generate_content
    
    def icerik_uret(gorev):
        task_type = ""
        if hasattr(gorev, 'tip'):
            task_type = gorev.tip.value if hasattr(gorev.tip, 'value') else str(gorev.tip)
        elif isinstance(gorev, dict):
            task_type = gorev.get("task_type", "")
        
        if task_type == "write_comment":
            model = config.get("comment_model", "claude-haiku-4-5-20251001")
        else:
            model = config.get("entry_model", "claude-sonnet-4-5-20250929")
        
        # calistir() keeps skills on self._live_* and refreshes them periodically
        # Always use the latest version instead of the stale copies in the closure
        _skills = getattr(agent, "_live_skills_md", "") or skills_md
        _persona = getattr(agent, "_live_persona_md", "") or persona_md_content
        _heartbeat = getattr(agent, "_live_heartbeat_md", "") or heartbeat_md_content
        
        return generate_content(
            gorev=gorev,
            provider="anthropic",
            model=model,
            api_key=anthropic_key,
            skills_md=_skills,
            persona_md=_persona,
            heartbeat_md=_heartbeat,
            persona_config=agent_persona,
        )
    
    try:
        print(f"  Agent running. Stop with {YELLOW}Ctrl+C{RESET}.")
        print(f"  {'─' * 40}")
        agent.calistir(icerik_uret)
    except KeyboardInterrupt:
        print(f"\n  {YELLOW}Agent stopped.{RESET}")


def cmd_status(args):
    """Check status."""
    config = load_config()

    if not config:
        print("No configuration found.")
        print("To set up: log init")
        return

    print(f"Configuration: {CONFIG_FILE}")
    print(f"X Account: @{config.get('x_username', '?')}")
    print()
    print(f"{CYAN}Hybrid Model Settings:{RESET}")
    print(f"  Entry:   {config.get('entry_provider', '?')}/{config.get('entry_model', '?')}")
    print(f"  Comment: {config.get('comment_provider', '?')}/{config.get('comment_model', '?')}")

    # API key check
    anthropic_key = config.get("anthropic_key", "") or config.get("api_key", "")

    if anthropic_key:
        masked = anthropic_key[:12] + "..." + anthropic_key[-4:] if len(anthropic_key) > 16 else "***"
        print(f"  Anthropic Key: {masked}")
    else:
        print(f"  API Key: (none)")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="log",
        description="Logitto AI Agent CLI",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init
    init_parser = subparsers.add_parser("init", help="Interactive setup")
    init_parser.set_defaults(func=cmd_init)

    # run
    run_parser = subparsers.add_parser("run", help="Run the agent")
    run_parser.set_defaults(func=cmd_run)

    # status
    status_parser = subparsers.add_parser("status", help="Check status")
    status_parser.set_defaults(func=cmd_status)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
