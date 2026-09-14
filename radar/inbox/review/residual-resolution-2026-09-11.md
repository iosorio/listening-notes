# RADAR — reparación de residuales y cierre de duplicados

Verificado y aplicado el 2026-09-11. Continuación de duplicate-resolution-2026-09-11: el informe anterior se conserva como instantánea histórica, no se reescribe.

## Resultado

Cuatro residuales corregidos; tres duplicados confirmados materializados tras validación completa en Mac Pro. Se dividieron tres lotes mixtos y todos los residuales siguen activos. No se materializó ningún create ni review. No se modificó ningún evento canónico.

| Planificador | create | archive_duplicate | review | merge | replace |
| --- | ---: | ---: | ---: | ---: | ---: |
| Antes | 492 | 3 | 1 | 0 | 0 |
| Después | 492 | 0 | 1 | 0 | 0 |

Eddie Palmieri histórico de 2019 sigue intacto en review. Los 11 duplicados archivados en la misión anterior y sus evidencias permanecen intactos; con estos tres, el total acumulado es 14.

## Fuentes y cambios exactos

| Residual | Cambio | Fuente / alcance |
| --- | --- | --- |
| Wycliffe Gordon | missing pasa de apple_music + individual_septet_personnel + individual_chorus_personnel a **[apple_music]**. status sigue pending. Se corrige la nota obsoleta y se añade una verificación, sin cambiar lineup. | [JALC](https://jazz.org/concert/wycliffe-gordon-welcome-to-georgia-town/) ya enumera músicos individuales el 11 de septiembre. La nota conserva el contexto de la captura del 28 de agosto y explica que el lineup original a nivel de ensembles no se amplía en esta reparación. |
| Sora Ichikawa | status **partial → pending**; missing **[official_tickets, apple_music]**. currency ya era JPY y se conserva. official.minimum y maximum **null → 5500**; source_url **null → agenda oficial**; checked_on **null → 2026-09-11**. Se actualiza note y se añaden dos fuentes oficiales. | [Agenda oficial ALFIE](https://alfie.tokyo/schedule/202609.html), entrada del 12 de septiembre; [reservas oficiales](https://alfie.tokyo/news/reservation.html). No se cambia ningún enlace de links, horario, lineup, copy ni Apple Music. |
| Cortex | status **partial → pending**; missing pasa de complete verified 2026 touring personnel + verified official face-value availability + apple_music a **[apple_music]**. Note se conserva literalmente, con incertidumbre de personal y precio face value. | Ambos links están almacenados y no hay Apple Music. [AXS](https://www.axs.com/events/1520923/cortex-tickets) confirma que su oferta visible es Marketplace de reventa. No se convierte en precio oficial ni se modifica el ticketing. |
| Interpretations | missing pasa de special_guest + apple_music a **[apple_music]**. status y note se conservan literalmente. | [Roulette](https://roulette.org/event/hemingway-andonovska-howard-motl-wallace-neuburg/) sigue anunciando un invitado sin nombre. Ese detalle permanece en note, no en missing. No se inventa personal. |

Los valores completos anteriores y posteriores de cada campo autorizado están en [el registro de reparación](residual-repair-2026-09-11.json), junto con los textos originales completos. Las fuentes existentes se conservan; las nuevas verificaciones se añaden, no reemplazan registros anteriores.

## Moneda y ticketing de Sora

El problema no era una moneda ausente: el candidato ya tenía **JPY**, pero validate_events.py sólo permitía USD. La modificación mínima del contrato admite exclusivamente **USD o JPY explícitos**. Valores ausentes, null, desconocidos, minúsculas o de otro tipo se rechazan. No se cambia el normalizador heredado ni se usa su default para Sora; no se convierte moneda ni se deduce de la ubicación.

La agenda oficial de septiembre de 2026 publica **￥5500** para el concierto de lanzamiento de Sora Ichikawa, 高橋将 y 塚田陽太 del día 12. El cargo incluye impuestos. La misma agenda exige al menos dos pedidos de comida/bebida por persona, cuyo coste queda separado y no se estima. El precio almacenado es el cargo musical, no el gasto total.

El índice de agenda redirige por JavaScript al archivo del mes. El extractor web no pudo abrir la página de septiembre, pero se obtuvo directamente por HTTPS y se decodificó con Shift_JIS, el charset declarado por la fuente. No se basó la cifra en un agregador. Los ¥3.300 del [sello discográfico](https://www.somethincooljazz.com/afcd6010) son el precio del disco y se descartaron como evidencia del concierto.

ALFIE acepta reservas por teléfono, no por la página ni por email. Por eso official_tickets permanece **null**, no se sustituye por la política general de reservas. pending también refleja que Apple Music aún no está verificado. Es incertidumbre legítima de enriquecimiento, no un bloqueo de validación.

## Manifiesto de los tres duplicados

Los candidatos duplicados no se editaron: sus objetos y hashes de evento son idénticos a los de la decisión confirmada anterior. Sólo cambia el hash del lote porque se repararon sus hermanos residuales. El materializador vuelve a comprobar los hashes del lote, canónico, registro de venues y decisión determinista por URL oficial específica.

| Candidato | Canónico | Evidencia oficial específica |
| --- | --- | --- |
| `jlco-wynton-marsalis-from-cuba-to-crescent-city-new-york-2026-10-23` | `wynton-marsalis-from-cuba-to-crescent-city-jalc-2026-10-23` | [URL coincidente](https://jazz.org/concert/from-cuba-to-the-crescent-city-the-jazz-at-lincoln-center-orchestra-with-wynton-marsalis/) |
| `eddie-palmieri-experience-jalc-rose-theater-nyc-2026-11-13` | `eddie-palmieri-experience-jalc-2026-11-13` | [URL coincidente](https://jazz.org/concert/eddie-palmieri-experience-an-all-star-celebration/) |
| `tsuyoshi-yamamoto-masahiko-satoh-kawasaki-shimin-plaza-2026-10-03` | `masahiko-satoh-tsuyoshi-yamamoto-kawasaki-shimin-plaza-2026-10-03` | [URL coincidente](https://www.kawasaki-shiminplaza.jp/event/detail?id=15726) |

[Manifiesto ejecutado](residual-duplicates-2026-09-11.json): acción archive_duplicate, aprobación permitted, fecha, razón, fuente, hash de candidato/canónico, hash del lote corregido y enlace al hash previo a la reparación.

## Lotes divididos, evidencia y residuales

### jalc-wynton-wycliffe-fall-2026-2026-08-28-discovery.json

- Lote activo residual: `radar/inbox/curated/jalc-wynton-wycliffe-fall-2026-2026-08-28-discovery.json`.
- SHA-256 anterior a la corrección: `d0d8769c320216c6cb212af7a0ecb5a59b4430d6b8e236c914af71dd37108664`.
- SHA-256 corregido antes del archivo: `77fd9f69d556dc2f990d451d886edd9c6829551921c59b151f67b72461d548b9`.
- Duplicado archivado: `jlco-wynton-marsalis-from-cuba-to-crescent-city-new-york-2026-10-23`.
- Archivo de evidencia: `radar/inbox/review/decisions/77fd9f69d556dc2f990d451d886edd9c6829551921c59b151f67b72461d548b9-jalc-wynton-wycliffe-fall-2026-2026-08-28-discovery.json`.
- Residuales activos: `wycliffe-gordon-welcome-to-georgia-town-jalc-new-york-2026-10-09`.

### sora-cortex-palmieri-2026-08-29-discovery.json

- Lote activo residual: `radar/inbox/curated/sora-cortex-palmieri-2026-08-29-discovery.json`.
- SHA-256 anterior a la corrección: `b6e6ad509ff72a8fa72c984afa70b33f68260e48908708dcc3ca810aef8f2208`.
- SHA-256 corregido antes del archivo: `7b510747e04e69afc9599b6a7190c92968c70da05300c680879057e8ebac7415`.
- Duplicado archivado: `eddie-palmieri-experience-jalc-rose-theater-nyc-2026-11-13`.
- Archivo de evidencia: `radar/inbox/review/decisions/7b510747e04e69afc9599b6a7190c92968c70da05300c680879057e8ebac7415-sora-cortex-palmieri-2026-08-29-discovery.json`.
- Residuales activos: `sora-ichikawa-concept-band-jazz-house-alfie-tokyo-2026-09-12`, `cortex-howard-theatre-washington-dc-2026-10-06`.

### yamamoto-satoh-interpretations-2026-08-29-discovery.json

- Lote activo residual: `radar/inbox/curated/yamamoto-satoh-interpretations-2026-08-29-discovery.json`.
- SHA-256 anterior a la corrección: `63cc2234ef40d1cf540abe4242ac7b00b95b452bd32afc644c71404b30909b83`.
- SHA-256 corregido antes del archivo: `99be9f6c0a0363821b18a281289fc62133fd113dd55a75594cc275f228ff6980`.
- Duplicado archivado: `tsuyoshi-yamamoto-masahiko-satoh-kawasaki-shimin-plaza-2026-10-03`.
- Archivo de evidencia: `radar/inbox/review/decisions/99be9f6c0a0363821b18a281289fc62133fd113dd55a75594cc275f228ff6980-yamamoto-satoh-interpretations-2026-08-29-discovery.json`.
- Residuales activos: `interpretations-hemingway-andonovska-howard-roulette-brooklyn-2026-12-03`.

### Cadena de recuperación

1. residual-repair-2026-09-11.json conserva cada lote original completo en original_text, UTF-8 exacto y SHA-256 anterior a la reparación.
2. El mismo registro conserva corrected_text y SHA-256 del lote corregido, más las diferencias autorizadas.
3. Cada archivo de decisiones conserva el lote corregido completo como source.original_text y source.original_batch, el duplicado intacto, evidencia y decisión.
4. La auditoría reconstruye cada lote corregido desde el original y los cambios declarados; después comprueba que quitar sólo el duplicado produce exactamente el lote residual activo.

No se retiró ningún lote completo en esta misión; los tres quedaron activos con sus cuatro residuales.

## Validación Mac Pro

Host de ejecución: Mac Pro. Fecha: `2026-09-11`. Tipo de artefacto: worktree temporal detached. Base exacta `d3d80064f8f7db75f09efe9fa0de1b533464964e`, más todo el diff acumulado. SHA-256 propio del artefacto: no registrado; SHA-256 disponible del diff tracked validado: `b88276c06bb3c4f8860476cc7942cd7102cc543432b351188827f6790f9fac05`. Estado: `temporary artifact removed after validation`. Las correcciones de candidatos y la materialización se probaron aquí antes de aplicarse localmente.

| Validación | Resultado |
| --- | --- |
| Canónico antes / después | 226 eventos válidos; bytes intactos |
| Suite antes del archivo | 99 tests, OK, 4.393 s |
| Suite después del archivo | 99 tests, OK, 4.415 s |
| Cada residual individual | 4/4 válidos, normalizando sólo una copia en memoria |
| Cada lote residual completo | 3/3 válidos; sobres conservados |
| Lotes mixtos de entrada | validate_batch OK; los duplicados sólo se archivan, no se ingieren al canónico |
| Planificador antes / después | 492/3/1 → 492/0/1 |
| Materializador en seco antes | 3 candidatos confirmados, OK |
| Materializador en seco con plan final | 0 archivos, sin error ni escritura |
| Auditoría | 389 lotes activos no seleccionados intactos; originales y evidencias preservados |
| git diff --check | OK en local y Mac Pro |
| Aplicación local | Dry-run y auditoría idénticos a Mac Pro |

Se añadieron nueve regresiones: validación de los cuatro residuales, etiquetas no estándar, partial inválido, special_guest fuera de missing, missing exacto, USD/JPY sin conversión, moneda inválida/ausente, precio oficial de Sora con fuente, y campos no autorizados intactos.

[Resultados estructurados de validación](residual-validation-2026-09-11.json). SHA-256 del diff tracked final, idéntico en ambas máquinas: `b88276c06bb3c4f8860476cc7942cd7102cc543432b351188827f6790f9fac05`. También coincidieron los hashes de todos los archivos nuevos de implementación/evidencia.

## Estado y límites

- Sin bloqueos restantes para estos tres duplicados.
- Los cuatro residuales siguen en pending por los componentes de enriquecimiento enumerados; no se inventaron enlaces para declararlos complete.
- `eddie-palmieri-2019-user-confirmed` sigue siendo el único review. Su lote conserva SHA-256 `7a73f6b198180a8463a6fb47a51614fc59be3c76a4351b7c7f804d15789c5d70`.
- HEAD local sigue en d3d8006. Tras git fetch origin: **1 commit por delante, 0 por detrás** de origin/main (`98d7e66d3a8b79d86aad3a6080c2f9c24593587e`).
- Checkout principal Mac Pro limpio en 98d7e66, sin modificaciones.
- Se conserva íntegro el diff heredado, incluidos el registro de venues, tests previos, materializador, planificador y evidencias anteriores.
- Sin commit, push, merge, rebase ni reset.

## Diff y archivos de implementación

- `scripts/validate_events.py`: sólo amplía la moneda admitida a USD/JPY explícitos y mejora el mensaje de error.
- `docs/DATA_MODEL.md`: documenta moneda, cargo verificado y límites de reserva.
- `scripts/verify_radar_residual_repairs.py`: auditoría de sólo lectura de los cuatro cambios permitidos y la cadena de archivo.
- `tests/test_residual_repairs.py`: nueve regresiones nuevas.
- Artefacto de diagnóstico: parche temporal del diff acumulado completo, incluidos archivos nuevos. Host: MacBook. Fecha: `2026-09-11`. Tipo: parche de diagnóstico temporal. SHA-256 propio del artefacto: no registrado; SHA-256 disponible del diff tracked validado: `b88276c06bb3c4f8860476cc7942cd7102cc543432b351188827f6790f9fac05`. Estado: `temporary artifact removed after validation`. El diff previo no se sobrescribió durante aquella validación y el estado actual sigue siendo reproducible con Git.
