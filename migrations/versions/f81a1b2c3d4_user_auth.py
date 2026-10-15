"""Adiciona versão de credencial e unicidade de e-mail normalizado."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f81a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_user_usr_email_normalized"


def upgrade() -> None:
    connection = op.get_bind()
    duplicates = connection.execute(
        sa.text(
            """
            SELECT lower(btrim(usr_email)) AS normalized_email,
                   count(*) AS account_count,
                   array_agg(usr_id) AS user_ids
            FROM "user"
            GROUP BY lower(btrim(usr_email))
            HAVING count(*) > 1
            """
        )
    ).fetchall()
    if duplicates:
        raise RuntimeError(
            "Existem contas com e-mail normalizado duplicado; "
            "reconcilie os titulares antes de aplicar a migração."
        )

    op.add_column(
        "user",
        sa.Column(
            "usr_token_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # Se uma escrita concorrente invalidar a criação, execute
    # DROP INDEX CONCURRENTLY IF EXISTS uq_user_usr_email_normalized,
    # reconcilie a colisão e reaplique esta revisão.
    with op.get_context().autocommit_block():
        op.execute(
            f'CREATE UNIQUE INDEX CONCURRENTLY "{INDEX_NAME}" '
            'ON "user" (lower(btrim(usr_email)))'
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS "{INDEX_NAME}"')
    op.drop_column("user", "usr_token_version")
