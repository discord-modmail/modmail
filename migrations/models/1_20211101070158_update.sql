-- upgrade --
CREATE TABLE IF NOT EXISTS "stickers" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(32) NOT NULL,
    "url" TEXT NOT NULL,
    "message_id_id" BIGINT NOT NULL REFERENCES "messages" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "stickers" IS 'Database model representing a custom discord sticker.';
-- downgrade --
DROP TABLE IF EXISTS "stickers";
