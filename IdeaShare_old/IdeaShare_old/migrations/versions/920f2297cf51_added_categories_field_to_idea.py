"""Added categories field to Idea

Revision ID: 920f2297cf51
Revises: dfcefa598869
Create Date: 2025-02-20 20:38:19.490346

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '920f2297cf51'
down_revision = 'dfcefa598869'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('idea', schema=None) as batch_op:
        batch_op.add_column(sa.Column('categories', sa.String(length=255), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('idea', schema=None) as batch_op:
        batch_op.drop_column('categories')

    # ### end Alembic commands ###
