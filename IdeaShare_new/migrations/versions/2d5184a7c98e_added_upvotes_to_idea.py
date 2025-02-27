"""Added upvotes to Idea

Revision ID: 2d5184a7c98e
Revises: 6d7de6b91220
Create Date: 2025-02-11 19:22:16.814592

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2d5184a7c98e'
down_revision = '6d7de6b91220'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('idea', schema=None) as batch_op:
        batch_op.add_column(sa.Column('upvotes', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('idea', schema=None) as batch_op:
        batch_op.drop_column('upvotes')

    # ### end Alembic commands ###
