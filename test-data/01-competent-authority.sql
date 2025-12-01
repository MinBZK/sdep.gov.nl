-- Insert competent authorities
-- These must be inserted first as area references them via foreign key

-- Gemeente Amsterdam
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0363',
  'Gemeente Amsterdam',
  NOW()
);

-- Gemeente Rotterdam
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0599',
  'Gemeente Rotterdam',
  NOW()
);

-- Gemeente Den Haag
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0518',
  'Gemeente Den Haag',
  NOW()
);
