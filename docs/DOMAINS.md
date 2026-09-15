# Geographic Domains

Listening Notes has two native live-music domains. They share one data model
and editorial standard, but not the same travel question.

## Greater Tokyo / Kantō (`tokyo_kanto`)

Tokyo, Yokohama, Kawasaki, Saitama, Chiba, and realistically accessible Kantō
performances belong here when musically justified. The central question is
usually whether a performance is worth building the evening around—not whether
it merits a flight to Japan.

Tsuyoshi Yamamoto is the current narrative guide. His unfinished Tokyo search
makes verified appearances especially important to research, while editorial
judgment still determines inclusion; a selected North American appearance keeps
its documented S+ treatment. Jazz House ALFIE in Roppongi is a priority venue
for future research. Jazz in Japan is an important curated discovery source;
link to and attribute it, but never mirror its articles.

## US corridor (`us_corridor`)

- **Local:** DC, Arlington, Alexandria, Bethesda/North Bethesda, immediate DC.
- **Short trip:** Baltimore.
- **Regional trip:** Philadelphia, Newark, New York City.
- **Special trip:** farther destinations only when the performance warrants it.

## RADAR browsing scenes

The two domains are peers in RADAR. `radar_area` lives on the canonical venue
in `radar/venue_identities.json` and organizes browsing without changing an
event's factual city or editorial travel classification. In the US corridor,
the visible sequence from Arlington is DMV / local scene, Baltimore,
Philadelphia, Newark, New York. It is an editorial order, not a distance
calculation. Columbia, Vienna, North Bethesda, Washington, Oxon Hill, and the
documented immediate DC localities in the registry belong to DMV. Brooklyn,
Queens, and Flushing belong to New York; Newark remains separate. Holmdel is
grouped as New Jersey, not Newark.

Tokyo is its own scene: every registered venue in Tokyo prefecture belongs to
it, whether the displayed `venue.city` says Tokyo, a ward plus Tokyo, or a
separate Tokyo municipality. Kanagawa / Kantō holds Kawasaki, Yokohama, and
other registered Kanagawa venues; Saitama / Kantō is separate. These scenes
are part of the native Greater Tokyo / Kantō domain. New scenes require an
explicit registry decision and a validated controlled value; `unassigned`
keeps unresolved venues visible under a review label until that decision.

## Future place knowledge

Events identify a stable `venue.id`; canonical venue records already hold
`radar_area` and can later hold neighborhood,
station, musical identity, personal notes, and nearby places without changing
event IDs or duplicating bilingual event records. Do not build a venue app or
travel guide until verified knowledge warrants it.
