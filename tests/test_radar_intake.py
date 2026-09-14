import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.plan_radar_intake import decide
from scripts.venue_identity import VenueIdentityError, canonicalize_venue, load_registry


def event(event_id, artist="Artist", showtimes=None, official="https://venue.example/events/show"):
    return {
        "id": event_id,
        "artist": artist,
        "subtitle": None,
        "dates": {"start": "2099-01-01", "end": None},
        "showtimes": showtimes or [],
        "venue": {"id": "the-anthem-washington-dc", "name": "The Anthem", "city": "Washington, DC", "state": "DC", "country": "US"},
        "links": {"official_event": official, "official_tickets": None},
        "lineup": [],
    }


class VenueIdentityTest(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()

    def test_alias_id_name_and_city_normalize_to_declarative_identity(self):
        venue, changes = canonicalize_venue(
            {"id": "anthem-washington-dc", "name": "Anthem", "city": "Washington", "state": "DC", "country": "US"}, self.registry
        )
        self.assertEqual(venue["id"], "the-anthem-washington-dc")
        self.assertEqual(venue["name"], "The Anthem")
        self.assertEqual(venue["city"], "Washington, DC")
        self.assertEqual({change["field"] for change in changes}, {"venue.id", "venue.name", "venue.city"})

    def test_canonical_historical_alias_is_not_a_valid_final_identity(self):
        venue, changes = canonicalize_venue(
            {"id": "blue-note-tokyo-aoyama", "name": "Blue Note Tokyo", "city": "Tokyo", "state": "Tokyo", "country": "JP"}, self.registry
        )
        self.assertEqual(venue["id"], "blue-note-tokyo-minamiaoyama")
        self.assertTrue(changes)

    def test_registry_rejects_duplicate_json_keys(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "venues.json"
            path.write_text('{"schema_version":1,"venues":{"same":{},"same":{}}}')
            with self.assertRaisesRegex(VenueIdentityError, "duplicate JSON key 'same'"):
                load_registry(path)

    def test_new_active_venue_identities_are_registered(self):
        venues = (
            ("blue-note-place-ebisu-tokyo", "Blue Note Place", "Shibuya, Tokyo"),
            ("fillmore-silver-spring-silver-spring-md", "The Fillmore Silver Spring", "Silver Spring"),
            ("keystone-club-tokyo", "KEYSTONE CLUB TOKYO", "Minato, Tokyo"),
            ("songbyrd-music-house-washington-dc", "Songbyrd Music House", "Washington, DC"),
            ("the-pocket-new-york", "The Pocket", "New York"),
            ("toyosu-pit-tokyo", "Toyosu PIT", "Koto, Tokyo"),
            ("victoria-theater-njpac-newark-nj", "Victoria Theater at NJPAC", "Newark"),
            ("wu-tsai-theater-david-geffen-hall-new-york", "Wu Tsai Theater, David Geffen Hall", "New York"),
        )
        for venue_id, name, city in venues:
            with self.subTest(venue_id=venue_id):
                venue, changes = canonicalize_venue(
                    {"id": venue_id, "name": name, "city": city, "state": self.registry["venues"][venue_id]["state"], "country": self.registry["venues"][venue_id]["country"]},
                    self.registry,
                )
                self.assertFalse(changes)
                self.assertEqual(venue["id"], venue_id)

    def test_new_observed_name_and_city_variants_normalize(self):
        cases = (
            ({"id": "songbyrd-music-house-washington-dc", "name": "Songbyrd Music House", "city": "Washington", "state": "DC", "country": "US"}, "songbyrd-music-house-washington-dc", "Washington, DC"),
            ({"id": "toyosu-pit-tokyo", "name": "Toyosu PIT", "city": "Tokyo", "state": "Tokyo", "country": "JP"}, "toyosu-pit-tokyo", "Koto, Tokyo"),
            ({"id": "victoria-theater-njpac-newark-nj", "name": "Victoria Theater, New Jersey Performing Arts Center", "city": "Newark", "state": "NJ", "country": "US"}, "victoria-theater-njpac-newark-nj", "Newark"),
        )
        for raw, expected_id, expected_city in cases:
            with self.subTest(venue_id=raw["id"]):
                venue, changes = canonicalize_venue(raw, self.registry)
                self.assertTrue(changes)
                self.assertEqual(venue["id"], expected_id)
                self.assertEqual(venue["city"], expected_city)

    def test_prioritized_unknown_venue_batch_is_registered(self):
        venues = (
            ("im-a-show-yurakucho-tokyo", "I'M A SHOW", "Chiyoda, Tokyo"),
            ("hokutopia-sakura-hall-tokyo", "Hokutopia Sakura Hall", "Kita, Tokyo"),
            ("sgc-hall-ariake-tokyo", "SGC HALL ARIAKE", "Koto, Tokyo"),
            ("jz-brat-sound-of-tokyo-shibuya", "JZ Brat SOUND OF TOKYO", "Shibuya, Tokyo"),
            ("black-cat-washington-dc", "Black Cat", "Washington, DC"),
            ("westminster-presbyterian-church-washington-dc", "Westminster Presbyterian Church", "Washington, DC"),
            ("public-records-brooklyn", "Public Records", "Brooklyn"),
            ("warsaw-brooklyn", "Warsaw", "Brooklyn"),
            ("grace-rainey-rogers-auditorium-the-met-new-york-ny", "The Grace Rainey Rogers Auditorium", "New York"),
            ("japan-society-new-york-ny", "Japan Society", "New York"),
            ("park-avenue-armory-new-york-ny", "Park Avenue Armory", "New York"),
            ("radio-city-music-hall-new-york-ny", "Radio City Music Hall", "New York"),
            ("harold-prince-theatre-penn-live-arts-philadelphia", "Harold Prince Theatre", "Philadelphia"),
        )
        for venue_id, name, city in venues:
            with self.subTest(venue_id=venue_id):
                identity = self.registry["venues"][venue_id]
                venue, changes = canonicalize_venue(
                    {"id": venue_id, "name": name, "city": city, "state": identity["state"], "country": identity["country"]},
                    self.registry,
                )
                self.assertFalse(changes)
                self.assertEqual(venue["id"], venue_id)

    def test_prioritized_observed_aliases_normalize(self):
        cases = (
            (
                {"id": "jz-brat-sound-of-tokyo-shibuya", "name": "JZ Brat Sound of Tokyo", "city": "Shibuya, Tokyo", "state": "Tokyo", "country": "JP"},
                "jz-brat-sound-of-tokyo-shibuya",
                "JZ Brat SOUND OF TOKYO",
            ),
            (
                {"id": "grace-rainey-rogers-auditorium-the-met-new-york-ny", "name": "Grace Rainey Rogers Auditorium at The Metropolitan Museum of Art", "city": "New York", "state": "NY", "country": "US"},
                "grace-rainey-rogers-auditorium-the-met-new-york-ny",
                "The Grace Rainey Rogers Auditorium",
            ),
            (
                {"id": "radio-city-music-hall-new-york", "name": "Radio City Music Hall", "city": "New York", "state": "NY", "country": "US"},
                "radio-city-music-hall-new-york-ny",
                "Radio City Music Hall",
            ),
        )
        for raw, expected_id, expected_name in cases:
            with self.subTest(venue_id=raw["id"], name=raw["name"]):
                venue, changes = canonicalize_venue(raw, self.registry)
                self.assertTrue(changes)
                self.assertEqual(venue["id"], expected_id)
                self.assertEqual(venue["name"], expected_name)

    def test_second_prioritized_venue_batch_is_registered(self):
        venues = (
            ("kawasaki-shimin-plaza-furusato-theater-kawasaki", "Kawasaki Shimin Plaza — Furusato Theater", "Kawasaki"),
            ("culttz-kawasaki-hall-kawasaki", "カルッツかわさき ホール", "Kawasaki"),
            ("shinyuri-twenty-one-hall-kawasaki", "新百合トウェンティワンホール", "Kawasaki"),
            ("odawara-sannomaru-hall-kanagawa", "小田原三の丸ホール — 大ホール", "Odawara"),
            ("sagamiko-community-center-luxman-hall-sagamihara", "神奈川県立相模湖交流センター — ラックスマン ホール", "Sagamihara"),
            ("totsuka-sakura-plaza-yokohama", "戸塚区民文化センター さくらプラザ — ホール", "Yokohama"),
            ("yokohama-bay-hall", "Yokohama Bay Hall", "Yokohama"),
            ("mizuki-hall-yokohama", "横浜市港北区民文化センター ミズキーホール", "Yokohama"),
            ("yokosuka-arts-theatre-yokosuka", "Yokosuka Arts Theatre", "Yokosuka"),
            ("hibiki-no-mori-okegawa-civic-hall", "響の森 桶川市民ホール", "Okegawa"),
            ("soka-city-culture-hall-saitama", "草加市文化会館", "Soka"),
            ("nippon-budokan-chiyoda-tokyo", "Nippon Budokan", "Chiyoda, Tokyo"),
            ("hamarikyu-asahi-hall-chuo-tokyo", "浜離宮朝日ホール", "Chuo, Tokyo"),
            ("itabashi-city-cultural-hall-small-hall-tokyo", "板橋区立文化会館 — 小ホール", "Itabashi, Tokyo"),
            ("katsushika-symphony-hills-mozart-hall-tokyo", "かつしかシンフォニーヒルズ — モーツァルトホール", "Katsushika, Tokyo"),
        )
        for venue_id, name, city in venues:
            with self.subTest(venue_id=venue_id):
                identity = self.registry["venues"][venue_id]
                venue, changes = canonicalize_venue(
                    {"id": venue_id, "name": name, "city": city, "state": identity["state"], "country": identity["country"]},
                    self.registry,
                )
                self.assertFalse(changes)
                self.assertEqual(venue["id"], venue_id)

    def test_second_prioritized_observed_aliases_normalize(self):
        cases = (
            ({"id": "kawasaki-shimin-plaza-furusato-theater", "name": "Kawasaki Shimin Plaza — Furusato Theater", "city": "Kawasaki", "state": "Kanagawa", "country": "JP"}, "kawasaki-shimin-plaza-furusato-theater-kawasaki", "Kawasaki Shimin Plaza — Furusato Theater"),
            ({"id": "kawasaki-shimin-plaza-kawasaki-jp", "name": "Kawasaki Shimin Plaza — Furusato Theater", "city": "Kawasaki", "state": "Kanagawa", "country": "JP"}, "kawasaki-shimin-plaza-furusato-theater-kawasaki", "Kawasaki Shimin Plaza — Furusato Theater"),
            ({"id": "odawara-sannomaru-hall-kanagawa", "name": "Odawara Sannomaru Hall — Grand Hall", "city": "Odawara", "state": "Kanagawa", "country": "JP"}, "odawara-sannomaru-hall-kanagawa", "小田原三の丸ホール — 大ホール"),
            ({"id": "sagamiko-community-center-luxman-hall-sagamihara", "name": "Kanagawa Prefectural Sagamiko Community Center — Luxman Hall", "city": "Sagamihara", "state": "Kanagawa", "country": "JP"}, "sagamiko-community-center-luxman-hall-sagamihara", "神奈川県立相模湖交流センター — ラックスマン ホール"),
            ({"id": "totsuka-sakura-plaza-yokohama", "name": "Totsuka Civic Cultural Center Sakura Plaza — Hall", "city": "Yokohama", "state": "Kanagawa", "country": "JP"}, "totsuka-sakura-plaza-yokohama", "戸塚区民文化センター さくらプラザ — ホール"),
            ({"id": "mizuki-hall-yokohama", "name": "Yokohama City Kohoku Ward Cultural Center Mizuki Hall", "city": "Yokohama", "state": "Kanagawa", "country": "JP"}, "mizuki-hall-yokohama", "横浜市港北区民文化センター ミズキーホール"),
            ({"id": "yokosuka-arts-theatre-kanagawa", "name": "Yokosuka Arts Theatre", "city": "Yokosuka", "state": "Kanagawa", "country": "JP"}, "yokosuka-arts-theatre-yokosuka", "Yokosuka Arts Theatre"),
            ({"id": "hibiki-no-mori-okegawa-civic-hall", "name": "Hibiki no Mori Okegawa Civic Hall", "city": "Okegawa", "state": "Saitama", "country": "JP"}, "hibiki-no-mori-okegawa-civic-hall", "響の森 桶川市民ホール"),
            ({"id": "soka-city-culture-hall-saitama", "name": "Soka City Culture Hall", "city": "Soka", "state": "Saitama", "country": "JP"}, "soka-city-culture-hall-saitama", "草加市文化会館"),
            ({"id": "hamarikyu-asahi-hall-chuo-tokyo", "name": "Hamarikyu Asahi Hall", "city": "Chuo, Tokyo", "state": "Tokyo", "country": "JP"}, "hamarikyu-asahi-hall-chuo-tokyo", "浜離宮朝日ホール"),
            ({"id": "itabashi-city-cultural-hall-small-hall-tokyo", "name": "Itabashi City Cultural Hall — Small Hall", "city": "Itabashi, Tokyo", "state": "Tokyo", "country": "JP"}, "itabashi-city-cultural-hall-small-hall-tokyo", "板橋区立文化会館 — 小ホール"),
            ({"id": "katsushika-symphony-hills-mozart-hall-tokyo", "name": "Katsushika Symphony Hills — Mozart Hall", "city": "Katsushika, Tokyo", "state": "Tokyo", "country": "JP"}, "katsushika-symphony-hills-mozart-hall-tokyo", "かつしかシンフォニーヒルズ — モーツァルトホール"),
        )
        for raw, expected_id, expected_name in cases:
            with self.subTest(venue_id=raw["id"], name=raw["name"]):
                venue, changes = canonicalize_venue(raw, self.registry)
                self.assertTrue(changes)
                self.assertEqual(venue["id"], expected_id)
                self.assertEqual(venue["name"], expected_name)

    def test_remaining_japanese_venue_batch_is_registered(self):
        venues = (
            ("dai-ichi-seimei-hall-tokyo", "Dai-ichi Seimei Hall", "Tokyo"),
            ("zepp-divercity-tokyo-koto", "Zepp DiverCity(TOKYO)", "Koto, Tokyo"),
            ("tokyo-garden-theater-koto-tokyo", "Tokyo Garden Theater", "Koto, Tokyo"),
            ("machida-civic-hall-tokyo", "町田市民ホール", "Machida"),
            ("meguro-persimmon-hall-tokyo", "Meguro Persimmon Hall — Main Hall", "Tokyo"),
            ("ebisu-the-garden-hall-tokyo", "The Garden Hall", "Meguro, Tokyo"),
            ("polaris-tokyo-minami-aoyama", "POLARIStokyo", "Minato, Tokyo"),
            ("suntory-hall-tokyo", "Suntory Hall — Main Hall", "Tokyo"),
            ("otokichi-meg-musashino-tokyo", "音吉!MEG", "Musashino"),
            ("shibuya-club-quattro-tokyo", "SHIBUYA CLUB QUATTRO", "Shibuya, Tokyo"),
            ("tunnel-tokyo-shinagawa", "TUNNEL TOKYO", "Shinagawa, Tokyo"),
            ("shinjuku-bunka-center-tokyo", "新宿区立新宿文化センター", "Shinjuku, Tokyo"),
            ("cecion-suginami-tokyo", "セシオン杉並 — ホール", "Suginami, Tokyo"),
            ("ryogoku-kokugikan-sumida-tokyo", "両国国技館", "Sumida, Tokyo"),
            ("tachikawa-stage-garden-tachikawa-tokyo", "TACHIKAWA STAGE GARDEN", "Tachikawa"),
            ("bistro-nohga-nohga-hotel-ueno-tokyo", "Bistro NOHGA", "Taito, Tokyo"),
            ("jazz-dining-b-flat-akasaka-tokyo", "Jazz Dining B-flat", "Minato, Tokyo"),
            ("jimbocho-shichoshitsu-tokyo", "神保町 試聴室", "Chiyoda, Tokyo"),
            ("mon-takanawa-box-1000-tokyo", "MoN Takanawa — Box1000", "Minato, Tokyo"),
            ("spotify-o-east-tokyo", "Spotify O-EAST", "Shibuya, Tokyo"),
            ("tokyo-dome-tokyo", "Tokyo Dome", "Bunkyo, Tokyo"),
            ("tessenkai-noh-theatre-tokyo", "銕仙会能楽研修所", "Minato, Tokyo"),
        )
        for venue_id, name, city in venues:
            with self.subTest(venue_id=venue_id):
                identity = self.registry["venues"][venue_id]
                venue, changes = canonicalize_venue(
                    {
                        "id": venue_id,
                        "name": name,
                        "city": city,
                        "state": identity["state"],
                        "country": identity["country"],
                    },
                    self.registry,
                )
                self.assertFalse(changes)
                self.assertEqual(venue["id"], venue_id)

    def test_remaining_japanese_observed_variants_normalize(self):
        cases = (
            ({"id": "dai-ichi-life-hall-chuo-tokyo", "name": "Dai-ichi Life Hall", "city": "Chuo, Tokyo", "state": "Tokyo", "country": "JP"}, "dai-ichi-seimei-hall-tokyo", "Dai-ichi Seimei Hall", "Tokyo"),
            ({"id": "zepp-divercity-tokyo-koto", "name": "Zepp DiverCity (TOKYO)", "city": "Koto City, Tokyo", "state": "Tokyo", "country": "JP"}, "zepp-divercity-tokyo-koto", "Zepp DiverCity(TOKYO)", "Koto, Tokyo"),
            ({"id": "machida-civic-hall-tokyo", "name": "Machida Civic Hall", "city": "Machida", "state": "Tokyo", "country": "JP"}, "machida-civic-hall-tokyo", "町田市民ホール", "Machida"),
            ({"id": "meguro-persimmon-hall-main-hall-tokyo", "name": "Meguro Persimmon Hall — Main Hall", "city": "Meguro, Tokyo", "state": "Tokyo", "country": "JP"}, "meguro-persimmon-hall-tokyo", "Meguro Persimmon Hall — Main Hall", "Tokyo"),
            ({"id": "suntory-hall-main-hall-tokyo", "name": "Suntory Hall — Main Hall", "city": "Minato, Tokyo", "state": "Tokyo", "country": "JP"}, "suntory-hall-tokyo", "Suntory Hall — Main Hall", "Tokyo"),
            ({"id": "otokichi-meg-musashino-tokyo", "name": "Otokichi! MEG", "city": "Musashino", "state": "Tokyo", "country": "JP"}, "otokichi-meg-musashino-tokyo", "音吉!MEG", "Musashino"),
            ({"id": "tunnel-tokyo-shinagawa", "name": "Tunnel Tokyo", "city": "Shinagawa, Tokyo", "state": "Tokyo", "country": "JP"}, "tunnel-tokyo-shinagawa", "TUNNEL TOKYO", "Shinagawa, Tokyo"),
            ({"id": "shinjuku-bunka-center-tokyo", "name": "Shinjuku Bunka Center", "city": "Shinjuku, Tokyo", "state": "Tokyo", "country": "JP"}, "shinjuku-bunka-center-tokyo", "新宿区立新宿文化センター", "Shinjuku, Tokyo"),
            ({"id": "cecion-suginami-tokyo", "name": "Cecion Suginami — Hall", "city": "Suginami, Tokyo", "state": "Tokyo", "country": "JP"}, "cecion-suginami-tokyo", "セシオン杉並 — ホール", "Suginami, Tokyo"),
            ({"id": "ryogoku-kokugikan-sumida-tokyo", "name": "Ryogoku Kokugikan", "city": "Sumida, Tokyo", "state": "Tokyo", "country": "JP"}, "ryogoku-kokugikan-sumida-tokyo", "両国国技館", "Sumida, Tokyo"),
            ({"id": "tachikawa-stage-garden-tachikawa-tokyo", "name": "Tachikawa Stage Garden", "city": "Tachikawa", "state": "Tokyo", "country": "JP"}, "tachikawa-stage-garden-tachikawa-tokyo", "TACHIKAWA STAGE GARDEN", "Tachikawa"),
            ({"id": "bistro-nohga-nohga-hotel-ueno-tokyo", "name": "Bistro NOHGA at NOHGA HOTEL UENO TOKYO", "city": "Tokyo", "state": "Tokyo", "country": "JP"}, "bistro-nohga-nohga-hotel-ueno-tokyo", "Bistro NOHGA", "Taito, Tokyo"),
            ({"id": "jazz-dining-b-flat-akasaka-tokyo", "name": "Jazz Dining B-flat", "city": "Tokyo", "state": "Tokyo", "country": "JP"}, "jazz-dining-b-flat-akasaka-tokyo", "Jazz Dining B-flat", "Minato, Tokyo"),
            ({"id": "jimbocho-shichoshitsu-tokyo", "name": "Jimbocho Shichoshitsu", "city": "Tokyo", "state": "Tokyo", "country": "JP"}, "jimbocho-shichoshitsu-tokyo", "神保町 試聴室", "Chiyoda, Tokyo"),
            ({"id": "mon-takanawa-box-1000-tokyo", "name": "MoN Takanawa — Box 1000", "city": "Tokyo", "state": "Tokyo", "country": "JP"}, "mon-takanawa-box-1000-tokyo", "MoN Takanawa — Box1000", "Minato, Tokyo"),
            ({"id": "spotify-o-east-tokyo", "name": "Spotify O-EAST", "city": "Tokyo", "state": "Tokyo", "country": "JP"}, "spotify-o-east-tokyo", "Spotify O-EAST", "Shibuya, Tokyo"),
            ({"id": "tokyo-dome-tokyo", "name": "Tokyo Dome", "city": "Tokyo", "state": "Tokyo", "country": "JP"}, "tokyo-dome-tokyo", "Tokyo Dome", "Bunkyo, Tokyo"),
            ({"id": "tessenkai-noh-theatre-tokyo", "name": "銕仙会能楽研修所", "city": "Tokyo", "state": "Tokyo", "country": "JP"}, "tessenkai-noh-theatre-tokyo", "銕仙会能楽研修所", "Minato, Tokyo"),
        )
        for raw, expected_id, expected_name, expected_city in cases:
            with self.subTest(venue_id=raw["id"], name=raw["name"]):
                venue, changes = canonicalize_venue(raw, self.registry)
                self.assertTrue(changes)
                self.assertEqual(venue["id"], expected_id)
                self.assertEqual(venue["name"], expected_name)
                self.assertEqual(venue["city"], expected_city)

    def test_us_declarative_venue_coverage_normalizes_every_observed_candidate(self):
        cases = (
            ("metro-baltimore-baltimore-md", "Metro Baltimore", "Baltimore", "MD", "metro-baltimore-baltimore-md", "Metro Baltimore", "Baltimore"),
            ("one-flight-up-new-york", "One Flight Up", "New York", "NY", "one-flight-up-new-york", "One Flight Up", "New York"),
            ("capital-one-hall-tysons", "Capital One Hall", "Tysons", "VA", "capital-one-hall-tysons", "Capital One Hall", "Tysons"),
            ("knockdown-center-queens", "Knockdown Center", "Queens", "NY", "knockdown-center-queens", "Knockdown Center", "Queens"),
            ("alice-tully-hall-lincoln-center-new-york", "Alice Tully Hall", "New York", "NY", "alice-tully-hall-lincoln-center-new-york", "Alice Tully Hall", "New York"),
            ("brooklyn-steel-brooklyn-ny", "Brooklyn Steel", "Brooklyn", "NY", "brooklyn-steel-brooklyn-ny", "Brooklyn Steel", "Brooklyn"),
            ("current-space-baltimore-md", "Current Space", "Baltimore", "MD", "current-space-baltimore-md", "Current Space", "Baltimore"),
            ("hillwood-estate-museum-gardens-washington-dc", "Hillwood Estate, Museum & Gardens", "Washington, DC", "DC", "hillwood-estate-museum-gardens-washington-dc", "Hillwood Estate, Museum & Gardens", "Washington, DC"),
            ("temple-of-dendur-the-met-new-york-ny", "Temple of Dendur at The Metropolitan Museum of Art", "New York", "NY", "temple-of-dendur-the-met-new-york-ny", "Temple of Dendur at The Metropolitan Museum of Art", "New York"),
            ("pioneer-works-brooklyn-ny", "Pioneer Works", "Brooklyn", "NY", "pioneer-works-brooklyn-ny", "Pioneer Works", "Brooklyn"),
            ("the-powerhouse-washington-dc", "The Powerhouse", "Washington, DC", "DC", "the-powerhouse-washington-dc", "The Powerhouse", "Washington, DC"),
            ("district-pier-the-wharf-washington-dc", "District Pier at The Wharf", "Washington, DC", "DC", "district-pier-the-wharf-washington-dc", "District Pier at The Wharf", "Washington, DC"),
            ("anthem-row-washington-dc", "Anthem Row", "Washington", "DC", "anthem-row-washington-dc", "Anthem Row", "Washington, DC"),
            ("martin-luther-king-jr-memorial-library-washington-dc", "Martin Luther King Jr. Memorial Library", "Washington, DC", "DC", "martin-luther-king-jr-memorial-library-washington-dc", "Martin Luther King Jr. Memorial Library", "Washington, DC"),
            ("pie-shop-washington-dc", "Pie Shop", "Washington, DC", "DC", "pie-shop-washington-dc", "Pie Shop", "Washington, DC"),
            ("colden-auditorium", "Colden Auditorium at Kupferberg Center for the Arts", "Flushing", "NY", "colden-auditorium", "Colden Auditorium at Kupferberg Center for the Arts", "Flushing"),
            ("bethany-baptist-church-newark-nj", "Bethany Baptist Church", "Newark", "NJ", "bethany-baptist-church-newark-nj", "Bethany Baptist Church", "Newark"),
            ("dizzys-club-new-york-ny", "Dizzy's Club", "New York City", "NY", "dizzys-club-new-york", "Dizzy's Club at Jazz at Lincoln Center", "New York"),
            ("tonal-park-studios-takoma-park-md", "Tonal Park Studios", "Takoma Park", "MD", "tonal-park-takoma-park-md", "Tonal Park", "Takoma Park"),
            ("njpac-prudential-hall-newark", "Prudential Hall at New Jersey Performing Arts Center", "Newark", "NJ", "prudential-hall-njpac-newark", "Prudential Hall at NJPAC", "Newark"),
            ("library-of-congress-great-hall-washington-dc", "Library of Congress — Great Hall", "Washington, DC", "DC", "library-of-congress-great-hall-washington-dc", "Library of Congress — Great Hall", "Washington, DC"),
            ("theatre-project-baltimore", "Theatre Project", "Baltimore", "MD", "theatre-project-baltimore", "Theatre Project", "Baltimore"),
            ("fringearts-philadelphia", "FringeArts", "Philadelphia", "PA", "fringearts-philadelphia", "FringeArts", "Philadelphia"),
            ("alethia-tanner-park-washington-dc", "Alethia Tanner Park", "Washington", "DC", "alethia-tanner-park-washington-dc", "Alethia Tanner Park", "Washington, DC"),
            ("appel-room-jazz-at-lincoln-center-new-york-ny", "The Appel Room, Frederick P. Rose Hall", "New York", "NY", "the-appel-room-jazz-at-lincoln-center-new-york", "The Appel Room at Jazz at Lincoln Center", "New York"),
            ("embassy-of-slovenia-washington-dc", "Embassy of the Republic of Slovenia", "Washington, DC", "DC", "embassy-of-slovenia-washington-dc", "Embassy of the Republic of Slovenia", "Washington, DC"),
            ("gallery-371-arms-and-armor-the-met-new-york-ny", "Gallery 371, Arms and Armor at The Metropolitan Museum of Art", "New York", "NY", "gallery-371-arms-and-armor-the-met-new-york-ny", "Gallery 371, Arms and Armor at The Metropolitan Museum of Art", "New York"),
            ("national-museum-of-american-history-washington-dc", "National Museum of American History", "Washington, DC", "DC", "national-museum-of-american-history-washington-dc", "National Museum of American History", "Washington, DC"),
            ("merkin-hall-kaufman-music-center-new-york", "Merkin Hall at Kaufman Music Center", "New York", "NY", "merkin-hall-kaufman-music-center-new-york", "Merkin Hall at Kaufman Music Center", "New York"),
            ("national-sawdust-brooklyn-new-york", "National Sawdust", "Brooklyn", "NY", "national-sawdust-brooklyn-ny", "National Sawdust", "Brooklyn"),
            ("richard-j-ernst-community-cultural-center-annandale", "Richard J. Ernst Community Cultural Center", "Annandale", "VA", "richard-j-ernst-community-cultural-center-annandale", "Richard J. Ernst Community Cultural Center", "Annandale"),
            ("underground-arts-philadelphia-pa", "Underground Arts", "Philadelphia", "PA", "underground-arts-philadelphia-pa", "Underground Arts", "Philadelphia"),
            ("jerrys-place-louis-armstrong-center", "Jerry’s Place — The Louis Armstrong Center", "Queens", "NY", "jerrys-place-louis-armstrong-center", "Jerry’s Place — The Louis Armstrong Center", "Queens"),
            ("national-jazz-museum-in-harlem", "The National Jazz Museum in Harlem", "New York", "NY", "national-jazz-museum-in-harlem", "The National Jazz Museum in Harlem", "New York"),
            ("barnes-foundation-philadelphia", "Barnes Foundation", "Philadelphia", "PA", "barnes-foundation-philadelphia", "Barnes Foundation", "Philadelphia"),
            ("quarry-house-tavern-silver-spring", "Quarry House Tavern", "Silver Spring", "MD", "quarry-house-tavern-silver-spring", "Quarry House Tavern", "Silver Spring"),
            ("first-unitarian-congregational-society-brooklyn", "First Unitarian Congregational Society in Brooklyn", "Brooklyn", "NY", "first-unitarian-congregational-society-brooklyn", "First Unitarian Congregational Society in Brooklyn", "Brooklyn"),
            ("lisner-auditorium-washington-dc", "Lisner Auditorium", "Washington, DC", "DC", "lisner-auditorium-washington-dc", "Lisner Auditorium", "Washington, DC"),
            ("shriver-hall-baltimore", "Shriver Hall", "Baltimore", "MD", "shriver-hall-baltimore", "Shriver Hall", "Baltimore"),
            ("echostage-washington-dc", "Echostage", "Washington, DC", "DC", "echostage-washington-dc", "Echostage", "Washington, DC"),
            ("delacorte-theater-new-york-ny", "The Revitalized Delacorte Theater", "New York", "NY", "delacorte-theater-new-york-ny", "The Delacorte Theater", "New York"),
            ("flagg-building-atrium-corcoran-washington-dc", "Flagg Building Atrium, Corcoran School of the Arts & Design", "Washington", "DC", "flagg-building-atrium-corcoran-washington-dc", "Flagg Building Atrium, Corcoran School of the Arts & Design", "Washington, DC"),
            ("warner-theatre-washington-dc", "Warner Theatre", "Washington", "DC", "warner-theatre-washington-dc", "Warner Theatre", "Washington, DC"),
            ("south-jazz-kitchen-philadelphia", "SOUTH Jazz Kitchen", "Philadelphia", "PA", "south-jazz-kitchen-philadelphia", "SOUTH Jazz Kitchen", "Philadelphia"),
            ("pearl-street-warehouse-washington-dc", "Pearl Street Warehouse", "Washington, DC", "DC", "pearl-street-warehouse-washington-dc", "Pearl Street Warehouse", "Washington, DC"),
            ("forest-hills-stadium-queens-new-york", "Forest Hills Stadium", "Queens", "NY", "forest-hills-stadium-queens-new-york", "Forest Hills Stadium", "Queens"),
            ("hank-dietles-tavern-rockville-md", "Hank Dietle's Tavern", "Rockville", "MD", "hank-dietles-tavern-rockville-md", "Hank Dietle's Tavern", "Rockville"),
            ("miracle-theatre-washington-dc", "The Miracle Theatre", "Washington", "DC", "miracle-theatre-washington-dc", "The Miracle Theatre", "Washington, DC"),
            ("lincoln-theatre-washington-dc", "Lincoln Theatre", "Washington", "DC", "lincoln-theatre-washington-dc", "Lincoln Theatre", "Washington, DC"),
            ("cafe-carlyle-new-york-ny", "Café Carlyle", "New York", "NY", "cafe-carlyle-new-york-ny", "Café Carlyle", "New York"),
            ("madison-square-garden-new-york-ny", "Madison Square Garden", "New York", "NY", "madison-square-garden-new-york-ny", "Madison Square Garden", "New York"),
            ("sisters-brooklyn-ny", "Sisters Brooklyn", "Brooklyn", "NY", "sisters-brooklyn-ny", "Sisters", "Brooklyn"),
            ("big-jazz-cafe-washington-dc", "Big Jazz Cafe", "Washington, DC", "DC", "big-jazz-cafe-washington-dc", "Big Jazz Cafe", "Washington, DC"),
            ("barrel-house-cafe-bar-washington-dc", "Barrel House Cafe & Bar", "Washington, DC", "DC", "barrel-house-cafe-bar-washington-dc", "Barrel House Cafe & Bar", "Washington, DC"),
            ("close-up-new-york-city", "Close Up", "New York City", "NY", "close-up-new-york-city", "Close Up", "New York"),
            ("frederick-p-rose-hall-jazz-at-lincoln-center-new-york", "Frederick P. Rose Hall — Jazz at Lincoln Center", "New York", "NY", "frederick-p-rose-hall-jazz-at-lincoln-center-new-york", "Frederick P. Rose Hall", "New York"),
            ("stern-auditorium-perelman-stage-carnegie-hall-new-york", "Stern Auditorium / Perelman Stage at Carnegie Hall", "New York", "NY", "carnegie-hall-stern-auditorium-new-york", "Carnegie Hall — Stern Auditorium / Perelman Stage", "New York"),
            ("rumsey-playfield-central-park-new-york", "Rumsey Playfield at Central Park", "New York", "NY", "rumsey-playfield-central-park-new-york", "Rumsey Playfield at Central Park", "New York"),
            ("warner-theatre-washington-dc", "Warner Theatre", "Washington, DC", "DC", "warner-theatre-washington-dc", "Warner Theatre", "Washington, DC"),
            ("zurcher-gallery-new-york-ny", "Zürcher Gallery", "New York", "NY", "zurcher-gallery-new-york-ny", "Zürcher Gallery", "New York"),
            ("malcolm-x-park-washington-dc", "Malcolm X Park", "Washington", "DC", "meridian-hill-park-washington-dc", "Meridian Hill Park", "Washington, DC"),
            ("palisades-hub-washington-dc", "Palisades Hub", "Washington", "DC", "palisades-hub-washington-dc", "Palisades Hub", "Washington, DC"),
            ("pnc-bank-arts-center-holmdel-nj", "PNC Bank Arts Center", "Holmdel", "NJ", "pnc-bank-arts-center-holmdel-nj", "PNC Bank Arts Center", "Holmdel"),
            ("prudential-hall-njpac-newark-nj", "Prudential Hall, New Jersey Performing Arts Center", "Newark", "NJ", "prudential-hall-njpac-newark", "Prudential Hall at NJPAC", "Newark"),
            ("marian-anderson-hall-kimmel-center-philadelphia-pa", "Marian Anderson Hall at the Kimmel Center", "Philadelphia", "PA", "marian-anderson-hall-kimmel-center-philadelphia-pa", "Marian Anderson Hall at the Kimmel Center", "Philadelphia"),
            ("union-stage-washington-dc", "Union Stage", "Washington, DC", "DC", "union-stage-washington-dc", "Union Stage", "Washington, DC"),
            ("zankel-hall-carnegie-hall-new-york-ny", "Zankel Hall at Carnegie Hall", "New York", "NY", "zankel-hall-carnegie-hall-new-york", "Zankel Hall at Carnegie Hall", "New York"),
        )
        self.assertEqual(len(cases), 67)
        for raw_id, raw_name, raw_city, state, expected_id, expected_name, expected_city in cases:
            with self.subTest(venue_id=raw_id, name=raw_name, city=raw_city):
                venue, _changes = canonicalize_venue(
                    {"id": raw_id, "name": raw_name, "city": raw_city, "state": state, "country": "US"},
                    self.registry,
                )
                self.assertEqual(venue["id"], expected_id)
                self.assertEqual(venue["name"], expected_name)
                self.assertEqual(venue["city"], expected_city)

        canonical_ids = {case[4] for case in cases}
        self.assertEqual(len(canonical_ids), 65)
        for venue_id in canonical_ids:
            with self.subTest(canonical_venue_id=venue_id):
                identity = self.registry["venues"][venue_id]
                venue, changes = canonicalize_venue(
                    {
                        "id": venue_id,
                        "name": identity["name"],
                        "city": identity["city"],
                        "state": identity["state"],
                        "country": identity["country"],
                    },
                    self.registry,
                )
                self.assertFalse(changes)
                self.assertEqual(venue["id"], venue_id)


class IntakeDecisionTest(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()

    def test_identical_official_url_is_a_permitted_archive_duplicate(self):
        canonical = event("canonical-2099")
        candidate = event("candidate-2099")
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "archive_duplicate")
        self.assertEqual(decision["approval"], "permitted")

    def test_distinct_showtimes_stay_in_review_not_automatic_merge(self):
        canonical = event("canonical-2099", artist="Same Artist", showtimes=["18:00"], official="https://venue.example/events/one")
        candidate = event("candidate-2099", artist="Same Artist", showtimes=["21:00"], official="https://venue.example/events/two")
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "review")
        self.assertTrue(decision["evidence"][1]["value"])

    def test_shared_ticket_provider_url_does_not_merge_different_functions(self):
        canonical = event("canonical-2099", artist="First Artist", official="https://venue.example/events/first")
        canonical["links"]["official_tickets"] = "https://tickets.example.com/provider/listing"
        candidate = event("candidate-2099", artist="Second Artist", official="https://venue.example/events/second")
        candidate["links"]["official_tickets"] = "https://tickets.example.com/provider/listing"
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "create")

    def test_generic_ticket_provider_listing_never_archives_same_artist(self):
        canonical = event("canonical-2099", official="https://venue.example/events/first")
        canonical["links"]["official_tickets"] = "https://tickets.example.com/provider/listing"
        candidate = event("candidate-2099", official="https://venue.example/events/second")
        candidate["links"]["official_tickets"] = "https://tickets.example.com/provider/listing"
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "review")

    def test_shared_ticket_url_with_partial_artist_identity_stays_in_review(self):
        canonical = event("canonical-2099", artist="BEAT: Belew Vai Levin Bozzio", official="https://venue.example/events/first")
        canonical["links"]["official_tickets"] = "https://tickets.example.com/event/123"
        candidate = event("candidate-2099", artist="BEAT", official="https://venue.example/events/second")
        candidate["links"]["official_tickets"] = "https://tickets.example.com/event/123"
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "review")

    def test_trailing_slash_is_not_an_exact_official_event_url(self):
        canonical = event("canonical-2099", official="https://venue.example/events/show")
        candidate = event("candidate-2099", official="https://venue.example/events/show/")
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "review")

    def test_shared_coming_soon_page_is_never_duplicate_evidence(self):
        canonical = event("canonical-2099", official="https://venue.example/event/coming-soon")
        candidate = event("candidate-2099", official="https://venue.example/event/coming-soon")
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "review")

    def test_shared_ticket_url_with_separate_showtimes_stays_in_review(self):
        canonical = event("canonical-2099", showtimes=["18:00"], official="https://venue.example/events/first")
        canonical["links"]["official_tickets"] = "https://tickets.example.com/event/123"
        candidate = event("candidate-2099", showtimes=["21:00"], official="https://venue.example/events/second")
        candidate["links"]["official_tickets"] = "https://tickets.example.com/event/123"
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "review")

    def test_factual_difference_never_becomes_replace_without_a_decision_record(self):
        canonical = event("canonical-2099", official="https://venue.example/events/old")
        candidate = event("candidate-2099", official="https://venue.example/events/new")
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "review" if decision["action"] == "review" else "create")


if __name__ == "__main__":
    unittest.main()
