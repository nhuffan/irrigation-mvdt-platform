INSERT INTO reservoirs (
    id,
    code,
    name,
    province,
    data_status,
    mvdt_level,
    description,
    location
)
VALUES (
    gen_random_uuid(),
    'DT001',
    'Dau Tieng Reservoir',
    'Tay Ninh',
    'MVDT_AVAILABLE',
    3,
    'Development seed record for API integration testing.',
    ST_SetSRID(
        ST_MakePoint(106.30, 11.35),
        4326
    )
) ON CONFLICT (code) DO NOTHING;


INSERT INTO reservoirs (
    id,
    code,
    name,
    province,
    data_status,
    mvdt_level,
    description,
    location
)
VALUES (
    gen_random_uuid(),
    'DEMO002',
    'Example Reservoir',
    'Example Province',
    'DATA_COLLECTION',
    1,
    'Placeholder record for platform testing.',
    ST_SetSRID(
        ST_MakePoint(106.00, 11.00),
        4326
    )
) ON CONFLICT (code) DO NOTHING;
