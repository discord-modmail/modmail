-- upgrade --
ALTER TABLE "configurations" DROP CONSTRAINT "fk_configur_servers_471a90ee";
ALTER TABLE "configurations" RENAME COLUMN "target_server_id_id" TO "target_guild_id_id";
CREATE TABLE IF NOT EXISTS "guilds" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(200) NOT NULL,
    "icon_url" TEXT NOT NULL
);
COMMENT ON TABLE "guilds" IS 'Database model representing a discord guild.';;
ALTER TABLE "tickets" ADD "creating_message_id_id" BIGINT NOT NULL;
ALTER TABLE "tickets" RENAME COLUMN "creater_id" TO "author_id";
ALTER TABLE "tickets" ADD "author_id" BIGINT NOT NULL;
ALTER TABLE "tickets" DROP COLUMN "creating_message_id";
DROP TABLE IF EXISTS "servers";
ALTER TABLE "configurations" ADD CONSTRAINT "fk_configur_guilds_942a92c3" FOREIGN KEY ("target_guild_id_id") REFERENCES "guilds" ("id") ON DELETE CASCADE;
ALTER TABLE "tickets" ADD CONSTRAINT "fk_tickets_messages_581a3e15" FOREIGN KEY ("creating_message_id_id") REFERENCES "messages" ("id") ON DELETE CASCADE;
-- downgrade --
ALTER TABLE "configurations" DROP CONSTRAINT "fk_configur_guilds_942a92c3";
ALTER TABLE "tickets" DROP CONSTRAINT "fk_tickets_messages_581a3e15";
ALTER TABLE "tickets" RENAME COLUMN "author_id" TO "creater_id";
ALTER TABLE "tickets" RENAME COLUMN "author_id" TO "creating_message_id";
ALTER TABLE "tickets" DROP COLUMN "creating_message_id_id";
ALTER TABLE "configurations" RENAME COLUMN "target_guild_id_id" TO "target_server_id_id";
DROP TABLE IF EXISTS "guilds";
ALTER TABLE "configurations" ADD CONSTRAINT "fk_configur_servers_471a90ee" FOREIGN KEY ("target_server_id_id") REFERENCES "servers" ("id") ON DELETE CASCADE;
