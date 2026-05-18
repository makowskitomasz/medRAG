from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render(template_name: str, override: str | None = None, **context: object) -> str:
    """Render a prompt template.

    If *override* is provided (a Jinja2 source string stored in the project's
    prompt_overrides), it is rendered instead of the file-based template.
    """
    tmpl = _env.from_string(override) if override is not None else _env.get_template(template_name)
    return tmpl.render(**context).strip()
