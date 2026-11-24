from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator

NO_NUMBER = "S/N"

PERCENT_RANGE = (0, 100)


PERCENT_VALIDATORS = (
    MinValueValidator(PERCENT_RANGE[0]),
    MaxValueValidator(PERCENT_RANGE[1]),
)

validate_letters = RegexValidator(
    r"^[^\W\d_]+(?:[ '’-][^\W\d_]+)*$",
    "Use somente letras.",
    code="invalid_letters",
)

validate_digits = RegexValidator(
    r"^[0-9]+$",
    "Use somente números.",
    code="invalid_digits",
)

validate_phone = RegexValidator(
    r"^[0-9]{10,11}$",
    "Informe o telefone com DDD, somente números, com 10 ou 11 dígitos.",
    code="invalid_phone",
)

validate_address_number = RegexValidator(
    r"^(?:[0-9]+|S/N)$",
    "Use somente números ou marque sem número.",
    code="invalid_address_number",
)
