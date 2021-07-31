"""Create a table for accounts

Revision ID: e7fdd31ab1ef
Revises: 0bb1586e5014
Create Date: 2021-07-31 05:16:40.904110

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7fdd31ab1ef'
down_revision = '0bb1586e5014'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('account',
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('phone', sa.String(), nullable=True),
    sa.Column('mail_address', sa.String(), nullable=True),
    sa.Column('billing_address', sa.String(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    op.add_column('resource', sa.Column('account_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'resource', 'account', ['account_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'resource', type_='foreignkey')
    op.drop_column('resource', 'account_id')
    op.drop_table('account')
    # ### end Alembic commands ###
