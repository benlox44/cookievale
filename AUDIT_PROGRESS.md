# Auditoría CookieVale — Progreso

Documento vivo para no perder el hilo en sesiones largas. Estado: **auditoría completa + todos los fixes aplicados**. `make check` pasa limpio. Clasificación: `[bug]` `[dead]` `[dup]` `[perf]` `[style]` `[typo]` `[ambig]`.

Base de revisión: working tree actual. `make check` pasa limpio (ruff, mypy, CSS diff, markdownlint).

## Estado de fases

- [x] Baseline (make check + greps globales)
- [x] `app/core/` (9 archivos)
- [x] `app/main.py`
- [x] Módulo `orders` (8 archivos)
- [x] Módulo `products` (6 archivos)
- [x] Módulo `scheduling` (5 archivos)
- [x] Módulo `auth` (1 archivo)
- [x] Templates (29 archivos)
- [x] CSS centralizado (`tailwind.config.js` + `public/tailwind.css`)
- [x] Lista priorizada de fixes (APLICADOS — ver sección final)

## Checklist por archivo

1. Typos/ambigüedad · 2. Código muerto · 3. Duplicación (DRY) · 4. Optimizaciones (N+1, renders) · 5. Modularidad · 6. Convenciones AGENTS.md.

## Hallazgos — Baseline

- `public/tailwind.css` tiene CSS muerto: `.badge`, `.badge-pending`, `.badge-confirmed`, `.badge-paid`, `.badge-delivered` (líneas 600-634) con vars `--status-pending-*`, `--status-confirmed-*`, etc. que NO existen en `:root`. Ningún template las usa. Sobrevivieron a la refactor de status. `[dead]`
- Vars duplicadas en `:root`: `--overlay`/`--overlay-soft` declaradas dos veces (líneas 39-40 y 46-47). `[dead]`
- `--bg-glass` y `--surface-translucent` son el mismo valor `rgba(255,255,255,0.7)`. `[dup]`
- Clases `cv-*` sin uso en templates: `cv-glass-header`, `cv-overlay-faint`, `cv-status-control`, `cv-text-inverse`. `[dead]` (cv-status-control quedó huérfano tras refactor de los botones de estado).
- `bg-brown-900/80` en `templates/admin/order_detail.html:175` — clase inexistente (Tailwind no tiene `brown`; el color custom es `cookie-brown`). El overlay del modal de carrito no pinta fondo. `[bug]` (comparar con `bg-black/40` correcto en la línea 235).
- `text-gray-400` / `bg-gray-100` en `slider.html:49` — bypasean el sistema de vars (existe `cv-media-placeholder`). `[style]`
- Sin `TODO/FIXME`, sin `os.getenv`, sin hex en templates, sin vars CSS inline en templates. Sin imports huérfanos (ruff limpio).

## Hallazgos — `app/core/`

- `uploads.get_safe_extension` (líneas 71-73): rama 2 efectivamente muerta — si `detected` está en `MIME_TO_EXT` ya retornó la rama 1; si es `None`, `content_type == detected` es falso. `[dead]`
- `security.SESSION_TTL_SECONDS = 8*60*60` hardcodeado; podría ir a config. `[style]`
- `core/templates.py` centraliza bien los labels ES (STATUS_LABELS, DELIVERY_LABELS, WEEKDAYS_SHORT, MONTHS_SHORT). Sin issues.

## Hallazgos — `app/main.py`

- Sin issues. Middleware, rate-limit handler, validación con anti-open-redirect, sitemap/robots bien.

## Hallazgos — módulo `orders`

- `admin_router.py`: `weekdays = ["Lunes", ..., "Domingo"]` duplicado en 3 endpoints (new_order_form, get_order_detail, client_router.get_new_order_form). `[dup]` (resultó ser contexto muerto: ningún template lo usaba).
- `admin_router.py`: `new_order_form` pasa `OrderStatuses = list(OrderStatus)` (enums) mientras `get_order_detail` pasa `[e.value for e in OrderStatus]` (strings). Cada template usa el que espera, pero el shape de la misma variable cambia por ruta. `[ambig]`
- `admin_router.py:211-227` `update_order_status`: comentario sobre "slot ocupado" es stale (el endpoint solo cambia status, no slot). `[style]`
- `service.py`: magia `photos[:8]`, `max_images=8`, `final_photos[:8]` repetida (también `max_images=10` en products). `[dup]`
- `service.py:88`: mapeo `{'Retiro' if ... else 'Delivery'}` hardcodeado duplicando `DELIVERY_LABELS` de core/templates. `[dup]` menor.
- `repository.replace_items` hace commit + segundo round-trip `get_by_id`. `[perf]` menor.
- `cart.py`: permite duplicar el mismo product_id en el carrito (dos line items). Edge case menor. `[ambig]`

## Hallazgos — módulo `products`

- `admin_router.delete_product` (línea 123): parámetro `request: Request` sin usar. `[dead]`
- Magia `[:10]` / `max_images=10` (ver orders). `[dup]`
- `schemas.ProductCreate` == `ProductUpdate` (solo `pass`). `[style]`

## Hallazgos — módulo `scheduling`

- `service.get_free_slots()` ejecuta `DELETE` de fechas pasadas en cada lectura (purga auto). Escribe en rutas GET. Decisión de diseño, pero anotar. `[style]`
- Naming residual: `AvailableDateOption` (sigue llamándose "AvailableDate" tras refactor a slots). `[ambig]`
- `admin_router` (dates): devuelve `JSONResponse {"detail"}` en errores en vez de `error_toast` (HTMX), inconsistente con el resto. `[style]`

## Hallazgos — módulo `auth`

- Sin issues. Login con `compare_digest`, cookie httponly/samesite/secure, rate-limit.

## Hallazgos — Templates

- `components/feedback/toast.html:13-14`: **doble atributo `class`** en la barra de progreso. El navegador toma el primer `class` y descarta `bg-cookie-golden` → barra invisible. `[bug]`
- Botón "Volver" con back-arrow duplicado verbatim en 5 páginas admin (orders_dashboard, dates_dashboard, products_dashboard, order_create, order_detail). `[dup]`
- Blobs decorativos duplicados en `admin/panel.html` y `client/index.html`. `[dup]`
- SVG "plus" inline en varios dashboards vs `render_icon("plus")` en dates_dashboard → inconsistente. `[dup]`
- SVG Instagram (path gigante) duplicado 3x: `orders_table.html:66`, `client_header.html:9`, `client/index.html:53` (+ `order_detail.html:84`). `[dup]`
- Resumen de carrito (x-for + total) duplicado 3x: `client/order_form`, `admin/order_create`, `admin/order_detail` (modal). `[dup]`
- Opciones delivery_method `pickup/delivery` + labels duplicadas en client/order_form y admin/order_create. `[dup]`
- `order_create.html` y `client/order_form.html`: botón submit + `x-data="{hasDate:false}"` y `@date-selected.window` casi idénticos. `[dup]`
- 4 botones de status en `order_detail.html:42-61` idénticos salvo el string; el sistema `.cv-status-control` (muerto) era para esto. `[dup]`
- `product_form.html:41`: typo "Imágen(es)" (falta la "e": Imagen). El resto usa "Imagen(es)". `[typo]`
- `login.html:6`: indentación rara. `[style]`
- `confirm_modal.html:13`: `{% elif true %}` idiomático, mejor `{% else %}`. `[style]`
- `products_dashboard.html:168`: `handleReorder() {}` no-op (requerido por x-sort). `[style]`
- `order_detail.html`: incluye `components/orders/cart.html` (define cookieCart) pero el modal sí lo usa con `x-data="cookieCart([...], ...)"`. OK, no es muerto.
- `base.html`: fuentes desde Google Fonts (CDN). AGENTS.md prohíbe CDN para libs JS, no para fuentes; pero anotar (privacidad/rendimiento). `[style]`

## Hallazgos — Uploaders (media)

- `order_uploader.html:2-5`: guard `{% if ... %}` llama a `missing_required_argument_uploader()` que NO existe. Solo se dispara si faltan args, pero si pasa → UndefinedError → 500. `[dead]`/`[bug latent]`
- `product_uploader.html:369-375` `updateInputFiles` usa `new DataTransfer()` sin try/catch; `order_uploader` lo envuelve en try/catch (iOS). Inconsistente. `[style]`
- Uploaders (orders 297 líneas + products 379) comparten ~60% de estructura (drop zone, sort grid, tile de añadir, botones remove, drag handle, lightbox). Refactor complejo pero posible: macro base común. `[dup]` mayor
- `product_uploader` no revoca object URLs al cancelar/saltar crops → leak menor. `[perf]`

## Hallazgos — CSS centralizado

- `.badge`, `.badge-pending/confirmed/paid/delivered` (líneas 600-634) muertas + referencian vars `--status-pending-*`/`--status-confirmed-*`/`--status-paid-*`/`--status-delivered-*` que no existen. `[dead]`
- `--overlay`/`--overlay-soft` declaradas dos veces (39-40 y 46-47). `[dead]`
- `--bg-glass` (0.7) == `--surface-translucent` (0.7): mismo valor, dos nombres (ambos con clase usada). `[dup]`
- Clases huérfanas: `cv-glass-header`, `cv-overlay-faint`, `cv-status-control`, `cv-text-inverse` (0 usos). `[dead]`
  - Al quitar `cv-glass-header` queda huérfana `--bg-glass-soft` (solo la usa esa clase).
  - Al quitar `cv-overlay-faint` queda huérfana `--overlay-faint` (solo la usa esa clase).
- `render_icon("calendar")` no se usa en ningún template → icono muerto en `icons.html`. `[dead]`
- El resto de vars están usadas (vía utilities compiladas `bg-cookie-*`, `text-cookie-*`, `border-cookie-*` en styles.css o clases `cv-*`). Sin colores hardcodeados en templates salvo los 3 casos ya anotados (`bg-brown-900/80`, `bg-gray-100`, `text-gray-400`).

## Cross-checks finales

- `render_tooltip`/`render_dropdown`/`render_date_calendar`/`render_product_picker`: todos los imports usados.
- Magia `8`/`10` (máx fotos) duplicada entre Python (`service.py`) y templates (labels "Máximo 8/10" y args de `render_uploader_*`). `[dup]`
- `hashlib.md5(...)[:8]` en templates.py es cache-bust (no relacionado con fotos).

## Fixes aplicados

### Bugs

- `order_detail.html` modal carrito: `bg-brown-900/80` → `bg-black/40`.
- `toast.html`: fusionado el doble atributo `class` (barra de progreso visible).
- `order_uploader.html`: eliminado el guard con `missing_required_argument_uploader()` inexistente.

### Dead code

- `tailwind.css`: eliminados `.badge*` + vars inexistentes, duplicados `--overlay`/`--overlay-soft`, y clases huérfanas `cv-glass-header`, `cv-overlay-faint`, `cv-status-control`, `cv-text-inverse` (+ vars `--bg-glass-soft`, `--overlay-faint`); unificado `--bg-glass`/`--surface-translucent` (queda `--bg-glass`).
- `icons.html`: eliminado `render_icon("calendar")` sin uso; añadido `render_icon("instagram")`.
- `uploads.get_safe_extension`: eliminada rama muerta.
- `products/admin_router.delete_product`: eliminado param `request` sin usar.
- Routers orders/client: eliminado contexto `weekdays` (muerto, ningún template lo usaba).

### DRY / reuso

- Nuevo `components/ui/back_button.html` (`render_back_button`) usado en 5 páginas.
- Nuevo `components/orders/cart_summary.html` (`render_cart_summary`) usado en order_form, order_create y modal de order_detail.
- Nuevo `components/layout/decorative_blobs.html` usado en panel.html e index.html.
- SVG Instagram → `render_icon("instagram")` (orders_table, client_header, client/index, order_detail).
- SVG plus → `render_icon("plus")` (orders_dashboard, products_dashboard, order_create, order_detail, picker).
- `delivery_methods` global en `core/templates.py` (reemplaza listas duplicadas en client/order_form y order_create).
- Constantes `MAX_ORDER_PHOTOS=8`/`MAX_PRODUCT_IMAGES=10` en `config.py`, globales Jinja + usadas en services y templates ("Máximo N").
- `order_detail` botones de status → loop `{% for s in OrderStatuses %}`.

### Consistencia / ambigüedad

- `OrderStatuses` siempre como strings (unificado `new_order_form` con `get_order_detail`; `order_create` usa `s` en vez de `s.value`).
- `AvailableDateOption` → `AvailableSlotOption` (scheduling + orders/admin_router).
- `SESSION_TTL_SECONDS` movido a `config.py` (security/auth lo importan).
- `ProductCreate`/`ProductUpdate` → `ProductInput` único.
- Comentario stale en `update_order_status` corregido.
- Typo `product_form.html` "Imágen(es)" → "Imagen(es)".
- `login.html` indentación; `confirm_modal` `{% elif true %}` → `{% else %}`.
- `slider.html` `bg-gray-100`/`text-gray-400` → `cv-media-placeholder`/`text-cookie-brown/40`.

### Optimizaciones

- `orders/repository.replace_items`: sin round-trip extra (`get_by_id`).
- `cart.parse_cart_items`: merge de product_id duplicados (suma cantidades).
- Uploaders: `removeNew` revoca object URLs; `product_uploader.updateInputFiles` con try/catch (paridad iOS).

### No aplicados (decisión documentada)

- Dates admin_router usa `JSONResponse` 409: es correcto porque dates_dashboard usa `fetch` (no HTMX); cambiar a `error_toast` lo rompería.
- `get_free_slots` purga en GET: decisión de diseño (autolimpieza); mover a tarea requiere infra nueva.
- Google Fonts CDN: decisión de diseño.
- Refactor de uploaders a macro base común: alto riesgo (feature crítica de imágenes), se deja como candidato futuro.
