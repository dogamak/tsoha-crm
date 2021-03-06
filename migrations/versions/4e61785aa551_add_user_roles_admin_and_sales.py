"""Add user roles ADMIN and SALES

Revision ID: 4e61785aa551
Revises: e38d0733c4f5
Create Date: 2021-07-29 00:43:11.575291

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '4e61785aa551'
down_revision = 'e38d0733c4f5'
branch_labels = None
depends_on = None


def upgrade():
    userrole = postgresql.ENUM('Administrator', 'Sales', name='userrole')
    userrole.create(op.get_bind())

    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('role', sa.Enum('Administrator', 'Sales', name='userrole'), nullable=False, server_default=sa.schema.DefaultClause("Administrator")))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'role')
    # ### end Alembic commands ###

    op.execute('DROP TYPE userrole')
