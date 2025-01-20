import random

from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def last_msg(messages):
    last = ''
    for msg in messages:
        last = msg
    return last


@register.filter
def percent(part, whole):
    try:
        part = int(part)
        whole = int(whole)
        if whole == 0:
            return 0
        return int((part / whole) * 100)
    except (ValueError, TypeError):
        return 0


@register.filter
def variants(exres):
    options = [exres.test.option1, exres.test.option2, exres.test.option3, exres.test.correct_option]
    random.shuffle(options)

    vars = ''
    for option in options:
        index = options.index(option) + 1
        test_id = exres.test.id
        vars += f"""
            <div class="col-sm-12">
                <div class="card" style="margin-bottom: 1%;">
                    <div class="media p-20">
                        <div class="radio radio-secondary me-3">
                            <input id="input_{index}_{test_id}" type="radio" name="question_{test_id}" value="{index}{option}">
                            <label for="input_{index}_{test_id}" style="margin: 0px 0px 14px 0px;"></label> 
                        </div>
                        <div class="media-body">
                            <label for="input_{index}_{test_id}" style="font-size: 16px;">{option}</label>
                        </div>
                    </div>
                </div>
            </div>
        """

    html_content = f"""
        <div class="row">
            {vars}
        </div>
    """

    return format_html(html_content)
