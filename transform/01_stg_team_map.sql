-- transform/01_stg_team_map.sql
-- Reference dimension: one row per NBA franchise mapping the identifiers used
-- across our sources. Numbered 01 so it builds before anything that joins on it.
--   full_name  — CTG's team name (the key mart_team_style uses)
--   bbref_abbr — Basketball-Reference 3-letter code (note BBref quirks:
--                BRK not BKN, CHO not CHA, PHO not PHX)
--   ctg_short  — CTG's city-only short name (used in CTG shooting/context exports)
-- Future DRY: stg_ctg_team still inlines its own city->full map; it could adopt
-- this dimension later.

select * from (values
    ('Atlanta Hawks',          'ATL', 'Atlanta'),
    ('Boston Celtics',         'BOS', 'Boston'),
    ('Brooklyn Nets',          'BRK', 'Brooklyn'),
    ('Charlotte Hornets',      'CHO', 'Charlotte'),
    ('Chicago Bulls',          'CHI', 'Chicago'),
    ('Cleveland Cavaliers',    'CLE', 'Cleveland'),
    ('Dallas Mavericks',       'DAL', 'Dallas'),
    ('Denver Nuggets',         'DEN', 'Denver'),
    ('Detroit Pistons',        'DET', 'Detroit'),
    ('Golden State Warriors',  'GSW', 'Golden State'),
    ('Houston Rockets',        'HOU', 'Houston'),
    ('Indiana Pacers',         'IND', 'Indiana'),
    ('Los Angeles Clippers',   'LAC', 'LA Clippers'),
    ('Los Angeles Lakers',     'LAL', 'LA Lakers'),
    ('Memphis Grizzlies',      'MEM', 'Memphis'),
    ('Miami Heat',             'MIA', 'Miami'),
    ('Milwaukee Bucks',        'MIL', 'Milwaukee'),
    ('Minnesota Timberwolves', 'MIN', 'Minnesota'),
    ('New Orleans Pelicans',   'NOP', 'New Orleans'),
    ('New York Knicks',        'NYK', 'New York'),
    ('Oklahoma City Thunder',  'OKC', 'Oklahoma City'),
    ('Orlando Magic',          'ORL', 'Orlando'),
    ('Philadelphia 76ers',     'PHI', 'Philadelphia'),
    ('Phoenix Suns',           'PHO', 'Phoenix'),
    ('Portland Trail Blazers', 'POR', 'Portland'),
    ('Sacramento Kings',       'SAC', 'Sacramento'),
    ('San Antonio Spurs',      'SAS', 'San Antonio'),
    ('Toronto Raptors',        'TOR', 'Toronto'),
    ('Utah Jazz',              'UTA', 'Utah'),
    ('Washington Wizards',     'WAS', 'Washington')
) as t(full_name, bbref_abbr, ctg_short)

-- ASSERTIONS (enforced by run.py):
-- ASSERT == 30: SELECT count(*) FROM stg_team_map
-- ASSERT == 30: SELECT count(DISTINCT bbref_abbr) FROM stg_team_map
-- ASSERT == 30: SELECT count(DISTINCT full_name) FROM stg_team_map
