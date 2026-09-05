import re

from localflavor.br.models import BRCPFField

NON_DIGITS = re.compile(r"\D")


def only_digits(value):
    return NON_DIGITS.sub("", value) if value else value


class DigitsBRCPFField(BRCPFField):
    def to_python(self, value):
        return only_digits(super().to_python(value))

    def get_prep_value(self, value):
        return only_digits(super().get_prep_value(value))
