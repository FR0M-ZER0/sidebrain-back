"""Adiciona versão de credencial e unicidade de e-mail normalizado."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f81a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_user_usr_email_normalized"


def _token_version_column_exists(connection) -> bool:
    return bool(
        connection.execute(
            sa.text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'user'
                      AND column_name = 'usr_token_version'
                )
                """
            )
        ).scalar_one()
    )


def _normalized_email_index_validity(connection) -> bool | None:
    return connection.execute(
        sa.text(
            """
            SELECT index_state.indisvalid
            FROM pg_index AS index_state
            JOIN pg_class AS index_relation
              ON index_relation.oid = index_state.indexrelid
            JOIN pg_class AS table_relation
              ON table_relation.oid = index_state.indrelid
            JOIN pg_namespace AS table_namespace
              ON table_namespace.oid = table_relation.relnamespace
            WHERE table_namespace.nspname = current_schema()
              AND table_relation.relname = 'user'
              AND index_relation.relname = :index_name
            """
        ),
        {"index_name": INDEX_NAME},
    ).scalar_one_or_none()


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

    if not _token_version_column_exists(connection):
        op.add_column(
            "user",
            sa.Column(
                "usr_token_version",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )

    index_validity = _normalized_email_index_validity(connection)
    with op.get_context().autocommit_block():
        if index_validity is False:
            op.execute(
                f'DROP INDEX CONCURRENTLY IF EXISTS "{INDEX_NAME}"'
            )
        if index_validity is not True:
            op.execute(
                f'CREATE UNIQUE INDEX CONCURRENTLY "{INDEX_NAME}" '
                'ON "user" (lower(btrim(usr_email)))'
            )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS "{INDEX_NAME}"')
    op.drop_column("user", "usr_token_version")
