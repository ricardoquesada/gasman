
# level name, file name
levels = (
    ('Learning to Move',        'level1'),
    ('Learning to Fart',        'level0'),
    ('Bad Guy',                 'level1_1'),
    ('Bad Guys',                'level1_2'),
    ('Learning to Aim',         'level2_1'),
    ('Long Jump',               'level4_2'),
    ('High Jump',               'level4_1'),
    ('Learning to Aim II',      'level6'),
    ('Fart Fart',               'level5_1'),
    ('Fart Fart Again',         'level2'),
    ('Fart Aim Fart',           'level3'),
    ('Triple Skill Farting',    'level5'),
    ('Double Farting',          'level4'),
    ('Hurry Up',                'level7'),
    ('Hurry Up II',             'level8'),
    ('Slipery When Wet',        'level9'),
    ('Farty Farty',             'level10'),
    ('Final Battle',            'level11'),
    )


def get_level_filename( idx ):
    return 'levels/%s.svg' % (levels[idx][1])

def get_level_name( idx ):
    return levels[idx][0]
