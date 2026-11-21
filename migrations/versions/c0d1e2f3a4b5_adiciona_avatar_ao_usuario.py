"""Adiciona catálogo de avatares e referência opcional ao usuário."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "c0d1e2f3a4b5"
down_revision: str | Sequence[str] | None = "a92b8c9d0e1f"
branch_labels = None
depends_on = None

AVATARS = (
    ("cat", "Gato", "/static/avatars/cat.png"),
    ("dog", "Cachorro", "/static/avatars/dog.png"),
    ("fox", "Raposa", "/static/avatars/fox.png"),
    ("bear", "Urso", "/static/avatars/bear.png"),
    ("rabbit", "Coelho", "/static/avatars/rabbit.png"),
    ("panda", "Panda", "/static/avatars/panda.png"),
    ("owl", "Coruja", "/static/avatars/owl.png"),
    ("penguin", "Pinguim", "/static/avatars/penguin.png"),
    ("lion", "Leão", "/static/avatars/lion.png"),
    ("turtle", "Tartaruga", "/static/avatars/turtle.png"),
)


def upgrade() -> None:
    op.create_table(
        "avatar",
        sa.Column("avt_slug", sa.String(length=64), nullable=False),
        sa.Column("avt_name", sa.String(length=100), nullable=False),
        sa.Column("avt_image_path", sa.String(length=255), nullable=False),
        sa.Column(
            "avt_is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "avt_created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("avt_slug"),
    )
    op.add_column(
        "user",
        sa.Column("usr_avatar_slug", sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        "fk_user_avatar_slug",
        "user",
        "avatar",
        ["usr_avatar_slug"],
        ["avt_slug"],
        ondelete="SET NULL",
    )
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO avatar (avt_slug, avt_name, avt_image_path)
            VALUES (:slug, :name, :image_path)
            ON CONFLICT (avt_slug) DO NOTHING
            """
        ),
        [
            {"slug": slug, "name": name, "image_path": image_path}
            for slug, name, image_path in AVATARS
        ],
    )


def downgrade() -> None:
    op.drop_constraint("fk_user_avatar_slug", "user", type_="foreignkey")
    op.drop_column("user", "usr_avatar_slug")
    op.drop_table("avatar")
