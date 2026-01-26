"""Email templates."""

from app.email.templates.password_reset import render_html as password_reset_html, render_text as password_reset_text

TEMPLATES = {
    "PASSWORD_RESET": {
        "text": password_reset_text,
        "html": password_reset_html,
    },
}


def render_template(template_key: str, vars: dict, format: str = "text") -> str:
    """
    Render email template.

    Args:
        template_key: Template identifier
        vars: Template variables
        format: "text" or "html"

    Returns:
        Rendered template string
    """
    if template_key not in TEMPLATES:
        raise ValueError(f"Unknown template key: {template_key}")

    template_func = TEMPLATES[template_key].get(format)
    if not template_func:
        raise ValueError(f"Template {template_key} does not support format {format}")

    return template_func(vars)
