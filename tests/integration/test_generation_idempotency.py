from sidebrain_back.models.track_model import Track


def test_generation_request_id_is_unique_on_track_model():
    constraint_names = {
        constraint.name for constraint in Track.__table__.constraints
    }

    assert any(
        constraint_name and "generation_request" in constraint_name
        for constraint_name in constraint_names
    )
