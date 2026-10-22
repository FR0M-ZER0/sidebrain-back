from datetime import datetime, timedelta

import pytest

from sidebrain_back.repositories.badge_repository import BadgeRepository
from sidebrain_back.schemas.badge_schema import BadgeListParams


@pytest.fixture
async def badge_listing(
    db_session, user_factory, badge_factory, badge_progress_factory
):
    owner = await user_factory()
    other_user = await user_factory()
    created = datetime(2026, 1, 1)
    idle = await badge_factory(
        name="Primeira trilha",
        description="Complete onboarding",
        rarity="common",
        criteria="tracks_completed",
        criteria_value=1,
    )
    active = await badge_factory(
        name="Lições de Python",
        description="Complete aulas Python",
        rarity="rare",
        criteria="lessons_completed",
        criteria_value=10,
    )
    done = await badge_factory(
        name="Respostas corretas",
        description="Acerte quizzes",
        rarity="epic",
        criteria="right_answers",
        criteria_value=25,
    )
    foreign_only = await badge_factory(
        name="Streak global",
        description="Dias ativos",
        rarity="legendary",
        criteria="day_streak",
        criteria_value=7,
    )
    deleted = await badge_factory(name="Removido", deleted=True)
    for badge, day in ((idle, 1), (active, 2), (done, 3), (foreign_only, 4)):
        badge.bdg_updated_at = created + timedelta(days=day)
    active_progress = await badge_progress_factory(
        active, owner, status="in_progress"
    )
    done_progress = await badge_progress_factory(done, owner, status="done")
    foreign_progress = await badge_progress_factory(
        foreign_only, other_user, status="done"
    )
    active_progress.bpg_updated_at = created + timedelta(days=8)
    done_progress.bpg_updated_at = created + timedelta(days=5)
    foreign_progress.bpg_updated_at = created + timedelta(days=10)
    await db_session.flush()
    return owner, other_user, idle, active, done, foreign_only, deleted


@pytest.mark.anyio
async def test_list_badges_paginates_global_definitions_and_user_progress(
    db_session, badge_listing
):
    owner, _other, idle, active, done, _foreign, _deleted = badge_listing
    repository = BadgeRepository(db_session)

    first, total = await repository.list(owner.usr_id, 0, 2)
    assert total == 4
    assert [badge.bdg_id for badge in first] == [active.bdg_id, done.bdg_id]
    assert first[0].badge_progresses[0].bpg_status == "in_progress"
    assert first[1].badge_progresses[0].bpg_status == "done"

    second, total = await repository.list(owner.usr_id, 2, 2)
    assert total == 4
    assert [badge.bdg_id for badge in second] == [_foreign.bdg_id, idle.bdg_id]
    foreign_progress = next(
        badge for badge in second if badge.bdg_id == _foreign.bdg_id
    )
    assert foreign_progress.badge_progresses == []


@pytest.mark.anyio
async def test_list_badges_filters_combine_and_missing_progress_is_idle(
    db_session, badge_listing
):
    owner, _other, idle, active, done, foreign, deleted = badge_listing
    repository = BadgeRepository(db_session)

    cases = [
        (BadgeListParams(status="idle"), {idle.bdg_id, foreign.bdg_id}),
        (BadgeListParams(status="in_progress"), {active.bdg_id}),
        (BadgeListParams(status="done"), {done.bdg_id}),
        (
            BadgeListParams(
                status="done", rarity="epic", criteria="right_answers"
            ),
            {done.bdg_id},
        ),
        (BadgeListParams(rarity="common", q="  ONBOARDING  "), {idle.bdg_id}),
        (BadgeListParams(q="respostas"), {done.bdg_id}),
        (BadgeListParams(q="%"), set()),
    ]
    for params, expected in cases:
        badges, total = await repository.list(
            owner.usr_id,
            (params.page - 1) * params.page_size,
            params.page_size,
            **params.model_dump(exclude={"page", "page_size"}),
        )
        assert {badge.bdg_id for badge in badges} == expected
        assert total == len(expected)
    assert deleted.bdg_id not in {
        badge.bdg_id
        for badge in (await repository.list(owner.usr_id, 0, 100))[0]
    }


@pytest.mark.anyio
async def test_list_badges_supports_oldest_order_and_out_of_range_page(
    db_session, badge_listing
):
    owner, _other, idle, active, _done, _foreign, _deleted = badge_listing
    repository = BadgeRepository(db_session)
    oldest, total = await repository.list(
        owner.usr_id, 0, 1, status="idle", sort="oldest"
    )
    assert total == 2
    assert [badge.bdg_id for badge in oldest] == [idle.bdg_id]
    empty, total = await repository.list(owner.usr_id, 99, 1)
    assert empty == []
    assert total == 4
    recent, _ = await repository.list(owner.usr_id, 0, 1, status="in_progress")
    assert recent[0].bdg_id == active.bdg_id
