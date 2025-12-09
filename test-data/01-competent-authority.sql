-- Insert competent authorities
-- These must be inserted first as area references them via foreign key
-- Can be removed once "competent authorities submit areas" is also supported (as this will provision the competent authorities automatically)

-- Gemeente Amsterdam
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0363',
  'Amsterdam (inclusief Weesp)',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Rotterdam
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0599',
  'Rotterdam',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Den Haag
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0518',
  'Den Haag',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Amstelveen
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0362',
  'Amstelveen',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Bergen (Noord-Holland)
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0373',
  'Bergen (Noord-Holland)',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Delft
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0503',
  'Delft',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Diemen
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0384',
  'Diemen',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Gouda
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0513',
  'Gouda',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Groningen
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0014',
  'Groningen (inclusief Haren, Slochteren en Ten Boer)',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Haarlem
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0392',
  'Haarlem',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Katwijk
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0537',
  'Katwijk',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Landsmeer
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0415',
  'Landsmeer',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Leiden
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0546',
  'Leiden',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Maastricht
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0935',
  'Maastricht',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Middelburg
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0687',
  'Middelburg',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Noordwijk
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0575',
  'Noordwijk (inclusief Noordwijkerhout)',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Pijnacker-Nootdorp
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-1926',
  'Pijnacker-Nootdorp',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Renkum
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0274',
  'Renkum',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Sluis
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-1714',
  'Sluis',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Schouwen-Duiveland
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-1676',
  'Schouwen-Duiveland',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Texel
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0448',
  'Texel',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Utrecht
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0344',
  'Utrecht',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Vlissingen
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0718',
  'Vlissingen',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Voorschoten
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0626',
  'Voorschoten',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Waterland
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0852',
  'Waterland',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Zaanstad
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0479',
  'Zaanstad',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Zandvoort
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0473',
  'Zandvoort',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;

-- Gemeente Zwolle
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0193',
  'Zwolle',
  NOW()
)
ON CONFLICT (competent_authority_id) DO NOTHING;
