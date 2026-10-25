import re
from typing import TypeAlias

import numpy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PORTUGUESE_STOPWORDS = {
    "a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "do",
    "da", "dos", "das", "em", "no", "na", "nos", "nas", "por",
    "para", "com", "sem", "e", "ou", "mas", "que", "se", "ao",
    "aos", "é", "são", "foi", "ser", "ter", "como", "mais", "não",
    "também", "isso", "essa", "esse", "esses", "essas", "seu", "sua",
    "pela", "pelo", "porém", "pois", "já", "só", "muito", "está",
    "estão", "pede", "pelos", "pelas", "num", "numa", "entre", "sobre",
    "onde", "qual", "quais", "à", "às",
}

NEGATION_TOKENS = {"não", "sem", "nunca", "nem", "jamais"}

META_TERMS = {
    "resposta", "pergunta", "aponta", "menciona", "fornece", "atendendo",
    "atende", "plenamente", "exatamente", "ficando", "geralmente",
    "destacada", "aspectos", "apresenta", "mostra", "explica", "principal",
    "indica", "cita", "diz", "corretamente", "apenas", "somente", "sendo",
    "feito", "feita", "descrita", "descrito",
}
META_TERMS.update(NEGATION_TOKENS)

VERDICT_PROTOTYPES = {
    "correct": (
        "correta correto certa certo adequada atendendo plenamente exatamente"
    ),
    "incorrect": (
        "incorreta incorreto errada errado equivocada falsa inadequada"
    ),
    "incomplete": (
        "incompleta incompleto parcial menciona omite omitiu falta faltou "
        "ficando"
    ),
}

TOKEN_PATTERN = re.compile(r"[a-záàâãéêíóôõúüç]+")
VERDICT_TERMS = {
    term
    for prototype in VERDICT_PROTOTYPES.values()
    for term in prototype.split()
}
CLAUSE_PATTERN = re.compile(r'[,.;:()!?"“”]')


ReasonAnalysis: TypeAlias = dict[str, str | list[str] | None]


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _analyze_tokens(text: str) -> list[str]:
    return [
        token
        for token in _tokenize(text)
        if (token not in PORTUGUESE_STOPWORDS or token in NEGATION_TOKENS)
        and len(token) >= 2
    ]


def _document_weights(tfidf_row, terms) -> dict[str, float]:
    coordinates = tfidf_row.tocoo()
    return {
        terms[column]: float(weight)
        for column, weight in zip(
            coordinates.col, coordinates.data, strict=True
        )
    }


def _terms_after_expected_content_marker(text: str) -> set[str]:
    participles = {"feito", "feita", "descrito", "descrita", "usado", "usada"}
    found_terms = set()
    for clause in CLAUSE_PATTERN.split(text):
        tokens = _tokenize(clause)
        for index, token in enumerate(tokens):
            is_marker = token == "como" or (
                token == "com"
                and index > 0
                and tokens[index - 1] in participles
            )
            if is_marker:
                found_terms.update(
                    _analyze_tokens(" ".join(tokens[index + 1 :]))
                )
                break
    return found_terms


def _extract_keywords(
    text: str, weights: dict[str, float], count: int
) -> list[str]:
    candidates = {
        term: weight
        for term, weight in weights.items()
        if term not in META_TERMS and term not in VERDICT_TERMS
    }
    preferred_terms = _terms_after_expected_content_marker(text) & set(
        candidates
    )
    if preferred_terms:
        candidates = {
            term: candidates[term] for term in preferred_terms
        }

    token_order = {
        token: index for index, token in enumerate(_tokenize(text))
    }
    top_terms = sorted(
        candidates,
        key=lambda term: (-candidates[term], token_order.get(term, 0)),
    )[:count]
    selected_terms = set(top_terms)

    phrases, used_terms = [], set()
    for clause in CLAUSE_PATTERN.split(text):
        current_phrase, pending_connectors = [], []

        def flush_phrase(
            current_phrase=current_phrase,
            pending_connectors=pending_connectors,
        ) -> None:
            if current_phrase:
                phrases.append(" ".join(current_phrase))
                used_terms.update(
                    term for term in current_phrase if term in selected_terms
                )
            current_phrase.clear()
            pending_connectors.clear()

        for token in _tokenize(clause):
            if token in selected_terms and token not in used_terms:
                if current_phrase:
                    current_phrase.extend(pending_connectors)
                current_phrase.append(token)
                pending_connectors.clear()
            elif (
                token in PORTUGUESE_STOPWORDS
                and current_phrase
                and len(pending_connectors) < 2
            ):
                pending_connectors.append(token)
            else:
                flush_phrase()
        flush_phrase()
    return phrases


def format_human_list(items: list[str]) -> str:
    if not items:
        return "(sem palavras-chave)"
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " e " + items[-1]


class StepSummaryAnalysisService:
    def analyze_reasons(self, texts: list[str]) -> list[ReasonAnalysis]:
        if not texts:
            return []

        vectorizer = TfidfVectorizer(
            analyzer=_analyze_tokens,
            sublinear_tf=True,
        )
        matrix = vectorizer.fit_transform(
            list(texts) + list(VERDICT_PROTOTYPES.values())
        )
        reason_vectors = matrix[: len(texts)]
        prototype_vectors = matrix[len(texts) :]
        similarities = cosine_similarity(reason_vectors, prototype_vectors)
        verdict_labels = list(VERDICT_PROTOTYPES)
        terms = vectorizer.get_feature_names_out()

        analyses = []
        for index, text in enumerate(texts):
            verdict = (
                verdict_labels[int(numpy.argmax(similarities[index]))]
                if similarities[index].max() > 0
                else None
            )
            weights = _document_weights(reason_vectors[index], terms)
            keywords = _extract_keywords(text, weights, count=3)
            analyses.append({"verdict": verdict, "keywords": keywords})
        return analyses
