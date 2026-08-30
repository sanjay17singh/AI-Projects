"""add 'serper' to run_costs.provider allowed values

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_cost_provider", "run_costs", type_="check")
    op.create_check_constraint(
        "ck_cost_provider", "run_costs", "provider IN ('openai','you_com','pinecone','serper')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_cost_provider", "run_costs", type_="check")
    op.create_check_constraint(
        "ck_cost_provider", "run_costs", "provider IN ('openai','you_com','pinecone')"
    )
