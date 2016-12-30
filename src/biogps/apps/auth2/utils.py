import re

from django.template import Context, RequestContext, TemplateDoesNotExist
from django.template.loader import get_template
from django.shortcuts import render_to_response
from django.conf import settings
from django.core.mail import EmailMultiAlternatives


# taken from django-account to keep previous site functionality
def render_to(template_path):
    """
    Decorate the django view.

    Wrap view that return dict of variables, that should be used for
    rendering the template.
    """

    def decorator(func):
        def wrapper(request, *args, **kwargs):
            output = func(request, *args, **kwargs)
            if not isinstance(output, dict):
                return output
            ctx = RequestContext(request)
            return render_to_response(template_path, output,
                                      context_instance=ctx)
        return wrapper
    return decorator


def parse_template(template_path, **kwargs):
    """
    Load and render template.

    First line of template should contain the subject of email.
    Return tuple with subject and content.
    """

    template = get_template(template_path)
    context = Context(kwargs)
    re_empty_lines = re.compile(r'^(\r?\n)+|(\r?\n)+$')
    data = template.render(context)
    return re_empty_lines.sub('', data)


def email_template(rcpt, template_path, **kwargs):
    """
    Load, render and email template.

    Template_path should not contain .txt or .html suffixes - they
    will be appended automatically.

    **kwargs may contain variables for template rendering.
    """

    from_email = settings.DEFAULT_FROM_EMAIL

    subject = parse_template('%s_subject.txt' % template_path, **kwargs)
    text_content = parse_template('%s_body.txt' % template_path, **kwargs)

    try:
        html_content = parse_template('%s_body.html' % template_path, **kwargs)
    except TemplateDoesNotExist:
        html_content = None

    msg = EmailMultiAlternatives(subject, text_content, from_email, [rcpt])
    if html_content:
        msg.attach_alternative(html_content, "text/html")

    return bool(msg.send(fail_silently=True))
