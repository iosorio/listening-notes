# RADAR — resolución de duplicados, 2026-09-11

## Resultado

Se materializaron **11 duplicados** (8 de los 12 inicialmente clasificados y los 3 reviews musicales investigados). Se dividieron 5 lotes mixtos, se conservaron 11 candidatos residuales y se retiraron del inbox 3 lotes íntegramente duplicados. Los 8 archivos de evidencia preservan el JSON completo original tanto como objeto como texto UTF-8 exacto, su SHA-256, ruta, candidatos, canónicos y decisiones.

Tres duplicados confirmados permanecen activos porque sus residuales preexistentes no pasan validación individual. No se corrigieron ni se dividieron esos lotes. Chuck Brown era un falso positivo por URL general del festival: permanece activo como create. Eddie Palmieri histórico permanece intacto en review.

No se materializó ningún create ni review. No se modificó ningún evento canónico ni ningún campo de los candidatos residuales. No hubo commit, push, merge, rebase ni reset.

## Conteos del planificador

| Estado | create | archive_duplicate | review | merge | replace |
| --- | ---: | ---: | ---: | ---: | ---: |
| Inicial, diff heredado | 491 | 12 | 4 | 0 | 0 |
| Tras corregir la URL general, antes de decisiones investigadas | 492 | 11 | 4 | 0 | 0 |
| Final, tras materializar 11 | 492 | 3 | 1 | 0 | 0 |

El manifiesto registra 16 decisiones: 14 archive_duplicate, 1 create y 1 review. De las 14 decisiones de archivo, 11 son ejecutables y 3 tienen materialization.status=blocked_residual_validation. Los reviews investigados se autorizan en el manifiesto con evidencia vinculada a hashes; no se convierte una coincidencia artista–venue–fecha en regla automática de archivo.

## Los 12 duplicados inicialmente clasificados

En las 11 coincidencias válidas, la URL específica literal, el canónico asociado, el rango de fechas y los horarios registrados coinciden. Las diferencias factuales restantes se conservan íntegramente en factual_diff_raw del manifiesto; no se copian al canónico. La coincidencia número 1 de la tabla no cumple la condición de URL específica y fue rechazada.

| Candidato | Canónico asociado | SHA-256 del lote original | Evidencia oficial | Resultado |
| --- | --- | --- | --- | --- |
| Chuck Brown Band — DC JazzFest<br>`chuck-brown-band-donald-harrison-dc-jazzfest-2026-09-06` | `african-rhythms-alumni-randy-weston-centennial-dc-jazzfest-2026-09-06` (asociación rechazada) | `ed3162d22d408c05fb7b0a3f97f40ad21082a32989614c374b2c1b6ad464b1e0` | [Página oficial](https://www.dcjazzfest.org/lineup-2026) | Falso positivo; create, no materializado |
| JLCO / From Cuba to the Crescent City<br>`jlco-wynton-marsalis-from-cuba-to-crescent-city-new-york-2026-10-23` | `wynton-marsalis-from-cuba-to-crescent-city-jalc-2026-10-23` | `d0d8769c320216c6cb212af7a0ecb5a59b4430d6b8e236c914af71dd37108664` | [Página oficial](https://jazz.org/concert/from-cuba-to-the-crescent-city-the-jazz-at-lincoln-center-orchestra-with-wynton-marsalis/) | Duplicado confirmado; lote intacto, bloqueado |
| Eddie Palmieri Experience — 2026<br>`eddie-palmieri-experience-jalc-rose-theater-nyc-2026-11-13` | `eddie-palmieri-experience-jalc-2026-11-13` | `b6e6ad509ff72a8fa72c984afa70b33f68260e48908708dcc3ca810aef8f2208` | [Página oficial](https://jazz.org/concert/eddie-palmieri-experience-an-all-star-celebration/) | Duplicado confirmado; lote intacto, bloqueado |
| JLCO / Swinging Cities<br>`jlco-wynton-marsalis-swinging-cities-new-york-2026-11-06` | `wynton-marsalis-swinging-cities-jazz-at-lincoln-center-2026-11-06` | `f67892bb0752ea9539d08c230481263a1995471b9ab221f1f0f35972371c12df` | [Página oficial](https://jazz.org/concert/marsalis-swinging-cities-the-jazz-at-lincoln-center-orchestra-with-wynton-marsalis/) | Archivado |
| Tsuyoshi Yamamoto — Keystone, 15 septiembre<br>`tsuyoshi-yamamoto-keystone-club-tokyo-2026-09-15` | `tsuyoshi-yamamoto-night-keystone-club-tokyo-2026-09-15` | `14af04886f1562c977c0890bdb700b3a41a7b038f7006569bdb62808dcc82842` | [Página oficial](https://keystoneclubtokyo.com/html/schedule/%E5%B1%B1%E6%9C%AC%E5%89%9B-night-3/) | Archivado |
| West Road Blues Band<br>`west-road-blues-band-cotton-club-tokyo-2026-09-30` | `west-road-blues-band-cotton-club-2026-09-30` | `027b6943c63fcacb8e998591b57d8f2a29dd53d5dc3c9f4032094f7f73c9c827` | [Página oficial](https://www.cottonclubjapan.co.jp/jp/sp/artists/westroad-bluesband-260930/) | Archivado |
| Plaza Afternoon Jazz — Kawasaki<br>`plaza-afternoon-jazz-final-yamamoto-sato-kawasaki-2026-10-03` | `masahiko-satoh-tsuyoshi-yamamoto-kawasaki-shimin-plaza-2026-10-03` | `015f80e6c67cc26f493cd7fcced0da3072874bfa6b92a8445146bf86f880dbb0` | [Página oficial](https://www.kawasaki-shiminplaza.jp/event/detail?id=15726) | Archivado |
| John Scofield / Electrospective<br>`john-scofield-electrospective-hamilton-washington-dc-2026-10-22` | `john-scofield-electrospective-hamilton-2026-10-22` | `015f80e6c67cc26f493cd7fcced0da3072874bfa6b92a8445146bf86f880dbb0` | [Página oficial](https://wl.eventim.us/event/john-scofields-electrospective/685362?afflky=TheHamiltonDC) | Archivado |
| Niladri Kumaar<br>`niladri-kumaar-space-between-notes-njpac-newark-2026-11-06` | `niladri-kumaar-space-between-notes-njpac-2026-11-06` | `e42bcd9942f26e05c953a6b85aeac3c3dafbc78ec76bfd9eb83d1db10ff8625a` | [Página oficial](https://www.njpac.org/event/niladri-kumaar/) | Archivado |
| Miles @100<br>`miles-100-jon-faddis-njpac-newark-2026-11-12` | `miles-100-jon-faddis-friends-njpac-2026-11-12` | `e42bcd9942f26e05c953a6b85aeac3c3dafbc78ec76bfd9eb83d1db10ff8625a` | [Página oficial](https://www.njpac.org/event/miles-100/) | Archivado |
| Sacred Visions<br>`sacred-visions-oru-de-oro-njpac-newark-2026-12-19` | `michele-rosewoman-new-yor-uba-sacred-visions-njpac-2026-12-19` | `e42bcd9942f26e05c953a6b85aeac3c3dafbc78ec76bfd9eb83d1db10ff8625a` | [Página oficial](https://www.njpac.org/event/sacred-visions/) | Archivado |
| Tsuyoshi Yamamoto / Masahiko Satoh — Kawasaki<br>`tsuyoshi-yamamoto-masahiko-satoh-kawasaki-shimin-plaza-2026-10-03` | `masahiko-satoh-tsuyoshi-yamamoto-kawasaki-shimin-plaza-2026-10-03` | `63cc2234ef40d1cf540abe4242ac7b00b95b452bd32afc644c71404b30909b83` | [Página oficial](https://www.kawasaki-shiminplaza.jp/event/detail?id=15726) | Duplicado confirmado; lote intacto, bloqueado |

### Diff factual revisado

Estos campos tienen valores diferentes entre candidato y canónico; sus valores exactos antes/después están en el manifiesto. Es una comparación documental, no una propuesta de editar datos.

| Candidato | Campos distintos |
| --- | --- |
| Aaron Parks Trio | `subtitle`, `showtimes`, `venue`, `links`, `tickets`, `sources`, `factual_description` |
| Chuck Brown Band — DC JazzFest | Ver instantánea de la decisión inicial |
| JLCO / From Cuba to the Crescent City | `venue`, `lineup`, `tickets`, `sources`, `factual_description` |
| Eddie Palmieri Experience — 2026 | `venue`, `links`, `lineup`, `tickets`, `sources`, `factual_description` |
| Stanley Jordan Trio | `artist`, `subtitle`, `venue`, `links`, `lineup`, `tickets`, `sources`, `factual_description` |
| JLCO / Swinging Cities | `subtitle`, `venue`, `links`, `lineup`, `tickets`, `sources`, `factual_description` |
| Tsuyoshi Yamamoto — Keystone, 15 septiembre | `venue`, `tickets`, `sources`, `factual_description` |
| Ravi Coltrane Centennial | `venue`, `links`, `lineup`, `tickets`, `sources`, `factual_description` |
| West Road Blues Band | `subtitle`, `venue`, `links`, `lineup`, `tickets`, `sources`, `factual_description` |
| Plaza Afternoon Jazz — Kawasaki | `artist`, `venue`, `links`, `lineup`, `tickets`, `sources`, `factual_description` |
| John Scofield / Electrospective | `subtitle`, `lineup`, `tickets`, `sources`, `factual_description` |
| Niladri Kumaar | `venue`, `lineup`, `tickets`, `sources`, `factual_description` |
| Miles @100 | `venue`, `links`, `lineup`, `tickets`, `sources`, `factual_description` |
| Sacred Visions | `artist`, `venue`, `links`, `lineup`, `tickets`, `sources`, `factual_description` |
| Tsuyoshi Yamamoto / Masahiko Satoh — Kawasaki | `artist`, `venue`, `links`, `lineup`, `tickets`, `sources`, `factual_description` |

## Los tres reviews musicales

| Candidato → canónico | Decisión | Evidencia determinante |
| --- | --- | --- |
| `aaron-parks-trio-village-vanguard-new-york-2026-10-27` → `aaron-parks-trio-village-vanguard-2026-10-27` | archive_duplicate; archivado | Ambos registros cubren la residencia completa del 27 de octubre al 1 de noviembre con Ben Street y Billy Hart. El programa oficial confirma ese trío y la FAQ los dos sets de 20:00/22:00. El canónico no tenía horarios; no describía una función distinta. [Fuente oficial 1](https://villagevanguard.com/), [Fuente oficial 2](https://villagevanguard.com/faq), [Fuente oficial 3](https://vv.squadup.com/artists/aaron-parks-trio) |
| `stanley-jordan-trio-keystone-korner-baltimore-2026-10-02` → `stanley-jordan-keystone-korner-baltimore-2026-10-02` | archive_duplicate; archivado | El calendario del artista confirma el trío con Kenwood Dennard y Wes Wirth el 2 y 3 de octubre. El ticketing autorizado enumera las cuatro funciones presenciales de 18:00/20:30. Ambos registros cubren las mismas cuatro funciones; la URL de tickets del candidato coincide con official_event del canónico. [Fuente oficial 1](https://stanleyjordan.com/en/tourdates/?v=1), [Fuente oficial 2](https://www.instantseats.com/?VenueID=514&artistid=37616&fuseaction=home.artist) |
| `ravi-coltrane-centennial-village-vanguard-new-york-2026-10-13` → `ravi-coltrane-quartet-centennial-village-vanguard-2026-10-13` | archive_duplicate; archivado | Ambos registros cubren toda la residencia Centennial Celebration del 13 al 18 de octubre. El venue publica un único programa semanal con una formación para 13–15 y otra para 16–18; el candidato no restringe el evento a una de esas formaciones. [Fuente oficial 1](https://villagevanguard.com/) |

Verificación: 2026-09-11. La página de SquadUp de Aaron Parks no expuso tickets fechados en la extracción; no se usó como prueba independiente. Las páginas específicas de Niladri Kumaar y Miles @100 no se pudieron extraer directamente; el [calendario oficial de NJPAC](https://www.njpac.org/tickets-events/) corroboró los programas, fechas y 19:30. Las limitaciones de acceso están registradas en el manifiesto. No queda un review musical pendiente por falta de evidencia.

## Lotes divididos y residuales

Cada residual conserva todos sus campos y el resto del sobre del lote. Sólo se retiraron los candidatos duplicados; la serialización JSON del lote puede cambiar. Cada original se puede recuperar byte por byte desde source.original_text.

| Lote original / activo residual | Candidatos archivados | Candidatos residuales intactos |
| --- | --- | --- |
| `radar/inbox/curated/takeo-moriyama-swinging-cities-2026-08-29-discovery.json` | `jlco-wynton-marsalis-swinging-cities-new-york-2026-11-06` | `takeo-moriyama-2days-shinjuku-pit-inn-tokyo-2026-09-11` |
| `radar/inbox/curated/village-vanguard-gilmore-ravi-hersch-october-2026-2026-08-29-discovery.json` | `ravi-coltrane-centennial-village-vanguard-new-york-2026-10-13` | `marcus-gilmore-new-orchestra-village-vanguard-new-york-2026-10-06`<br>`fred-hersch-trio-plus-two-village-vanguard-new-york-2026-10-20` |
| `radar/inbox/curated/west-road-shipp-parker-2026-08-30-discovery.json` | `west-road-blues-band-cotton-club-tokyo-2026-09-30` | `matthew-shipp-william-parker-roulette-brooklyn-2026-12-04` |
| `radar/inbox/curated/yamamoto-kawasaki-dmv-roulette-tokyo-2026-08-29-discovery.json` | `plaza-afternoon-jazz-final-yamamoto-sato-kawasaki-2026-10-03`<br>`john-scofield-electrospective-hamilton-washington-dc-2026-10-22` | `katherine-young-biomes-roulette-brooklyn-2026-09-17`<br>`kaho-nakamura-billboard-live-tokyo-solo-2026-10-12`<br>`m3-festival-roulette-brooklyn-2026-11-07`<br>`matana-roberts-off-the-record-roulette-brooklyn-2026-11-11` |
| `radar/inbox/curated/yamamoto-keystone-njpac-fall-2026-2026-08-28-discovery.json` | `niladri-kumaar-space-between-notes-njpac-newark-2026-11-06`<br>`miles-100-jon-faddis-njpac-newark-2026-11-12`<br>`sacred-visions-oru-de-oro-njpac-newark-2026-12-19` | `tsuyoshi-yamamoto-trio-keystone-club-tokyo-2026-09-01`<br>`tsuyoshi-yamamoto-trio-keystone-club-tokyo-2026-09-08`<br>`beat-king-crimson-njpac-newark-2026-11-09` |

### Lotes completos retirados del inbox

- `radar/inbox/curated/aaron-parks-trio-village-vanguard-2026-08-30-discovery.json`: `aaron-parks-trio-village-vanguard-new-york-2026-10-27`. Original completo recuperable en el archivo de evidencia cuyo nombre empieza por `95b9029246595db4a257b96473c90e4cbc411f6223ae1d69603345da9bb4fa82`.
- `radar/inbox/curated/stanley-jordan-keystone-baltimore-2026-08-30-discovery.json`: `stanley-jordan-trio-keystone-korner-baltimore-2026-10-02`. Original completo recuperable en el archivo de evidencia cuyo nombre empieza por `dd48832bcb27e92f3cad6c56e562fa6eac4062506360e2755ae1863b31661cd8`.
- `radar/inbox/curated/tsuyoshi-yamamoto-keystone-night-2026-09-15-discovery.json`: `tsuyoshi-yamamoto-keystone-club-tokyo-2026-09-15`. Original completo recuperable en el archivo de evidencia cuyo nombre empieza por `14af04886f1562c977c0890bdb700b3a41a7b038f7006569bdb62808dcc82842`.

### Archivos de evidencia creados

- `radar/inbox/review/decisions/95b9029246595db4a257b96473c90e4cbc411f6223ae1d69603345da9bb4fa82-aaron-parks-trio-village-vanguard-2026-08-30-discovery.json`
- `radar/inbox/review/decisions/dd48832bcb27e92f3cad6c56e562fa6eac4062506360e2755ae1863b31661cd8-stanley-jordan-keystone-baltimore-2026-08-30-discovery.json`
- `radar/inbox/review/decisions/f67892bb0752ea9539d08c230481263a1995471b9ab221f1f0f35972371c12df-takeo-moriyama-swinging-cities-2026-08-29-discovery.json`
- `radar/inbox/review/decisions/14af04886f1562c977c0890bdb700b3a41a7b038f7006569bdb62808dcc82842-tsuyoshi-yamamoto-keystone-night-2026-09-15-discovery.json`
- `radar/inbox/review/decisions/078c95ce2b8a37ce044a1a9190212771eed69c731794cd185afd9c98109cac31-village-vanguard-gilmore-ravi-hersch-october-2026-2026-08-29-discovery.json`
- `radar/inbox/review/decisions/027b6943c63fcacb8e998591b57d8f2a29dd53d5dc3c9f4032094f7f73c9c827-west-road-shipp-parker-2026-08-30-discovery.json`
- `radar/inbox/review/decisions/015f80e6c67cc26f493cd7fcced0da3072874bfa6b92a8445146bf86f880dbb0-yamamoto-kawasaki-dmv-roulette-tokyo-2026-08-29-discovery.json`
- `radar/inbox/review/decisions/e42bcd9942f26e05c953a6b85aeac3c3dafbc78ec76bfd9eb83d1db10ff8625a-yamamoto-keystone-njpac-fall-2026-2026-08-28-discovery.json`

## Bloqueos de validación: no se materializaron

Los siguientes errores existen en candidatos no duplicados del lote original. La autorización exige que los residuales pasen validación y permanezcan intactos. No se adivinaron monedas ni se repararon metadatos. Cada lote conserva su SHA-256 original.

### JLCO / From Cuba to the Crescent City

- Duplicado: `jlco-wynton-marsalis-from-cuba-to-crescent-city-new-york-2026-10-23`.
- Lote intacto: `radar/inbox/curated/jalc-wynton-wycliffe-fall-2026-2026-08-28-discovery.json`.
- SHA-256: `d0d8769c320216c6cb212af7a0ecb5a59b4430d6b8e236c914af71dd37108664`.
- Residual `wycliffe-gordon-welcome-to-georgia-town-jalc-new-york-2026-10-09`: enrichment.missing contains unsupported individual_septet_personnel and individual_chorus_personnel.

### Eddie Palmieri Experience — 2026

- Duplicado: `eddie-palmieri-experience-jalc-rose-theater-nyc-2026-11-13`.
- Lote intacto: `radar/inbox/curated/sora-cortex-palmieri-2026-08-29-discovery.json`.
- SHA-256: `b6e6ad509ff72a8fa72c984afa70b33f68260e48908708dcc3ca810aef8f2208`.
- Residual `sora-ichikawa-concept-band-jazz-house-alfie-tokyo-2026-09-12`: tickets.currency is not explicit; enrichment.missing also contains nonstandard labels.
- Residual `cortex-howard-theatre-washington-dc-2026-10-06`: enrichment.status is not complete, pending, or unavailable.

### Tsuyoshi Yamamoto / Masahiko Satoh — Kawasaki

- Duplicado: `tsuyoshi-yamamoto-masahiko-satoh-kawasaki-shimin-plaza-2026-10-03`.
- Lote intacto: `radar/inbox/curated/yamamoto-satoh-interpretations-2026-08-29-discovery.json`.
- SHA-256: `63cc2234ef40d1cf540abe4242ac7b00b95b452bd32afc644c71404b30909b83`.
- Residual `interpretations-hemingway-andonovska-howard-roulette-brooklyn-2026-12-03`: enrichment.missing contains unsupported special_guest.

La primera ejecución temporal de los 14 duplicados detectó estos errores al validar los residuales normalizados. No se aplicó esa ejecución al checkout local. Se reforzó la prevalidación del materializador para detectar esos errores **antes de cualquier escritura**, y se repitió todo desde una segunda worktree limpia basada en d3d8006 con las 11 decisiones elegibles.

## Evidencia insuficiente / histórico

- `eddie-palmieri-2019-user-confirmed`: evidencia histórica incompleta y falta de identidad mínima de venue. Permanece en review sin investigación ni modificaciones, conforme a la instrucción del usuario.
- Lote: `radar/inbox/curated/historical-attendance-2026-08-14-deferred.json`.
- SHA-256 intacto: `7a73f6b198180a8463a6fb47a51614fc59be3c76a4351b7c7f804d15789c5d70`.
- No confundir este histórico con Eddie Palmieri Experience de noviembre de 2026: este último es un duplicado confirmado, bloqueado por sus residuales Sora/Cortex.

## Validación Mac Pro

Host de ejecución: Mac Pro. Fecha: `2026-09-11`. Tipo de artefacto: worktree temporal detached, sobre la base exacta `d3d80064f8f7db75f09efe9fa0de1b533464964e`, más el diff heredado y el de esta misión. SHA-256 propio del artefacto: no registrado; SHA-256 disponible del diff tracked validado: `58c93d8a15338aaf02ed1962f6e750fd69e06e58bfe1d515365cb1f89278abdf`. Estado: `temporary artifact removed after validation`. Se creó desde un repositorio temporal aislado; el checkout principal de Mac Pro no se cambió.

| Comprobación | Antes | Después |
| --- | --- | --- |
| python3 scripts/validate_events.py radar/events.json | 226 válidos | 226 válidos |
| python3 -m unittest discover -s tests -v | 90 pruebas, OK (3.477 s) | 90 pruebas, OK (3.472 s) |
| Planificador activo | 492 / 11 / 4 | 492 / 3 / 1 (create / archive / review) |
| Materializador en seco con decisiones elegibles | 11 candidatos, OK | 0 elegibles, ninguna escritura |
| Residuales: lote y cada candidato individual | Prevalidación OK | 5 lotes, 11 candidatos, OK |
| Auditoría del JSON original, hashes y datos protegidos | Baseline intacto | OK; 387 lotes no seleccionados intactos |
| git diff --check | OK | OK |

La validación individual normaliza una copia en memoria para aplicar el esquema canónico; no escribe esa normalización al residual. El dry-run del plan final **sin excluir los tres bloqueos** termina con código 2 por el residual Wycliffe. Se probaron también los tres duplicados pendientes individualmente: cada uno es rechazado antes de escribir; los errores exactos están en el informe de validación. No se presenta ese dry-run como aprobado.

La aplicación local pasó la misma auditoría y su JSON de resultados es idéntico al de Mac Pro. El SHA-256 del diff tracked final coincide en ambas máquinas: `58c93d8a15338aaf02ed1962f6e750fd69e06e58bfe1d515365cb1f89278abdf`. El informe JSON adjunto contiene el inventario de archivos, residuales y comprobaciones.

## Protección y estado Git

- `radar/events.json`: intacto, SHA-256 `6848126fc1bcb084e83719e68e2e9de22ca1ee5590e13617e15955eb7b1fdda1`.
- `radar/venue_identities.json` y `tests/test_radar_intake.py`: hashes del diff heredado preservados, sin ediciones de esta misión.
- HEAD local: `d3d80064f8f7db75f09efe9fa0de1b533464964e`.
- Tras git fetch origin al inicio y al cierre, origin/main: `98d7e66d3a8b79d86aad3a6080c2f9c24593587e`. Local está **1 commit por delante, 0 por detrás**.
- Checkout principal Mac Pro: limpio, HEAD `98d7e66d3a8b79d86aad3a6080c2f9c24593587e`, sin modificaciones.
- Todo el trabajo local permanece sin commit y sin push. No se alteraron fuentes, fechas, horarios, precios, lineup, Apple Music, copy editorial, prioridades, asistencia ni IDs de los eventos.

## Artefactos y diff

- [Manifiesto completo](duplicate-resolution-2026-09-11.json): 16 decisiones, hashes, rutas, evidencia oficial, fecha, razón, diff factual, plan original, investigación y gates de materialización.
- [Validación y auditoría](duplicate-resolution-2026-09-11-validation.json): resultados de Mac Pro y listado completo de archivados/residuales.
- `scripts/plan_radar_intake.py`: rechaza URLs generales de lineup anual como prueba específica y evita archivar por página compartida con fechas/sets incompatibles.
- `scripts/materialize_radar_intake.py`: verifica de nuevo hashes, índices, IDs, canónico, registro y evidencia; prevalida todos los residuales y conserva originales exactos y decisiones completas.
- `scripts/verify_radar_duplicate_resolution.py`: auditoría de preservación de datos y conteos.
- `tests/test_duplicate_materialization.py`: 13 pruebas de seguridad; el archivo de pruebas heredado permanece intacto.
- Artefacto de diagnóstico: parche temporal del diff completo, incluidos archivos nuevos. Host: MacBook. Fecha: `2026-09-11`. Tipo: parche de diagnóstico temporal. SHA-256 propio del artefacto: no registrado; SHA-256 disponible del diff tracked validado: `58c93d8a15338aaf02ed1962f6e750fd69e06e58bfe1d515365cb1f89278abdf`. Estado: `temporary artifact removed after validation`. El contenido sigue siendo reproducible mediante git diff y los archivos untracked listados por git status.

Para los tres duplicados pendientes hace falta una autorización separada para resolver los metadatos inválidos de sus residuales, manteniendo intactos los hechos y las fuentes. Esta misión no los repara.
