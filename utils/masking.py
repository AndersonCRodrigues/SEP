import re


def mask_cpf(cpf: str) -> str:
    digits = re.sub(r"\D", "", cpf or "")
    if len(digits) != 11:
        return "***.***.***-**"
    return f"***.***.{digits[6:9]}-{digits[9:]}"


def _clean_text(obj, attr: str) -> str:
    return (getattr(obj, attr, "") or "").strip()


def student_patient_label(patient) -> str:
    parts = []
    first_name = _clean_text(patient, "first_name")
    if first_name:
        parts.append(first_name)

    age = getattr(patient, "current_age", None)
    if age is not None:
        unit = "ano" if age == 1 else "anos"
        parts.append(f"{age} {unit}")

    gender = _clean_text(patient, "gender_identity")
    if gender:
        parts.append(gender)

    return " · ".join(parts) or "Paciente"


def student_patient_initials(patient) -> str:
    first_name = _clean_text(patient, "first_name")
    return first_name[:2].upper() if first_name else "PA"
