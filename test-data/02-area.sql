-- Insert areas

-- Amsterdam area
INSERT INTO area (area_id, filename, filedata, competent_authority_id, created_at)
VALUES (
  'amsterdam-area-0363',
  'Amsterdam.zip',
  pg_read_binary_file('/test-data/Amsterdam.zip'),
  (SELECT id FROM competent_authority WHERE competent_authority_id = 'sdep-ca-0363'),
  NOW()
);

-- Rotterdam area
INSERT INTO area (area_id, filename, filedata, competent_authority_id, created_at)
VALUES (
  'rotterdam-area-0599',
  'Rotterdam.zip',
  pg_read_binary_file('/test-data/Rotterdam.zip'),
  (SELECT id FROM competent_authority WHERE competent_authority_id = 'sdep-ca-0599'),
  NOW()
);

-- Den Haag area
INSERT INTO area (area_id, filename, filedata, competent_authority_id, created_at)
VALUES (
  'denhaag-area-0518',
  'Den_Haag.zip',
  pg_read_binary_file('/test-data/Den_Haag.zip'),
  (SELECT id FROM competent_authority WHERE competent_authority_id = 'sdep-ca-0518'),
  NOW()
);
