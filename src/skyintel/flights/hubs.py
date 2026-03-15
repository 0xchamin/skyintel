"""Global air-traffic hubs for ADSB.lol regional polling."""

# (IATA, city, latitude, longitude)
HUBS = [
    # ── North America (10) ──
    ("ATL", "Atlanta",           33.6407,  -84.4277),
    ("JFK", "New York",          40.6413,  -73.7781),
    ("LAX", "Los Angeles",       33.9425, -118.4081),
    ("ORD", "Chicago O'Hare",    41.9742,  -87.9073),
    ("DFW", "Dallas/Fort Worth", 32.8998,  -97.0403),
    ("YYZ", "Toronto",           43.6777,  -79.6248),
    ("SFO", "San Francisco",     37.6213, -122.3790),
    ("IAD", "Washington Dulles", 38.9531,  -77.4565),
    ("MIA", "Miami",             25.7959,  -80.2870),
    ("MEX", "Mexico City",       19.4363,  -99.0721),

    # ── Europe (9) ──
    ("LHR", "London Heathrow",   51.4700,   -0.4543),
    ("CDG", "Paris",             49.0097,    2.5479),
    ("FRA", "Frankfurt",         50.0379,    8.5622),
    ("AMS", "Amsterdam",         52.3105,    4.7683),
    ("IST", "Istanbul",          41.2753,   28.7519),
    ("MAD", "Madrid",            40.4983,   -3.5676),
    ("FCO", "Rome",              41.8003,   12.2389),
    ("WAW", "Warsaw",            52.1657,   20.9671),
    ("OSL", "Oslo",              60.1975,   11.1004),

    # ── Middle East (4) ──
    ("DXB", "Dubai",             25.2532,   55.3657),
    ("DOH", "Doha",              25.2731,   51.6081),
    ("AUH", "Abu Dhabi",         24.4330,   54.6511),
    ("TLV", "Tel Aviv",          32.0055,   34.8854),

    # ── Asia (12) ──
    ("SIN", "Singapore",          1.3644,  103.9915),
    ("HND", "Tokyo Haneda",      35.5494,  139.7798),
    ("ICN", "Seoul Incheon",     37.4602,  126.4407),
    ("PEK", "Beijing",           40.0799,  116.6031),
    ("BKK", "Bangkok",           13.6900,  100.7501),
    ("DEL", "Delhi",             28.5562,   77.1000),
    ("PVG", "Shanghai",          31.1443,  121.8083),
    ("HKG", "Hong Kong",         22.3080,  113.9185),
    ("CMB", "Colombo",            7.1807,   79.8842),
    ("TPE", "Taipei",            25.0797,  121.2342),
    ("KUL", "Kuala Lumpur",       2.7456,  104.6530),
    ("CGK", "Jakarta",           -6.1256,  106.6559),
    ("MNL", "Manila",            14.5086,  121.0198),

    # ── Russia / Ukraine (2) ──
    ("SVO", "Moscow",            55.9726,   37.4146),
    ("IEV", "Kyiv",              50.4019,   30.4499),

    # ── Australia / NZ (4) ──
    ("SYD", "Sydney",           -33.9461,  151.1772),
    ("AKL", "Auckland",         -37.0082,  174.7850),
    ("MEL", "Melbourne",        -37.6690,  144.8410),
    ("PER", "Perth",            -31.9403,  115.9670),

    # ── South America (3) ──
    ("GRU", "São Paulo",        -23.4356,  -46.4731),
    ("EZE", "Buenos Aires",     -34.8222,  -58.5358),
    ("BOG", "Bogotá",            4.7016,  -74.1469),

    # ── Africa (5) ──
    ("JNB", "Johannesburg",     -26.1392,   28.2460),
    ("CAI", "Cairo",             30.1219,   31.4056),
    ("ADD", "Addis Ababa",        8.9779,   38.7993),
    ("NBO", "Nairobi",           -1.3192,   36.9278),
    ("LOS", "Lagos",              6.5774,    3.3212),

    # ── Pacific (1) ──
    ("HNL", "Honolulu",         21.3187, -157.9224),

    # ── China (1) ──
    ("CAN", "Guangzhou",         23.3924,  113.2988),
]
