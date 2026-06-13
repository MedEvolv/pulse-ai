-- =============================================================================
-- Identity Crosswalk Seed — ReputationOS + Pulse AI
-- Target: PostgreSQL 15+ (Supabase-managed). Run AFTER schema.sql.
-- Version: v0.1  (2026-06-14)
--
-- Purpose: seed core.region / core.clinic / core.clinic_alias / core.actor so the
-- two products' demo identifiers resolve to the SAME canonical rows. This is the
-- table that makes "shared database" true (Pulse-00 §5.2).
--
-- Scope of v0.1: the clinics/actors that actually exist in the two running demos —
--   * Pulse AI  : engine.py CLINICS (12 synthetic) + OWNERS (5)
--   * ReputationOS: domain/demo-data.ts (6 real Clove clinics + their people)
--
-- HONESTY NOTES (do not "fix" these into false matches):
--   1. Exactly ONE clinic is a proven identity match across both products:
--        Kamla Nagar — Pulse 'DL-KMN-01' == Clove '5129'.
--      It is the only row with aliases from BOTH products.
--   2. "Thane" appears on both sides but is NOT merged: Pulse 'MH-THN-03' is a
--      generic synthetic locality; Clove 7102/7103 are two specific Thane
--      addresses. Three distinct canonical rows, by design.
--   3. Actor sets are fully disjoint. Beware near-name collisions that are
--      DIFFERENT people: repos 'Priya Sharma' != Pulse 'Priya Deshmukh';
--      repos 'Rohan Sethi' != Pulse 'Rohan Iyer'. Never auto-merge on first name.
--   4. canonical_code = the real Clove/SAP id where one exists (decision §7.3);
--      it is an INTERNAL join key and must never render on demo/external surfaces.
--      Pulse-only synthetic clinics use their Pulse code as canonical_code until a
--      real Clove id is assigned via the Master Tracker ingest (the scale-up path).
--   5. Latitude/longitude are NULL — no KML has been parsed in v0.1. Honesty rule:
--      absent data stays NULL rather than guessed.
--
-- Idempotent: every insert is ON CONFLICT DO NOTHING and resolves FKs by stable
-- business key (region.code / clinic.canonical_code / actor.code), so re-running
-- is safe and uuids never need to be hand-pinned.
-- =============================================================================

begin;

-- -----------------------------------------------------------------------------
-- 1. REGIONS — one hierarchy: band (Pulse) -> region -> sub_region (ReputationOS)
-- -----------------------------------------------------------------------------
-- Bands are Pulse's coarse REG-* split. ReputationOS regions/sub_regions hang
-- beneath the matching band.
insert into core.region (code, name, level, parent_uid) values
  ('REG-NORTH', 'North', 'band', null),
  ('REG-WEST',  'West',  'band', null),
  ('REG-SOUTH', 'South', 'band', null)
on conflict (code) do nothing;

insert into core.region (code, name, level, parent_uid)
select v.code, v.name, 'region', p.region_uid
from (values
  ('RN-NORTH-INDIA', 'North India',      'REG-NORTH'),
  ('RN-MUMBAI',      'Mumbai',           'REG-WEST'),
  ('RN-SW-INDIA',    'South West India', 'REG-WEST'),
  ('RN-SE-INDIA',    'South East India', 'REG-SOUTH'),
  ('RN-SOUTH-INDIA', 'South India',      'REG-SOUTH')   -- Karnataka / Pulse south band
) as v(code, name, parent_code)
join core.region p on p.code = v.parent_code
on conflict (code) do nothing;

insert into core.region (code, name, level, parent_uid)
select v.code, v.name, 'sub_region', p.region_uid
from (values
  ('SUB-DELHI-NCR', 'Delhi NCR', 'RN-NORTH-INDIA'),
  ('SUB-PUNJAB',    'Punjab',    'RN-NORTH-INDIA'),
  ('SUB-MUMBAI',    'Mumbai',    'RN-MUMBAI'),
  ('SUB-GUJARAT',   'Gujarat',   'RN-SW-INDIA'),
  ('SUB-TELANGANA', 'Telangana', 'RN-SE-INDIA'),
  ('SUB-KARNATAKA', 'Karnataka', 'RN-SOUTH-INDIA')
) as v(code, name, parent_code)
join core.region p on p.code = v.parent_code
on conflict (code) do nothing;

-- -----------------------------------------------------------------------------
-- 2. CLINICS — canonical rows (union, deduped on real identity)
-- -----------------------------------------------------------------------------
-- region_uid is resolved by the FINEST region we can justify from source data:
--   * ReputationOS clinics carry a real sub_region.
--   * Pulse clinics carry only a band, but their names are real localities, so
--     NCR/Mumbai/Karnataka placement is defensible (not invented). Pune has no
--     sub_region row, so it sits at the REG-WEST band.
insert into core.clinic (canonical_code, name, region_uid, sub_region, clinic_head, ops_executive)
select v.canonical_code, v.name, r.region_uid, v.sub_region, v.clinic_head, v.ops_executive
from (values
  -- (A) PROVEN MATCH — both products. canonical_code = Clove id.
  ('5129', 'Kamla Nagar', 'SUB-DELHI-NCR', 'Delhi NCR', 'Dr. Ritu Malhotra', 'Anuj Batra'),

  -- (B) ReputationOS-only (real Clove clinics). canonical_code = Clove id.
  ('6015', 'Amritsar - Ranjit Avenue',          'SUB-PUNJAB',    'Punjab',    'Dr. Harleen Kaur',   'Manpreet Sandhu'),
  ('7098', 'Shela, Ahmedabad',                  'SUB-GUJARAT',   'Gujarat',   'Dr. Niyati Shah',    'Kunal Trivedi'),
  ('7102', 'Dev Ashoka, Wagle Estate, Thane',   'SUB-MUMBAI',    'Mumbai',    'Dr. Sagar Kulkarni', 'Rashmi Patil'),
  ('7103', 'Manas CHS, Navpada, Thane',         'SUB-MUMBAI',    'Mumbai',    'Dr. Neha Deshpande', 'Rashmi Patil'),
  ('8120', 'Hasthinapuram',                     'SUB-TELANGANA', 'Telangana', 'Dr. Kavya Reddy',    'Sridhar Rao'),

  -- (C) Pulse-only (synthetic). canonical_code = Pulse code until a Clove id lands.
  ('DL-RHN-02', 'Rohini',          'SUB-DELHI-NCR', 'Delhi NCR', null, null),
  ('DL-DWK-03', 'Dwarka',          'SUB-DELHI-NCR', 'Delhi NCR', null, null),
  ('DL-NOD-04', 'Noida Sector 62', 'SUB-DELHI-NCR', 'Delhi NCR', null, null),
  ('MH-BAN-01', 'Bandra',          'SUB-MUMBAI',    'Mumbai',    null, null),
  ('MH-AND-02', 'Andheri',         'SUB-MUMBAI',    'Mumbai',    null, null),
  ('MH-THN-03', 'Thane',           'SUB-MUMBAI',    'Mumbai',    null, null),  -- generic; NOT 7102/7103
  ('MH-PUN-04', 'Pune Kothrud',    'REG-WEST',      null,        null, null),  -- no Pune sub_region row
  ('KA-IND-01', 'Indiranagar',     'SUB-KARNATAKA', 'Karnataka', null, null),
  ('KA-WFD-02', 'Whitefield',      'SUB-KARNATAKA', 'Karnataka', null, null),
  ('KA-JAY-03', 'Jayanagar',       'SUB-KARNATAKA', 'Karnataka', null, null),
  ('KA-HSR-04', 'HSR Layout',      'SUB-KARNATAKA', 'Karnataka', null, null)
) as v(canonical_code, name, region_code, sub_region, clinic_head, ops_executive)
join core.region r on r.code = v.region_code
on conflict (canonical_code) do nothing;

-- -----------------------------------------------------------------------------
-- 3. CLINIC ALIASES — the crosswalk (product external_code -> canonical clinic)
-- -----------------------------------------------------------------------------
-- The Kamla Nagar row carries aliases from BOTH products + Clove (the alignment).
insert into core.clinic_alias (product, external_code, clinic_uid)
select v.product, v.external_code, c.clinic_uid
from (values
  -- Kamla Nagar: the one true cross-product identity
  ('pulse',        'DL-KMN-01', '5129'),
  ('reputationos', '5129',      '5129'),
  ('clove',        '5129',      '5129'),

  -- ReputationOS-only clinics: reputationos + clove alias onto their own canonical row
  ('reputationos', '6015', '6015'), ('clove', '6015', '6015'),
  ('reputationos', '7098', '7098'), ('clove', '7098', '7098'),
  ('reputationos', '7102', '7102'), ('clove', '7102', '7102'),
  ('reputationos', '7103', '7103'), ('clove', '7103', '7103'),
  ('reputationos', '8120', '8120'), ('clove', '8120', '8120'),

  -- Pulse-only clinics: pulse alias onto their own canonical row
  ('pulse', 'DL-RHN-02', 'DL-RHN-02'),
  ('pulse', 'DL-DWK-03', 'DL-DWK-03'),
  ('pulse', 'DL-NOD-04', 'DL-NOD-04'),
  ('pulse', 'MH-BAN-01', 'MH-BAN-01'),
  ('pulse', 'MH-AND-02', 'MH-AND-02'),
  ('pulse', 'MH-THN-03', 'MH-THN-03'),
  ('pulse', 'MH-PUN-04', 'MH-PUN-04'),
  ('pulse', 'KA-IND-01', 'KA-IND-01'),
  ('pulse', 'KA-WFD-02', 'KA-WFD-02'),
  ('pulse', 'KA-JAY-03', 'KA-JAY-03'),
  ('pulse', 'KA-HSR-04', 'KA-HSR-04')
) as v(product, external_code, canonical_code)
join core.clinic c on c.canonical_code = v.canonical_code
on conflict (product, external_code) do nothing;

-- -----------------------------------------------------------------------------
-- 4. ACTORS — union of both products' people. No cross-product overlap.
-- -----------------------------------------------------------------------------
-- Codes: Pulse owners keep their OWNER-* codes. ReputationOS people have no source
-- code, so we mint stable ROS-* codes (idempotent on conflict). All are human.
insert into core.actor (code, name, role, actor_kind) values
  -- Pulse AI owners (engine.py OWNERS)
  ('OWNER-NEHA',    'Neha Sharma',     'cluster_operations', 'human'),
  ('OWNER-VIKRAM',  'Vikram Nair',     'telecalling',        'human'),
  ('OWNER-ROHAN',   'Rohan Iyer',      'revops_analyst',     'human'),
  ('OWNER-ANANYA',  'Ananya Mehra',    'regional_head',      'human'),
  ('OWNER-PRIYA',   'Priya Deshmukh',  'cluster_operations', 'human'),

  -- ReputationOS clinic heads
  ('ROS-HEAD-RITU-MALHOTRA',  'Dr. Ritu Malhotra',  'clinic_head', 'human'),
  ('ROS-HEAD-HARLEEN-KAUR',   'Dr. Harleen Kaur',   'clinic_head', 'human'),
  ('ROS-HEAD-NIYATI-SHAH',    'Dr. Niyati Shah',    'clinic_head', 'human'),
  ('ROS-HEAD-SAGAR-KULKARNI', 'Dr. Sagar Kulkarni', 'clinic_head', 'human'),
  ('ROS-HEAD-NEHA-DESHPANDE', 'Dr. Neha Deshpande', 'clinic_head', 'human'),
  ('ROS-HEAD-KAVYA-REDDY',    'Dr. Kavya Reddy',    'clinic_head', 'human'),

  -- ReputationOS ops executives
  ('ROS-OPS-ANUJ-BATRA',      'Anuj Batra',      'ops_executive', 'human'),
  ('ROS-OPS-MANPREET-SANDHU', 'Manpreet Sandhu', 'ops_executive', 'human'),
  ('ROS-OPS-KUNAL-TRIVEDI',   'Kunal Trivedi',   'ops_executive', 'human'),
  ('ROS-OPS-RASHMI-PATIL',    'Rashmi Patil',    'ops_executive', 'human'),
  ('ROS-OPS-SRIDHAR-RAO',     'Sridhar Rao',     'ops_executive', 'human'),

  -- ReputationOS agents (assigned_agent)
  ('ROS-AGENT-ASHA-MEHTA',   'Asha Mehta',   'agent', 'human'),
  ('ROS-AGENT-KABIR-KHAN',   'Kabir Khan',   'agent', 'human'),
  ('ROS-AGENT-MEERA-RAO',    'Meera Rao',    'agent', 'human'),
  ('ROS-AGENT-NIKHIL-DAS',   'Nikhil Das',   'agent', 'human'),
  ('ROS-AGENT-PRIYA-SHARMA', 'Priya Sharma', 'agent', 'human'),  -- NOT Pulse 'Priya Deshmukh'
  ('ROS-AGENT-ROHAN-SETHI',  'Rohan Sethi',  'agent', 'human'),  -- NOT Pulse 'Rohan Iyer'

  -- ReputationOS manager owners (title-named roles, not individuals)
  ('ROS-MGR-NORTH',      'North Ops Lead',      'manager', 'human'),
  ('ROS-MGR-MUMBAI',     'Mumbai Ops Lead',     'manager', 'human'),
  ('ROS-MGR-SW',         'South West Ops Lead', 'manager', 'human'),
  ('ROS-MGR-SE',         'South East Ops Lead', 'manager', 'human'),

  -- ReputationOS escalation owners (zonal, title-named)
  ('ROS-ESC-DELHI-NCR',  'Delhi NCR Zonal Manager', 'escalation_owner', 'human'),
  ('ROS-ESC-PUNJAB',     'Punjab Zonal Manager',    'escalation_owner', 'human'),
  ('ROS-ESC-GUJARAT',    'Gujarat Zonal Manager',   'escalation_owner', 'human'),
  ('ROS-ESC-MUMBAI',     'Mumbai Zone Manager',     'escalation_owner', 'human'),
  ('ROS-ESC-HYDERABAD',  'Hyderabad Zonal Manager', 'escalation_owner', 'human')
on conflict (code) do nothing;

commit;

-- =============================================================================
-- VERIFICATION (run after seeding; expected counts for v0.1):
--   select count(*) from core.region;        -- 14 (3 band + 5 region + 6 sub_region)
--   select count(*) from core.clinic;        -- 17 (1 matched + 5 repos-only + 11 pulse-only)
--   select count(*) from core.clinic_alias;  -- 24 = 3 (Kamla: pulse+reputationos+clove)
--                                             --    + 10 (5 repos clinics x reputationos+clove)
--                                             --    + 11 (pulse-only x pulse)
--   select count(*) from core.actor;         -- 31 (5 pulse + 6 head + 5 ops + 6 agent + 4 mgr + 5 esc)
--
-- The one cross-product clinic (should return Kamla Nagar with 3 aliases):
--   select c.canonical_code, c.name,
--          array_agg(a.product || ':' || a.external_code order by a.product) as aliases
--   from core.clinic c join core.clinic_alias a using (clinic_uid)
--   group by c.clinic_uid, c.canonical_code, c.name
--   having count(distinct a.product) > 1;
-- =============================================================================
