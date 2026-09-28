from django.db.models import Q, Value
from django.db.models.functions import Concat

from .fields import collapse_spaces


def full_name_lookup(queryset, search, *relations):
    relations = relations or ("",)
    names = {
        f"full_name_{index}": Concat(
            f"{relation}first_name", Value(" "), f"{relation}last_name"
        )
        for index, relation in enumerate(relations)
    }

    term = collapse_spaces(search)
    match = Q()
    for alias in names:
        match |= Q(**{f"{alias}__icontains": term})

    return queryset.annotate(**names), match
