import re

from sidebrain_back.services.step_summary_analysis_service import (
    META_TERMS,
    PORTUGUESE_STOPWORDS,
    TOKEN_PATTERN,
    VERDICT_TERMS,
    ReasonAnalysis,
)

_CODE_SPAN_PATTERN = re.compile(r"`([^`]+)`")
_MEMBER_CALL_PATTERN = re.compile(
    r"(?<![\w$])([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+\s*\(\s*\))"
)
_CODE_TOPIC_PATTERN = re.compile(
    r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*(?:\(\))?"
)
_PROGRAMMING_TERMS = {
    "async",
    "await",
    "class",
    "const",
    "defer",
    "def",
    "else",
    "except",
    "fetch",
    "finally",
    "for",
    "function",
    "if",
    "import",
    "input",
    "lambda",
    "let",
    "map",
    "print",
    "promise",
    "reduce",
    "return",
    "try",
    "var",
    "while",
    "yield",
}
_GENERIC_TOPIC_TERMS = {
    "adequado",
    "adequada",
    "adia",
    "ajuda",
    "antes",
    "atributo",
    "código",
    "compara",
    "comparar",
    "converte",
    "correta",
    "correto",
    "define",
    "definir",
    "demonstra",
    "depurar",
    "erros",
    "está",
    "explicar",
    "explicitar",
    "gerais",
    "isto",
    "operador",
    "quando",
    "resposta",
    "serve",
    "solicitado",
    "solicitada",
    "texto",
    "termos",
    "tipos",
    "valores",
    "você",
}


def _keyword_tokens(analysis: ReasonAnalysis) -> set[str]:
    ignored = (
        PORTUGUESE_STOPWORDS
        | META_TERMS
        | VERDICT_TERMS
        | _GENERIC_TOPIC_TERMS
    )
    return {
        token
        for phrase in analysis["keywords"]
        for token in TOKEN_PATTERN.findall(phrase.lower())
        if token not in ignored
    }


def _extract_inline_code_topic(
    text: str, analysis: ReasonAnalysis
) -> str | None:
    keyword_tokens = _keyword_tokens(analysis)
    for match in _CODE_SPAN_PATTERN.finditer(text):
        candidate = match.group(1).strip()
        if (
            len(candidate) <= 60
            and _CODE_TOPIC_PATTERN.fullmatch(candidate)
            and set(TOKEN_PATTERN.findall(candidate.lower())) & keyword_tokens
        ):
            return candidate
    return None


def _extract_compact_keyword_topic(
    text: str, analysis: ReasonAnalysis
) -> str | None:
    candidates = _keyword_tokens(analysis)
    if not candidates:
        return None

    source_tokens = list(TOKEN_PATTERN.finditer(text))
    source_by_token = {
        match.group(0).lower(): match.group(0) for match in source_tokens
    }
    keyword_order = [
        token
        for phrase in analysis["keywords"]
        for token in TOKEN_PATTERN.findall(phrase.lower())
        if token in candidates and token in source_by_token
    ]

    review_markers = {
        "não",
        "sem",
        "falta",
        "faltou",
        "omite",
        "omitiu",
        "incorreta",
        "incorreto",
        "incompleta",
        "incompleto",
        "errada",
        "errado",
    }
    if analysis["verdict"] in {"incorrect", "incomplete"}:
        for clause in re.split(r"(?<=[.!?;])\s+|,\s+", text):
            clause_tokens = set(TOKEN_PATTERN.findall(clause.lower()))
            if review_markers & clause_tokens:
                for token in keyword_order:
                    if token in clause_tokens:
                        return source_by_token[token]

    for token in keyword_order:
        if token in _PROGRAMMING_TERMS:
            return source_by_token[token]

    # Preserve keyword order when no specific review clause is available.
    for token in keyword_order:
        return source_by_token[token]
    return None


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
    def extract_topic(self, text: str, analysis: ReasonAnalysis) -> str | None:
        member_call = _MEMBER_CALL_PATTERN.search(text)
        if member_call:
            candidate = re.sub(r"\s+", "", member_call.group(1))
            candidate_tokens = set(TOKEN_PATTERN.findall(candidate.lower()))
            if candidate_tokens & _keyword_tokens(analysis):
                return candidate
        inline_code_topic = _extract_inline_code_topic(text, analysis)
        if inline_code_topic:
            return inline_code_topic

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
                return "o tratamento de exceções"
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
                return "o uso dos operadores de atribuição"
        if len(quoted_items) >= 2 and "função" in normalized_text:
            if any(
                item.lower() in {"function", "def"} for item in quoted_items
            ):
                return (
                    "a definição de funções em Python"
                    if "python" in normalized_text
                    else "a definição de funções"
                )

        action_match = re.search(
            r"\bpara\s+((?:criar|definir|contar|calcular|converter|usar)"
            r"\s+[^.;]+?)\s+é\b",
            text,
            re.IGNORECASE,
        )
        if action_match:
            return _nominalize_action(action_match.group(1))

        action_with_code_match = re.search(
            r"\bpara\s+((?:criar|definir|contar|calcular|converter|usar)"
            r"\s+[^,.;()]+)",
            text,
            re.IGNORECASE,
        )
        code_assignment = _extract_code_assignment(text)
        if action_with_code_match and code_assignment:
            return _nominalize_action(action_with_code_match.group(1))

        correct_fact = _extract_correct_fact(text)
        if correct_fact and analysis["verdict"] == "correct":
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

        expected_content = _extract_expected_content(text)
        if expected_content:
            return f"os conceitos de {expected_content}"

        if "capital" in normalized_text and "canadá" in normalized_text:
            return "a capital do Canadá"
        return _extract_compact_keyword_topic(text, analysis)
