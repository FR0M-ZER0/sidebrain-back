"""
Script de seed do banco de dados.

Popula as tabelas criadas pela migration inicial (16fd0aac0bc2) com
dados de exemplo, respeitando a ordem de dependência das foreign
keys:

    badge, user
    -> badge_progress, day_streak, login, track
    -> step
    -> lesson, mission
    -> feedback, lesson_file, mission_progress, quiz
    -> answer

Uso:
    python seed.py

Configuração:
    Ajuste a variável DATABASE_URL abaixo (ou defina a env var
    DATABASE_URL) antes de rodar. Exemplo:
        postgresql+asyncpg://usuario:senha@localhost:5432/nome_do_banco
"""

import asyncio
import os
import sys
import uuid
from datetime import date, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print(
        "Aviso: python-dotenv não instalado; o .env não será "
        "carregado automaticamente. Rode: uv add python-dotenv"
    )

# No Windows, o asyncpg tem um bug conhecido com o ProactorEventLoop
# (padrão do asyncio) que causa quedas de conexão no meio da operação.
# Forçamos o SelectorEventLoop para evitar isso.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Monta a DATABASE_URL a partir das variáveis POSTGRES_* do .env,
# caso DATABASE_URL não esteja definida diretamente.
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "usuario")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "senha")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "nome_do_banco")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)

metadata = sa.MetaData()

# --- Definição das tabelas (espelhando a migration) -------------------------

badge = sa.Table(
    "badge",
    metadata,
    sa.Column("bdg_id", sa.UUID(), primary_key=True),
    sa.Column("bdg_name", sa.String(255), nullable=False),
    sa.Column("bdg_description", sa.Text()),
    sa.Column(
        "bdg_rarity",
        postgresql.ENUM(
            "common",
            "rare",
            "epic",
            "legendary",
            name="badge_rarity",
            create_type=False,
        ),
    ),
    sa.Column(
        "bdg_criteria",
        postgresql.ENUM(
            "xp_gained",
            "tracks_completed",
            "lessons_completed",
            "right_answers",
            "day_streak",
            "tracks_created",
            "missions_completed",
            name="badge_criteria",
            create_type=False,
        ),
    ),
    sa.Column("bdg_criteria_value", sa.Integer()),
    sa.Column("bdg_updated_at", sa.DateTime()),
)

user = sa.Table(
    "user",
    metadata,
    sa.Column("usr_id", sa.UUID(), primary_key=True),
    sa.Column("usr_email", sa.String(255), nullable=False),
    sa.Column("usr_name", sa.String(255), nullable=False),
    sa.Column("usr_password_hash", sa.String(255), nullable=False),
    sa.Column("usr_created_at", sa.DateTime()),
    sa.Column("usr_updated_at", sa.DateTime()),
)

badge_progress = sa.Table(
    "badge_progress",
    metadata,
    sa.Column("bpg_id", sa.UUID(), primary_key=True),
    sa.Column("bpg_user_id", sa.UUID(), nullable=False),
    sa.Column("bpg_badge_id", sa.UUID(), nullable=False),
    sa.Column(
        "bpg_status",
        postgresql.ENUM(
            "idle",
            "in_progress",
            "done",
            name="badge_progress_status",
            create_type=False,
        ),
    ),
    sa.Column("bpg_updated_at", sa.DateTime()),
)

day_streak = sa.Table(
    "day_streak",
    metadata,
    sa.Column("dst_id", sa.UUID(), primary_key=True),
    sa.Column("dst_user_id", sa.UUID(), nullable=False),
    sa.Column("dst_value", sa.Integer()),
    sa.Column("dst_updated_at", sa.DateTime()),
)

login = sa.Table(
    "login",
    metadata,
    sa.Column("lgn_id", sa.UUID(), primary_key=True),
    sa.Column("lgn_user_id", sa.UUID(), nullable=False),
    sa.Column("lgn_date", sa.Date(), nullable=False),
    sa.Column("lgn_updated_at", sa.DateTime()),
)

track = sa.Table(
    "track",
    metadata,
    sa.Column("trk_id", sa.UUID(), primary_key=True),
    sa.Column("trk_user_id", sa.UUID(), nullable=False),
    sa.Column("trk_title", sa.String(255), nullable=False),
    sa.Column("trk_description", sa.Text()),
    sa.Column("trk_created_at", sa.DateTime()),
    sa.Column("trk_updated_at", sa.DateTime()),
)

step = sa.Table(
    "step",
    metadata,
    sa.Column("stp_id", sa.UUID(), primary_key=True),
    sa.Column("stp_track_id", sa.UUID(), nullable=False),
    sa.Column(
        "stp_level",
        postgresql.ENUM(
            "beginner",
            "intermediate",
            "advanced",
            "pro",
            name="step_level",
            create_type=False,
        ),
    ),
    sa.Column("stp_title", sa.String(255), nullable=False),
    sa.Column(
        "stp_status",
        postgresql.ENUM(
            "idle",
            "in_progress",
            "done",
            name="step_status",
            create_type=False,
        ),
    ),
    sa.Column("stp_updated_at", sa.DateTime()),
)

lesson = sa.Table(
    "lesson",
    metadata,
    sa.Column("lsn_id", sa.UUID(), primary_key=True),
    sa.Column("lsn_step_id", sa.UUID(), nullable=False),
    sa.Column("lsn_title", sa.String(255), nullable=False),
    sa.Column("lsn_text", sa.Text(), nullable=False),
    sa.Column(
        "lsn_status",
        postgresql.ENUM(
            "idle",
            "in_progress",
            "done",
            name="lesson_status",
            create_type=False,
        ),
    ),
    sa.Column("lsn_position", sa.Integer(), nullable=False),
    sa.Column("lsn_updated_at", sa.DateTime()),
)

mission = sa.Table(
    "mission",
    metadata,
    sa.Column("msn_id", sa.UUID(), primary_key=True),
    sa.Column("msn_step_id", sa.UUID(), nullable=False),
    sa.Column("msn_title", sa.String(255), nullable=False),
    sa.Column(
        "msn_difficulty",
        postgresql.ENUM(
            "easy",
            "medium",
            "hard",
            "very_hard",
            name="mission_difficulty",
            create_type=False,
        ),
    ),
    sa.Column("msn_xp_reward", sa.Integer(), nullable=False),
    sa.Column(
        "msn_criteria",
        postgresql.ENUM(
            "number_of_lessons_completed",
            "get_all_answer_right_in_a_lesson",
            "complete_a_step",
            "complete_a_track",
            "number_of_steps_completed",
            "get_all_answers_right",
            name="mission_criteria",
            create_type=False,
        ),
    ),
    sa.Column("msn_criteria_value", sa.Integer(), nullable=False),
    sa.Column("msn_updated_at", sa.DateTime()),
)

feedback = sa.Table(
    "feedback",
    metadata,
    sa.Column("fbk_id", sa.UUID(), primary_key=True),
    sa.Column("fbk_lesson_id", sa.UUID(), nullable=False),
    sa.Column("fbk_user_id", sa.UUID(), nullable=False),
    sa.Column("fbk_text", sa.Text(), nullable=False),
    sa.Column("fbk_created_at", sa.DateTime()),
    sa.Column("fbk_updated_at", sa.DateTime()),
)

lesson_file = sa.Table(
    "lesson_file",
    metadata,
    sa.Column("lsf_id", sa.UUID(), primary_key=True),
    sa.Column("lsf_lesson_id", sa.UUID(), nullable=False),
    sa.Column("lsf_path", sa.String(1024), nullable=False),
    sa.Column(
        "lsf_file_type",
        postgresql.ENUM(
            "audio", "gif", "image", name="lesson_file_type", create_type=False
        ),
    ),
    sa.Column("lsf_updated_at", sa.DateTime()),
)

mission_progress = sa.Table(
    "mission_progress",
    metadata,
    sa.Column("mpg_id", sa.UUID(), primary_key=True),
    sa.Column("mpg_user_id", sa.UUID(), nullable=False),
    sa.Column("mpg_mission_id", sa.UUID(), nullable=False),
    sa.Column(
        "mpg_status",
        postgresql.ENUM(
            "idle",
            "in_progress",
            "done",
            name="mission_progress_status",
            create_type=False,
        ),
    ),
    sa.Column("mpg_finished_in", sa.DateTime()),
    sa.Column("mpg_score", sa.Integer()),
    sa.Column("mpg_updated_at", sa.DateTime()),
)

quiz = sa.Table(
    "quiz",
    metadata,
    sa.Column("qui_id", sa.UUID(), primary_key=True),
    sa.Column("qui_lesson_id", sa.UUID(), nullable=False),
    sa.Column("qui_question", sa.Text(), nullable=False),
    sa.Column("qui_updated_at", sa.DateTime()),
)

answer = sa.Table(
    "answer",
    metadata,
    sa.Column("ans_id", sa.UUID(), primary_key=True),
    sa.Column("ans_question_id", sa.UUID(), nullable=False),
    sa.Column("ans_user_id", sa.UUID(), nullable=False),
    sa.Column("ans_text", sa.Text(), nullable=False),
    sa.Column(
        "ans_rate",
        postgresql.ENUM(
            "good",
            "perfect",
            "wrong",
            "almost_got_it",
            name="answer_rate",
            create_type=False,
        ),
    ),
    sa.Column("ans_created_at", sa.DateTime()),
    sa.Column("ans_updated_at", sa.DateTime()),
)


def uid() -> uuid.UUID:
    return uuid.uuid4()


async def seed(session: AsyncSession) -> None:
    now = datetime.utcnow()

    # --- badges ---------------------------------------------------------
    badges = [
        {
            "bdg_id": uid(),
            "bdg_name": "Primeiros Passos",
            "bdg_description": "Complete sua primeira lição.",
            "bdg_rarity": "common",
            "bdg_criteria": "lessons_completed",
            "bdg_criteria_value": 1,
            "bdg_updated_at": now,
        },
        {
            "bdg_id": uid(),
            "bdg_name": "Sequência de Ferro",
            "bdg_description": "Mantenha um streak de 7 dias.",
            "bdg_rarity": "rare",
            "bdg_criteria": "day_streak",
            "bdg_criteria_value": 7,
            "bdg_updated_at": now,
        },
        {
            "bdg_id": uid(),
            "bdg_name": "Mestre das Trilhas",
            "bdg_description": "Complete 3 trilhas.",
            "bdg_rarity": "epic",
            "bdg_criteria": "tracks_completed",
            "bdg_criteria_value": 3,
            "bdg_updated_at": now,
        },
        {
            "bdg_id": uid(),
            "bdg_name": "Lenda dos Dados",
            "bdg_description": "Acumule 10000 XP.",
            "bdg_rarity": "legendary",
            "bdg_criteria": "xp_gained",
            "bdg_criteria_value": 10000,
            "bdg_updated_at": now,
        },
    ]
    await session.execute(sa.insert(badge), badges)

    # --- users ------------------------------------------------------------
    users = [
        {
            "usr_id": uid(),
            "usr_email": "ana.silva@example.com",
            "usr_name": "Ana Silva",
            "usr_password_hash": "hash_ana",
            "usr_created_at": now,
            "usr_updated_at": now,
        },
        {
            "usr_id": uid(),
            "usr_email": "bruno.costa@example.com",
            "usr_name": "Bruno Costa",
            "usr_password_hash": "hash_bruno",
            "usr_created_at": now,
            "usr_updated_at": now,
        },
        {
            "usr_id": uid(),
            "usr_email": "carla.mendes@example.com",
            "usr_name": "Carla Mendes",
            "usr_password_hash": "hash_carla",
            "usr_created_at": now,
            "usr_updated_at": now,
        },
    ]
    await session.execute(sa.insert(user), users)

    # --- badge_progress -----------------------------------------------
    badge_progress_rows = [
        {
            "bpg_id": uid(),
            "bpg_user_id": users[0]["usr_id"],
            "bpg_badge_id": badges[0]["bdg_id"],
            "bpg_status": "done",
            "bpg_updated_at": now,
        },
        {
            "bpg_id": uid(),
            "bpg_user_id": users[0]["usr_id"],
            "bpg_badge_id": badges[1]["bdg_id"],
            "bpg_status": "in_progress",
            "bpg_updated_at": now,
        },
        {
            "bpg_id": uid(),
            "bpg_user_id": users[1]["usr_id"],
            "bpg_badge_id": badges[0]["bdg_id"],
            "bpg_status": "done",
            "bpg_updated_at": now,
        },
    ]
    await session.execute(sa.insert(badge_progress), badge_progress_rows)

    # --- day_streak ------------------------------------------------------
    day_streak_rows = [
        {
            "dst_id": uid(),
            "dst_user_id": users[0]["usr_id"],
            "dst_value": 5,
            "dst_updated_at": now,
        },
        {
            "dst_id": uid(),
            "dst_user_id": users[1]["usr_id"],
            "dst_value": 12,
            "dst_updated_at": now,
        },
        {
            "dst_id": uid(),
            "dst_user_id": users[2]["usr_id"],
            "dst_value": 0,
            "dst_updated_at": now,
        },
    ]
    await session.execute(sa.insert(day_streak), day_streak_rows)

    # --- login -------------------------------------------------------------
    login_rows = [
        {
            "lgn_id": uid(),
            "lgn_user_id": users[0]["usr_id"],
            "lgn_date": date.today(),
            "lgn_updated_at": now,
        },
        {
            "lgn_id": uid(),
            "lgn_user_id": users[0]["usr_id"],
            "lgn_date": date.today() - timedelta(days=1),
            "lgn_updated_at": now,
        },
        {
            "lgn_id": uid(),
            "lgn_user_id": users[1]["usr_id"],
            "lgn_date": date.today(),
            "lgn_updated_at": now,
        },
    ]
    await session.execute(sa.insert(login), login_rows)

    # --- tracks --------------------------------------------------------
    tracks = [
        {
            "trk_id": uid(),
            "trk_user_id": users[0]["usr_id"],
            "trk_title": "Introdução à Mineração de Dados",
            "trk_description": "Conceitos fundamentais de data mining.",
            "trk_created_at": now,
            "trk_updated_at": now,
        },
        {
            "trk_id": uid(),
            "trk_user_id": users[1]["usr_id"],
            "trk_title": "SQL na Prática",
            "trk_description": "Consultas e modelagem em bancos relacionais.",
            "trk_created_at": now,
            "trk_updated_at": now,
        },
    ]
    await session.execute(sa.insert(track), tracks)

    # --- steps -----------------------------------------------------------
    steps = [
        {
            "stp_id": uid(),
            "stp_track_id": tracks[0]["trk_id"],
            "stp_level": "beginner",
            "stp_title": "Fundamentos de Dados",
            "stp_status": "done",
            "stp_updated_at": now,
        },
        {
            "stp_id": uid(),
            "stp_track_id": tracks[0]["trk_id"],
            "stp_level": "intermediate",
            "stp_title": "Pré-processamento",
            "stp_status": "in_progress",
            "stp_updated_at": now,
        },
        {
            "stp_id": uid(),
            "stp_track_id": tracks[1]["trk_id"],
            "stp_level": "beginner",
            "stp_title": "Consultas Básicas em SQL",
            "stp_status": "idle",
            "stp_updated_at": now,
        },
    ]
    await session.execute(sa.insert(step), steps)

    # --- lessons ---------------------------------------------------------
    lessons = [
        {
            "lsn_id": uid(),
            "lsn_step_id": steps[0]["stp_id"],
            "lsn_title": "O que são dados?",
            "lsn_text": "Nesta lição você vai aprender o conceito de dado.",
            "lsn_status": "done",
            "lsn_position": 1,
            "lsn_updated_at": now,
        },
        {
            "lsn_id": uid(),
            "lsn_step_id": steps[0]["stp_id"],
            "lsn_title": "Tipos de dados",
            "lsn_text": "Nesta lição você vai aprender os tipos de dados.",
            "lsn_status": "in_progress",
            "lsn_position": 2,
            "lsn_updated_at": now,
        },
        {
            "lsn_id": uid(),
            "lsn_step_id": steps[2]["stp_id"],
            "lsn_title": "SELECT básico",
            "lsn_text": "Introdução ao comando SELECT.",
            "lsn_status": "idle",
            "lsn_position": 1,
            "lsn_updated_at": now,
        },
    ]
    await session.execute(sa.insert(lesson), lessons)

    # --- missions --------------------------------------------------------
    missions = [
        {
            "msn_id": uid(),
            "msn_step_id": steps[0]["stp_id"],
            "msn_title": "Complete a primeira lição",
            "msn_difficulty": "easy",
            "msn_xp_reward": 50,
            "msn_criteria": "number_of_lessons_completed",
            "msn_criteria_value": 1,
            "msn_updated_at": now,
        },
        {
            "msn_id": uid(),
            "msn_step_id": steps[1]["stp_id"],
            "msn_title": "Complete o step inteiro",
            "msn_difficulty": "medium",
            "msn_xp_reward": 150,
            "msn_criteria": "complete_a_step",
            "msn_criteria_value": 1,
            "msn_updated_at": now,
        },
    ]
    await session.execute(sa.insert(mission), missions)

    # --- feedback ----------------------------------------------------------
    feedback_rows = [
        {
            "fbk_id": uid(),
            "fbk_lesson_id": lessons[0]["lsn_id"],
            "fbk_user_id": users[0]["usr_id"],
            "fbk_text": "Lição bem explicada!",
            "fbk_created_at": now,
            "fbk_updated_at": now,
        },
        {
            "fbk_id": uid(),
            "fbk_lesson_id": lessons[1]["lsn_id"],
            "fbk_user_id": users[1]["usr_id"],
            "fbk_text": "Poderia ter mais exemplos.",
            "fbk_created_at": now,
            "fbk_updated_at": now,
        },
    ]
    await session.execute(sa.insert(feedback), feedback_rows)

    # --- lesson_file ------------------------------------------------------
    lesson_file_rows = [
        {
            "lsf_id": uid(),
            "lsf_lesson_id": lessons[0]["lsn_id"],
            "lsf_path": "/media/lessons/o-que-sao-dados.png",
            "lsf_file_type": "image",
            "lsf_updated_at": now,
        },
        {
            "lsf_id": uid(),
            "lsf_lesson_id": lessons[2]["lsn_id"],
            "lsf_path": "/media/lessons/select-basico.gif",
            "lsf_file_type": "gif",
            "lsf_updated_at": now,
        },
    ]
    await session.execute(sa.insert(lesson_file), lesson_file_rows)

    # --- mission_progress ---------------------------------------------
    mission_progress_rows = [
        {
            "mpg_id": uid(),
            "mpg_user_id": users[0]["usr_id"],
            "mpg_mission_id": missions[0]["msn_id"],
            "mpg_status": "done",
            "mpg_finished_in": now,
            "mpg_score": 100,
            "mpg_updated_at": now,
        },
        {
            "mpg_id": uid(),
            "mpg_user_id": users[1]["usr_id"],
            "mpg_mission_id": missions[1]["msn_id"],
            "mpg_status": "in_progress",
            "mpg_finished_in": None,
            "mpg_score": None,
            "mpg_updated_at": now,
        },
    ]
    await session.execute(sa.insert(mission_progress), mission_progress_rows)

    # --- quiz -------------------------------------------------------------
    quizzes = [
        {
            "qui_id": uid(),
            "qui_lesson_id": lessons[0]["lsn_id"],
            "qui_question": (
                "Qual das opções é um exemplo de dado estruturado?"
            ),
            "qui_updated_at": now,
        },
        {
            "qui_id": uid(),
            "qui_lesson_id": lessons[2]["lsn_id"],
            "qui_question": "Qual cláusula SQL filtra linhas?",
            "qui_updated_at": now,
        },
    ]
    await session.execute(sa.insert(quiz), quizzes)

    # --- answer -------------------------------------------------------
    answer_rows = [
        {
            "ans_id": uid(),
            "ans_question_id": quizzes[0]["qui_id"],
            "ans_user_id": users[0]["usr_id"],
            "ans_text": "Uma planilha com colunas fixas.",
            "ans_rate": "perfect",
            "ans_created_at": now,
            "ans_updated_at": now,
        },
        {
            "ans_id": uid(),
            "ans_question_id": quizzes[1]["qui_id"],
            "ans_user_id": users[1]["usr_id"],
            "ans_text": "WHERE",
            "ans_rate": "good",
            "ans_created_at": now,
            "ans_updated_at": now,
        },
    ]
    await session.execute(sa.insert(answer), answer_rows)

    await session.commit()
    print("Seed concluído com sucesso.")


async def main() -> None:
    engine = create_async_engine(DATABASE_URL)
    async with AsyncSession(engine) as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())