"""Global air-traffic hubs for ADSB.lol regional polling."""

# (IATA, city, latitude, longitude)
HUBS = [
    # ── North America (8) ──
    ("ATL", "Atlanta",           33.6407,  -84.4277),
    ("JFK", "New York",          40.6413,  -73.7781),
    ("LAX", "Los Angeles",       33.9425, -118.4081),
    ("ORD", "Chicago O'Hare",    41.9742,  -87.9073),
    ("DFW", "Dallas/Fort Worth", 32.8998,  -97.0403),
    ("YYZ", "Toronto",           43.6777,  -79.6248),
    ("SFO", "San Francisco",     37.6213, -122.3790),
    ("IAD", "Washington Dulles", 38.9531,  -77.4565),

    # ── Europe (8) ──
    ("LHR", "London Heathrow",   51.4700,   -0.4543),
    ("CDG", "Paris",             49.0097,    2.5479),
    ("FRA", "Frankfurt",         50.0379,    8.5622),
    ("AMS", "Amsterdam",         52.3105,    4.7683),
    ("IST", "Istanbul",          41.2753,   28.7519),
    ("MAD", "Madrid",            40.4983,   -3.5676),
    ("FCO", "Rome",              41.8003,   12.2389),
    ("WAW", "Warsaw",            52.1657,   20.9671),

    # ── Middle East (4) ──
    ("DXB", "Dubai",             25.2532,   55.3657),
    ("DOH", "Doha",              25.2731,   51.6081),
    ("AUH", "Abu Dhabi",         24.4330,   54.6511),
    ("TLV", "Tel Aviv",          32.0055,   34.8854),

    # ── Asia (6) ──
    ("SIN", "Singapore",          1.3644,  103.9915),
    ("HND", "Tokyo Haneda",      35.5494,  139.7798),
    ("ICN", "Seoul Incheon",     37.4602,  126.4407),
    ("PEK", "Beijing",           40.0799,  116.6031),
    ("BKK", "Bangkok",           13.6900,  100.7501),
    ("DEL", "Delhi",             28.5562,   77.1000),

    # ── Australia / NZ (2) ──
    ("SYD", "Sydney",           -33.9461,  151.1772),
    ("AKL", "Auckland",         -37.0082,  174.7850),

    # ── South America (3) ──
    ("GRU", "São Paulo",        -23.4356,  -46.4731),
    ("EZE", "Buenos Aires",     -34.8222,  -58.5358),
    ("BOG", "Bogotá",            4.7016,  -74.1469),

    # ── Africa (2) ──
    ("JNB", "Johannesburg",     -26.1392,   28.2460),
    ("CAI", "Cairo",             30.1219,   31.4056),
]
