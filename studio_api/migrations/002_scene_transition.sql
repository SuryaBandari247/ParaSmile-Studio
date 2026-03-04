-- Add transition effect column to scenes (used during final render concat)
ALTER TABLE scenes ADD COLUMN transition TEXT NOT NULL DEFAULT 'fade';
