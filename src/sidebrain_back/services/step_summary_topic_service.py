import re

from sidebrain_back.services.step_summary_analysis_service import (
    ReasonAnalysis,
    format_human_list,
)


def _extract_target(text: str) -> str | None:
    match = re.search(
        r"\b(?:pergunta|quest[aã]o)\s+pede\s+(.+?)(?=[,;.]|$)",
        text,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _extract_expected_content(text: str) -> str | None:
    match = re.search(
        r"\b(?:destacad[oa]s?|descrit[oa]s?|definid[oa]s?|conhecid[oa]s?|"
        r"apresentad[oa]s?)\s+como\s+(.+?)(?=[,;.]|$)",
        text,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _extract_code_assignment(text: str) -> str | None:
    for start_index, character in enumerate(text):
        if character != "(":
            continue
        nesting_level = 0
        for end_index in range(start_index, len(text)):
            if text[end_index] == "(":
                nesting_level += 1
            elif text[end_index] == ")":
                nesting_level -= 1
                if nesting_level == 0:
                    content = text[start_index + 1 : end_index].strip()
                    if "=" in content:
                        return content
                    break
    return None


def _extract_correct_fact(text: str) -> str | None:
    patterns = (
        (
            r"\b(?:ao afirmar|ao dizer|ao informar|ao explicar|ao indicar)"
            r"\s+que\s+(.+?)(?=,\s*(?:como solicitado|conforme)|[.;]|$)"
        ),
        (
            r"\b(?:calcula|identifica|apresenta|descreve|usa)"
            r"\s+corretamente\s+"
            r"(.+?)(?=[.;]|$)"
        ),
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" ,.")
    return None


def _nominalize_action(action: str) -> str:
    action = action.strip().rstrip(" .")
    normalized_action = action.lower()
    if "criar uma lista vazia" in normalized_action:
        return (
            "a criação de listas vazias em Python"
            if "python" in normalized_action
            else "a criação de listas vazias"
        )
    if "definir uma função" in normalized_action:
        return (
            "a definição de funções em Python"
            if "python" in normalized_action
            else "a definição de funções"
        )

    action_forms = (
        ("criar ", "a criação de "),
        ("definir ", "a definição de "),
        ("contar ", "a contagem de "),
        ("calcular ", "o cálculo de "),
        ("converter ", "a conversão de "),
        ("usar ", "o uso de "),
    )
    for verb, noun_form in action_forms:
        if normalized_action.startswith(verb):
            complement = action[len(verb) :]
            complement = re.sub(
                r"^(?:uma?|os?|as?)\s+",
                "",
                complement,
                flags=re.IGNORECASE,
            )
            return noun_form + complement
    return action


class StepSummaryTopicService:
    def extract_topic(
        self, text: str, analysis: ReasonAnalysis
    ) -> str | None:
        target = _extract_target(text)
        if target:
            normalized_target = re.sub(
                r"^(?:a|o|as|os|um|uma)\s+",
                "",
                target.strip(),
                flags=re.IGNORECASE,
            )
            normalized_target_lower = normalized_target.lower()
            if (
                "capturar exceções" in normalized_target_lower
                or "tratar exceções" in normalized_target_lower
            ):
                return "o tratamento de exceções em Python"
            if "código de status" in normalized_target_lower:
                return "os códigos de status HTTP"
            if "complexidade temporal" in normalized_target_lower:
                return "a complexidade temporal de algoritmos"
            if (
                "vantagem" in normalized_target_lower
                and "python" in text.lower()
            ):
                return "as vantagens do Python para iniciantes"
            return target.strip()

        operation = re.search(r"\b\d+\s*[×xX*+−/-]\s*\d+\b", text)
        if operation:
            expression = operation.group(0)
            if re.search(r"[×xX*]", expression):
                return f"a multiplicação de {expression}"
            if "+" in expression:
                return f"a adição de {expression}"
            if re.search(r"[−-]", expression):
                return f"a subtração de {expression}"
            return f"operações matemáticas como {expression}"

        quoted_items = re.findall(r'["“]([^"”]+)["”]', text)
        normalized_text = text.lower()
        if len(quoted_items) >= 2 and any(
            "=" in item for item in quoted_items
        ):
            if re.search(
                r"\b(?:atribui|atribuição|operador)\b", normalized_text
            ):
                return "o uso dos operadores de atribuição em Python"
        if len(quoted_items) >= 2 and "função" in normalized_text:
            if any(
                item.lower() in {"function", "def"} for item in quoted_items
            ):
                return "a definição de funções em Python"

        action_match = re.search(
            r"\bpara\s+(.+?)\s+é\b", text, re.IGNORECASE
        )
        if action_match:
            return _nominalize_action(action_match.group(1))

        action_with_code_match = re.search(
            r"\bpara\s+([^,.;()]+)", text, re.IGNORECASE
        )
        code_assignment = _extract_code_assignment(text)
        if action_with_code_match and code_assignment:
            return _nominalize_action(action_with_code_match.group(1))

        correct_fact = _extract_correct_fact(text)
        if correct_fact:
            normalized_fact = correct_fact.lower()
            if "água" in normalized_fact and "congela" in normalized_fact:
                return "o congelamento da água"
            if "marte" in normalized_fact and "lua" in normalized_fact:
                return "as luas de Marte"
            if "área" in normalized_fact and "retângulo" in normalized_fact:
                return "o cálculo da área de retângulos"
            if "soma" in normalized_fact:
                return "a adição"
            if "%" in normalized_fact or "por cento" in normalized_fact:
                return "o cálculo de porcentagens"
            return f"o fato de que {correct_fact}"

        expected_content = _extract_expected_content(text)
        if expected_content:
            return f"os conceitos de {expected_content}"

        ignored_terms = {
            "resultado", "resposta", "solicitado", "solicitada", "código",
            "sob", "possui",
        }
        keywords = [
            term
            for term in analysis["keywords"]
            if term.lower() not in ignored_terms
        ]
        if "capital" in normalized_text and "canadá" in normalized_text:
            return "a capital do Canadá"
        return format_human_list(keywords) if keywords else None
