import sqlalchemy

from app.db import metadata


profiles = sqlalchemy.Table(
    "profiles",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String, nullable=False, unique=True),
    sqlalchemy.Column("gender", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("gender_probability", sqlalchemy.Float, nullable=False),
    sqlalchemy.Column("sample_size", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("age", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("age_group", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("country_id", sqlalchemy.String(2), nullable=False),
    sqlalchemy.Column("country_name", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("country_probability", sqlalchemy.Float, nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.String, nullable=False),
)

users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("github_id", sqlalchemy.String, nullable=False, unique=True),
    sqlalchemy.Column("username", sqlalchemy.String, nullable=False, unique=True),
    sqlalchemy.Column("email", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("avatar_url", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("role", sqlalchemy.String, nullable=False, server_default="analyst"),
    sqlalchemy.Column("is_active", sqlalchemy.Boolean, nullable=False, server_default=sqlalchemy.true()),
    sqlalchemy.Column("last_login_at", sqlalchemy.DateTime(timezone=True), nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
)

refresh_tokens = sqlalchemy.Table(
    "refresh_tokens",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("user_id", sqlalchemy.String, sqlalchemy.ForeignKey("users.id"), nullable=False),
    sqlalchemy.Column("token_hash", sqlalchemy.String, nullable=False, unique=True),
    sqlalchemy.Column("expires_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.Column("revoked_at", sqlalchemy.DateTime(timezone=True), nullable=True),
)

oauth_states = sqlalchemy.Table(
    "oauth_states",
    metadata,
    sqlalchemy.Column("state", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("client_type", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("redirect_uri", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("return_to", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("code_challenge", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("code_verifier", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.Column("expires_at", sqlalchemy.DateTime(timezone=True), nullable=False),
    sqlalchemy.Column("consumed_at", sqlalchemy.DateTime(timezone=True), nullable=True),
)
