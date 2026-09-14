from django import template
from django.template.loader import render_to_string

register = template.Library()


def _build_slot_tag(tag_name, template_path):

    class SlotNode(template.Node):
        def __init__(self, nodelist, kwargs):
            self.nodelist = nodelist
            self.kwargs = kwargs

        def render(self, context):
            resolved = {
                key: value.resolve(context)
                for key, value in self.kwargs.items()
            }
            body = self.nodelist.render(context)
            return render_to_string(template_path, {**resolved, "body": body})

    def compile_tag(parser, token):
        bits = token.split_contents()[1:]
        kwargs = {}
        for bit in bits:
            key, value = bit.split("=", 1)
            kwargs[key] = parser.compile_filter(value)
        nodelist = parser.parse((f"end{tag_name}",))
        parser.delete_first_token()
        return SlotNode(nodelist, kwargs)

    return compile_tag


register.tag("card", _build_slot_tag("card", "components/_card.html"))
register.tag("section", _build_slot_tag("section", "components/_section.html"))
register.tag("modal", _build_slot_tag("modal", "components/_modal.html"))