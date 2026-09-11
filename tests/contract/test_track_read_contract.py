from uuid import UUID

from sidebrain_back.schemas.track_schema import TrackResponse


def test_track_id_is_public_uuid_field():
    fields = TrackResponse.model_fields
    assert "id" in fields
    assert fields["id"].validation_alias == "trk_id"
    assert UUID("00000000-0000-0000-0000-000000000001")
