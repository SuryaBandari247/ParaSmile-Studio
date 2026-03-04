-- Add show_title toggle to scenes (controls text overlay on stock footage, default off)
ALTER TABLE scenes ADD COLUMN show_title INTEGER NOT NULL DEFAULT 0;
