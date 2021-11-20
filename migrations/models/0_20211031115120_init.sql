-- upgrade --
CREATE TABLE IF NOT EXISTS "messages" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "ticket_id" BIGINT NOT NULL,
    "mirrored_id" BIGINT NOT NULL,
    "author_id" BIGINT NOT NULL,
    "content" VARCHAR(4000) NOT NULL
);
COMMENT ON TABLE "messages" IS 'Database model representing a message sent in a modmail ticket.';
CREATE TABLE IF NOT EXISTS "attachments" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "filename" VARCHAR(255) NOT NULL,
    "file_url" TEXT NOT NULL,
    "message_id_id" BIGINT NOT NULL REFERENCES "messages" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "attachments" IS 'Database model representing a message attachment sent in a modmail ticket.';
CREATE TABLE IF NOT EXISTS "embeds" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "content" JSONB NOT NULL,
    "message_id_id" BIGINT NOT NULL REFERENCES "messages" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "embeds" IS 'Database model representing a discord embed.';
CREATE TABLE IF NOT EXISTS "emojis" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(32) NOT NULL,
    "url" TEXT NOT NULL,
    "animated" BOOL NOT NULL  DEFAULT False,
    "message_id_id" BIGINT NOT NULL REFERENCES "messages" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "emojis" IS 'Database model representing a custom discord emoji.';
CREATE TABLE IF NOT EXISTS "servers" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(200) NOT NULL,
    "icon_url" TEXT NOT NULL
);
COMMENT ON TABLE "servers" IS 'Database model representing a discord server.';
CREATE TABLE IF NOT EXISTS "configurations" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "target_bot_id" BIGINT,
    "config_key" TEXT NOT NULL,
    "config_value" TEXT NOT NULL,
    "target_server_id_id" BIGINT REFERENCES "servers" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "configurations" IS 'Database model representing a discord modmail bot configurations.';
CREATE TABLE IF NOT EXISTS "tickets" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "thread_id" BIGINT NOT NULL UNIQUE,
    "creater_id" BIGINT NOT NULL,
    "creating_message_id" BIGINT NOT NULL,
    "creating_channel_id" BIGINT NOT NULL,
    "server_id_id" BIGINT NOT NULL REFERENCES "servers" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "tickets" IS 'An discord modmail ticket for a Discord user with id `creator_id`.';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(20) NOT NULL,
    "content" JSONB NOT NULL
);
