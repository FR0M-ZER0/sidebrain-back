from sidebrain_back.schemas.pagination_schema import PaginationParams


def test_pagination_defaults_and_limits():
    params = PaginationParams()
    assert params.page == 1
    assert params.page_size == 20

    assert PaginationParams(page=2, page_size=100).page_size == 100

    for payload in ({"page": 0}, {"page_size": 0}, {"page_size": 101}):
        try:
            PaginationParams.model_validate(payload)
        except ValueError:
            continue
        raise AssertionError("parâmetro inválido aceito")
