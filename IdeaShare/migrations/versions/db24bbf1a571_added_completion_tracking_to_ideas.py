"""Added completion tracking to ideas

Revision ID: db24bbf1a571
Revises: 9331614d18c0
Create Date: 2025-02-22 00:48:47.392824

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'db24bbf1a571'
down_revision = '9331614d18c0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('idea', schema=None) as batch_op:
        batch_op.add_column(sa.Column('completed_by', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('completion_link', sa.String(length=255), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('idea', schema=None) as batch_op:
        batch_op.drop_column('completion_link')
        batch_op.drop_column('completed_by')

    # ### end Alembic commands ###
