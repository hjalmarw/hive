"""Agent model and name generation"""
import random
import secrets
from typing import Optional, Set


# Tech/Nature themed adjectives (200+)
ADJECTIVES = [
    "quantum", "cyber", "neural", "swift", "silent", "crimson", "silver", "golden",
    "azure", "emerald", "jade", "obsidian", "crystal", "stellar", "lunar", "solar",
    "cosmic", "atomic", "electric", "magnetic", "sonic", "photon", "plasma", "fusion",
    "blazing", "frozen", "storm", "thunder", "lightning", "shadow", "ghost", "phantom",
    "stealth", "rapid", "turbo", "hyper", "ultra", "mega", "giga", "tera",
    "alpha", "beta", "gamma", "delta", "omega", "prime", "apex", "zenith",
    "nexus", "vertex", "vortex", "matrix", "vector", "tensor", "scalar", "quasar",
    "nebula", "pulsar", "comet", "meteor", "asteroid", "eclipse", "aurora", "corona",
    "mystic", "arcane", "ethereal", "astral", "celestial", "divine", "sacred", "ancient",
    "eternal", "infinite", "limitless", "boundless", "endless", "timeless", "ageless", "deathless",
    "fierce", "savage", "wild", "feral", "primal", "brutal", "ruthless", "merciless",
    "gentle", "calm", "serene", "peaceful", "tranquil", "quiet", "still", "silent",
    "bright", "radiant", "brilliant", "luminous", "glowing", "shining", "gleaming", "sparkling",
    "dark", "shadowy", "murky", "dim", "dusky", "gloomy", "somber", "bleak",
    "fierce", "bold", "brave", "valiant", "heroic", "noble", "proud", "majestic",
    "wise", "sage", "clever", "cunning", "crafty", "shrewd", "astute", "keen",
    "swift", "agile", "nimble", "quick", "fleet", "rapid", "hasty", "speedy",
    "strong", "mighty", "powerful", "robust", "sturdy", "tough", "hardy", "resilient",
    "sleek", "smooth", "polished", "refined", "elegant", "graceful", "flowing", "fluid",
    "sharp", "keen", "acute", "piercing", "cutting", "incisive", "pointed", "edged",
    "amber", "ruby", "sapphire", "topaz", "garnet", "pearl", "opal", "onyx",
    "cobalt", "indigo", "violet", "magenta", "cyan", "teal", "jade", "olive",
    "crimson", "scarlet", "vermillion", "burgundy", "maroon", "rust", "copper", "bronze",
    "iron", "steel", "titanium", "platinum", "chrome", "nickel", "zinc", "mercury",
    "arctic", "alpine", "polar", "glacial", "tundra", "boreal", "tropical", "desert"
]

# Tech concepts, animals, and elements (200+)
NOUNS = [
    "falcon", "hawk", "eagle", "raven", "crow", "owl", "phoenix", "dragon",
    "wolf", "fox", "lynx", "panther", "leopard", "jaguar", "cheetah", "cougar",
    "tiger", "lion", "bear", "shark", "orca", "dolphin", "whale", "octopus",
    "spider", "mantis", "scorpion", "viper", "cobra", "python", "anaconda", "mamba",
    "cipher", "code", "algorithm", "protocol", "system", "network", "circuit", "processor",
    "kernel", "daemon", "thread", "process", "socket", "buffer", "cache", "registry",
    "compiler", "parser", "lexer", "interpreter", "debugger", "profiler", "tracer", "monitor",
    "firewall", "gateway", "router", "switch", "hub", "node", "server", "client",
    "daemon", "agent", "proxy", "broker", "handler", "manager", "controller", "director",
    "sentinel", "guardian", "watcher", "observer", "listener", "scanner", "analyzer", "detector",
    "forge", "anvil", "hammer", "blade", "sword", "lance", "spear", "arrow",
    "shield", "armor", "helm", "gauntlet", "greaves", "plate", "mail", "chain",
    "crystal", "prism", "lens", "mirror", "beacon", "torch", "flame", "spark",
    "storm", "tempest", "cyclone", "tornado", "typhoon", "hurricane", "blizzard", "avalanche",
    "thunder", "lightning", "bolt", "flash", "pulse", "wave", "surge", "spike",
    "nexus", "vertex", "apex", "zenith", "peak", "summit", "crest", "crown",
    "forge", "foundry", "reactor", "generator", "engine", "turbine", "dynamo", "motor",
    "spectrum", "array", "matrix", "grid", "mesh", "lattice", "framework", "scaffold",
    "cipher", "enigma", "puzzle", "riddle", "mystery", "secret", "paradox", "anomaly",
    "cosmos", "galaxy", "nebula", "quasar", "pulsar", "nova", "supernova", "blackhole",
    "photon", "electron", "neutron", "proton", "quark", "boson", "lepton", "hadron",
    "atom", "molecule", "particle", "ion", "isotope", "element", "compound", "crystal",
    "vector", "tensor", "scalar", "matrix", "array", "sequence", "series", "pattern",
    "catalyst", "reactor", "chamber", "vessel", "container", "capsule", "pod", "shell",
    "sentinel", "vanguard", "bastion", "bulwark", "fortress", "citadel", "stronghold", "rampart"
]


def generate_agent_name() -> str:
    """
    Generate a unique agent name in format: {adjective}-{noun}-{4-digit-hex}

    Examples:
        - silver-falcon-a3f2
        - quantum-cipher-7b1e
        - crimson-raven-d4c9

    Returns:
        str: Generated agent name
    """
    adjective = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    hex_suffix = secrets.token_hex(2)  # 4 hex digits

    return f"{adjective}-{noun}-{hex_suffix}"


def generate_unique_agent_name(used_names: Set[str], max_attempts: int = 100) -> Optional[str]:
    """
    Generate a unique agent name that doesn't exist in the used names set.

    Args:
        used_names: Set of already used agent names
        max_attempts: Maximum number of generation attempts

    Returns:
        str: Unique agent name or None if failed after max_attempts
    """
    for _ in range(max_attempts):
        name = generate_agent_name()
        if name not in used_names:
            return name

    return None


def validate_agent_name(name: str) -> bool:
    """
    Validate agent name format: {adjective}-{noun}-{4-hex-digits}

    Args:
        name: Agent name to validate

    Returns:
        bool: True if valid format
    """
    parts = name.split("-")
    if len(parts) != 3:
        return False

    adjective, noun, hex_suffix = parts

    # Check if adjective and noun are in our lists
    if adjective not in ADJECTIVES or noun not in NOUNS:
        return False

    # Check if hex suffix is 4 hex digits
    if len(hex_suffix) != 4:
        return False

    try:
        int(hex_suffix, 16)
        return True
    except ValueError:
        return False
