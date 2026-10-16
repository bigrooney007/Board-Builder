"""Present resource content without exposing the generation schema to readers."""
import re

# These describe a container, not a meaningful section of an organization's work.
CONTAINERS = {"title", "headline", "heading", "body", "content", "text", "sections", "section", "paragraphs"}
PREFIX = re.compile(r"^(?:title|headline|heading|body|content|text)\s*:\s*", re.I)
CONTAINER_LINE = re.compile(r"^(?:sections?|paragraphs|version\s*\d+)\s*:?\s*$", re.I)


def clean_resource_text(text: str) -> str:
    """Remove standalone drafting labels, keeping the actual words and paragraphs.

    Only match whole structural labels at the start of a line. Ordinary prose,
    legal headings such as 'Title to Property', and real email subjects survive.
    """
    lines = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if CONTAINER_LINE.fullmatch(line):
            continue
        while PREFIX.match(line):
            line = PREFIX.sub("", line).strip()
        # A bare label introduces no reader-facing content.
        if line.casefold() in CONTAINERS:
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def resource_lines(value, indent=0):
    """Flatten structured resources while retaining meaningful topic labels."""
    lines = []
    if isinstance(value, dict):
        for key, item in value.items():
            if item is None or item == "" or item == [] or item == {}:
                continue
            structural = str(key).lower() in CONTAINERS
            if isinstance(item, (dict, list)):
                if not structural:
                    lines.extend([str(key).replace("_", " ").title(), ""])
                lines.extend(resource_lines(item, indent + 1))
            elif structural:
                lines.extend([clean_resource_text(str(item)), ""])
            else:
                lines.extend([f"{str(key).replace('_', ' ').title()}: {clean_resource_text(str(item))}", ""])
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.extend(resource_lines(item, indent))
            elif item is not None:
                lines.append(f"- {clean_resource_text(str(item))}")
        lines.append("")
    elif value is not None:
        lines.append(clean_resource_text(str(value)))
    return lines
