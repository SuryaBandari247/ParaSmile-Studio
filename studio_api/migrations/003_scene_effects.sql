-- Add effects column to scenes (JSON array of effect names applied during render)
ALTER TABLE scenes ADD COLUMN effects_json TEXT NOT NULL DEFAULT '[]';
