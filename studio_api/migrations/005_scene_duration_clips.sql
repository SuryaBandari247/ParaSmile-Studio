-- Add user-controllable target duration and clip count per scene
ALTER TABLE scenes ADD COLUMN target_duration REAL;
ALTER TABLE scenes ADD COLUMN clip_count INTEGER NOT NULL DEFAULT 0;
