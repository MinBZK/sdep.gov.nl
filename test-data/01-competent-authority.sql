-- Insert competent authorities
-- These must be inserted first as area references them via foreign key
-- Can be removed once "competent authorities submit areas" is also supported (as this will provision the competent authorities automatically)

-- Gemeente Amsterdam
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0363',
  'Amsterdam (inclusief Weesp)',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Rotterdam
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0599',
  'Rotterdam',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Den Haag
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0518',
  'Den Haag',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Amstelveen
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0362',
  'Amstelveen',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Bergen (Noord-Holland)
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0373',
  'Bergen (Noord-Holland)',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Delft
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0503',
  'Delft',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Diemen
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0384',
  'Diemen',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Gouda
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0513',
  'Gouda',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Groningen
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0014',
  'Groningen (inclusief Haren, Slochteren en Ten Boer)',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Haarlem
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0392',
  'Haarlem',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Katwijk
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0537',
  'Katwijk',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Landsmeer
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0415',
  'Landsmeer',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Leiden
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0546',
  'Leiden',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Maastricht
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0935',
  'Maastricht',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Middelburg
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0687',
  'Middelburg',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Noordwijk
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0575',
  'Noordwijk (inclusief Noordwijkerhout)',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Pijnacker-Nootdorp
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-1926',
  'Pijnacker-Nootdorp',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Renkum
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0274',
  'Renkum',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Sluis
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-1714',
  'Sluis',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Schouwen-Duiveland
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-1676',
  'Schouwen-Duiveland',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Texel
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0448',
  'Texel',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Utrecht
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0344',
  'Utrecht',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Vlissingen
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0718',
  'Vlissingen',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Voorschoten
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0626',
  'Voorschoten',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Waterland
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0852',
  'Waterland',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Zaanstad
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0479',
  'Zaanstad',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Zandvoort
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0473',
  'Zandvoort',
  '2025-01-01 00:00:00+00'::timestamptz
);

-- Gemeente Zwolle
INSERT INTO competent_authority (competent_authority_id, competent_authority_name, created_at)
VALUES (
  'sdep-ca-0193',
  'Zwolle',
  '2025-01-01 00:00:00+00'::timestamptz
);
