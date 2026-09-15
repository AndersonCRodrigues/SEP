import re

from localflavor.br.models import BRCPFField

from .validators import NO_NUMBER

NON_DIGITS = re.compile(r"\D")
PHONE_CHARACTERS = re.compile(r"^[0-9\s().+-]+$")
CEP_CHARACTERS = re.compile(r"^[0-9\s.-]+$")


def only_digits(value):
    return NON_DIGITS.sub("", value) if value else value


def collapse_spaces(value):
    return " ".join(value.split()) if value else value


def normalize_phone(value):
    if value and PHONE_CHARACTERS.match(value):
        return only_digits(value)
    return value


def format_cep(value):
    digits = only_digits(value)
    if value and CEP_CHARACTERS.match(value) and len(digits) == 8:
        return f"{digits[:5]}-{digits[5:]}"
    return value


def normalize_address_number(value):
    cleaned = collapse_spaces(value)
    if cleaned and cleaned.replace(" ", "").upper() in ("S/N", "SN"):
        return NO_NUMBER
    return cleaned


class DigitsBRCPFField(BRCPFField):
    def to_python(self, value):
        return only_digits(super().to_python(value))

    def get_prep_value(self, value):
        return only_digits(super().get_prep_value(value))
