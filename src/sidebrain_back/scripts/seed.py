import asyncio
import logging
from uuid import uuid4

from sqlalchemy import select

from sidebrain_back.core.database import async_session
from sidebrain_back.enums.badge_criteria_enum import BadgeCriteriaEnum
from sidebrain_back.enums.badge_rarity_enum import BadgeRarityEnum
from sidebrain_back.enums.mission_criteria_enum import MissionCriteriaEnum
from sidebrain_back.enums.mission_difficulty_enum import MissionDifficultyEnum
from sidebrain_back.enums.step_level_enum import StepLevelEnum
from sidebrain_back.enums.step_status_enum import StepStatusEnum
from sidebrain_back.models import Badge, Mission, Step, Track, User

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def seed_database() -> None:
    """Popula o banco com dados pilotos de trilha, passos e gamificação."""
    logger.info("Iniciando processo de seed no banco de dados...")

    async with async_session() as session:
        async with session.begin():
            # 1. Garante a existência do usuário piloto
            user_stmt = select(User).where(
                User.usr_email == "pilot@sidebrain.ai"
            )
            result = await session.execute(user_stmt)
            pilot_user = result.scalars().first()

            if not pilot_user:
                logger.info("Criando usuário piloto...")
                pilot_user = User(
                    usr_id=uuid4(),
                    usr_email="pilot@sidebrain.ai",
                    usr_name="Sidebrain Pilot User",
                    usr_password_hash=(
                        "$2b$12$K8y5k2Y2.D2vL0n1v4j8uuK5Yx5wYp4k6p"
                        "7g8s9t0u1v2w3x4y5z6"
                    ),
                    usr_is_deleted=False,
                )
                session.add(pilot_user)
                await session.flush()
                logger.info("Usuário piloto criado: %s", pilot_user.usr_id)
            else:
                logger.info("Usuário piloto existente: %s", pilot_user.usr_id)

            # 2. Cria trilha de aprendizagem piloto
            track_title = (
                "Desenvolvimento Web Full-Stack Moderno (Python & React)"
            )
            track_stmt = select(Track).where(
                Track.trk_title == track_title,
                Track.trk_user_id == pilot_user.usr_id,
            )
            result = await session.execute(track_stmt)
            pilot_track = result.scalars().first()

            if not pilot_track:
                logger.info("Criando trilha piloto...")
                pilot_track = Track(
                    trk_id=uuid4(),
                    trk_user_id=pilot_user.usr_id,
                    trk_title=track_title,
                    trk_description=(
                        "Trilha prática cobrindo desenvolvimento backend "
                        "com FastAPI, modelagem com PostgreSQL/SQLAlchemy, "
                        "frontend com React e automação CI/CD."
                    ),
                    trk_is_deleted=False,
                )
                session.add(pilot_track)
                await session.flush()
                logger.info(
                    "Trilha piloto criada com ID: %s", pilot_track.trk_id
                )

                # 3. Passos associados (Step) com níveis e status
                steps_data = [
                    (
                        "1. Fundamentos de Backend & APIs com FastAPI",
                        StepLevelEnum.BEGINNER,
                        StepStatusEnum.DONE,
                    ),
                    (
                        "2. Modelagem Relacional e Migrações com SQLAlchemy",
                        StepLevelEnum.INTERMEDIATE,
                        StepStatusEnum.IN_PROGRESS,
                    ),
                    (
                        "3. Conteinerização, Pipeline CI/CD e Deploy OCI",
                        StepLevelEnum.ADVANCED,
                        StepStatusEnum.IDLE,
                    ),
                    (
                        "4. Escalabilidade, Cache e Filas Assíncronas",
                        StepLevelEnum.PRO,
                        StepStatusEnum.IDLE,
                    ),
                ]

                created_steps = []
                for title, level, status in steps_data:
                    step = Step(
                        stp_id=uuid4(),
                        stp_track_id=pilot_track.trk_id,
                        stp_title=title,
                        stp_level=level,
                        stp_status=status,
                        stp_is_deleted=False,
                    )
                    session.add(step)
                    created_steps.append(step)

                await session.flush()
                logger.info(
                    "%d passos criados para a trilha.", len(created_steps)
                )

                # 4. Missões gamificadas associadas aos passos
                missions_data = [
                    (
                        created_steps[0].stp_id,
                        "Primeira API Operacional",
                        MissionDifficultyEnum.EASY,
                        150,
                        MissionCriteriaEnum.NUMBER_OF_LESSONS_COMPLETED,
                        3,
                    ),
                    (
                        created_steps[1].stp_id,
                        "Mestre das Migrações e Schemas",
                        MissionDifficultyEnum.MEDIUM,
                        300,
                        MissionCriteriaEnum.COMPLETE_A_STEP,
                        1,
                    ),
                    (
                        created_steps[2].stp_id,
                        "Capitão da Nuvem e DevOps",
                        MissionDifficultyEnum.HARD,
                        500,
                        MissionCriteriaEnum.COMPLETE_A_STEP,
                        1,
                    ),
                    (
                        created_steps[3].stp_id,
                        "Arquiteto de Sistemas Distribuídos",
                        MissionDifficultyEnum.VERY_HARD,
                        1000,
                        MissionCriteriaEnum.COMPLETE_A_TRACK,
                        1,
                    ),
                ]

                for (
                    stp_id,
                    msn_title,
                    difficulty,
                    xp,
                    criteria,
                    val,
                ) in missions_data:
                    mission = Mission(
                        msn_id=uuid4(),
                        msn_step_id=stp_id,
                        msn_title=msn_title,
                        msn_difficulty=difficulty,
                        msn_xp_reward=xp,
                        msn_criteria=criteria,
                        msn_criteria_value=val,
                        msn_is_deleted=False,
                    )
                    session.add(mission)

                await session.flush()
                logger.info(
                    "%d missões gamificadas criadas.", len(missions_data)
                )
            else:
                logger.info(
                    "Trilha piloto existente: %s, pulando criação.",
                    pilot_track.trk_id,
                )

            # 5. Emblemas (Badges) com raridades e critérios
            badges_data = [
                (
                    "Pioneiro Sidebrain",
                    "Criou sua primeira trilha de conhecimento na plataforma.",
                    BadgeRarityEnum.COMMON,
                    BadgeCriteriaEnum.TRACKS_CREATED,
                    1,
                ),
                (
                    "Explorador de Trilhas",
                    "Finalizou com êxito uma trilha inteira de aprendizado.",
                    BadgeRarityEnum.RARE,
                    BadgeCriteriaEnum.TRACKS_COMPLETED,
                    1,
                ),
                (
                    "Mente Brilhante",
                    "Acumulou mais de 1000 XP completando tarefas e lições.",
                    BadgeRarityEnum.EPIC,
                    BadgeCriteriaEnum.XP_GAINED,
                    1000,
                ),
                (
                    "Lenda da Constância",
                    "Manteve uma sequência diária ininterrupta de 7 dias.",
                    BadgeRarityEnum.LEGENDARY,
                    BadgeCriteriaEnum.DAY_STREAK,
                    7,
                ),
            ]

            created_badges_count = 0
            for name, desc, rarity, crit, crit_val in badges_data:
                b_stmt = select(Badge).where(Badge.bdg_name == name)
                res = await session.execute(b_stmt)
                existing_badge = res.scalars().first()
                if not existing_badge:
                    badge = Badge(
                        bdg_id=uuid4(),
                        bdg_name=name,
                        bdg_description=desc,
                        bdg_rarity=rarity,
                        bdg_criteria=crit,
                        bdg_criteria_value=crit_val,
                        bdg_is_deleted=False,
                    )
                    session.add(badge)
                    created_badges_count += 1

            await session.flush()
            logger.info("%d novos emblemas cadastrados.", created_badges_count)

    logger.info("✅ Processo de seed concluído com sucesso absoluto!")


def main() -> None:
    asyncio.run(seed_database())


if __name__ == "__main__":
    main()
