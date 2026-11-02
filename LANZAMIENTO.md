# Rolan Web · Cómo publicarla

Web de Autoescoles Rolan con matrícula y pago online. Es independiente de Rolan Gestió y de Formació: no comparte ni base de datos ni código.

## Qué hace

- **Páginas públicas** (las mismas de la web nueva): inicio, precios, quiénes somos, contacto y páginas legales. Se han añadido las condiciones de contratación, obligatorias para vender online.
- **Matrícula en 4 pasos:**
  1. El alumno elige centro y pack y escribe sus datos.
  2. Lee y firma el contrato en pantalla. Si es menor, firma el tutor/a legal.
  3. Paga con Stripe. Si quiere, añade la tasa de la DGT y el canon de pistas.
  4. Recibe un correo con el contrato firmado y el recibo.
- **Packs de prácticas** para alumnos ya matriculados: pago y recibo, sin contrato.
- **Correos al pagar:**
  - Al alumno. Su respuesta llega a la secretaría de su centro.
  - A la secretaría del centro y a admin, con todos los datos y los PDF. Su respuesta llega al alumno.
- **Panel interno** en `/gestio`:
  - Pedidos, con los PDF y la opción de reenviar los correos.
  - Excel.
  - Mensajes del formulario de contacto.
  - Precios, promociones (Black Friday), centros, datos de la autoescuela y usuarios.
  - Cada secretaria solo ve los pedidos de su centro.
- **Facturas:** las sigue haciendo la secretaría en Holded. El correo le recuerda que debe hacerla.

## 1. Render

1. En Render: **New → Blueprint**. Elige el repositorio `web`, rama `nova-web`. Render lee el archivo `render.yaml` y crea:
   - la web (`rolan-web`, Frankfurt);
   - la base de datos Postgres.
2. En la web → **Environment**, rellena:
   - `PUBLIC_URL`: de momento, la dirección que te dé Render (`https://rolan-web.onrender.com`). Cuando cambies el dominio: `https://www.autoescolesrolan.cat`.
   - `ADMIN_EMAIL` y `ADMIN_PASSWORD`: tu correo y una contraseña de al menos 10 caracteres. Sirven para crear el primer acceso a `/gestio`.
   - `STRIPE_SECRET_KEY` y `STRIPE_WEBHOOK_SECRET`: ver el punto 2.
   - `RESEND_API_KEY` y `MAIL_FROM`: ver el punto 3.

   `SECRET_KEY` la genera Render solo. Las claves nunca se escriben en el código ni en el chat.

## 2. Stripe (pagos)

1. Crea la cuenta de la autoescuela en stripe.com (datos fiscales y cuenta bancaria).
2. **Primero, en modo de prueba.** En Developers → API keys, copia la `sk_test_…` en `STRIPE_SECRET_KEY`.
3. En Developers → Webhooks → Add endpoint:
   - URL: `https://LA-DIRECCIÓN/stripe/webhook`
   - Eventos: `checkout.session.completed` y `checkout.session.async_payment_succeeded`
   - Copia el «Signing secret» (`whsec_…`) en `STRIPE_WEBHOOK_SECRET`.
4. Haz una matrícula de prueba con la tarjeta `4242 4242 4242 4242`, cualquier fecha futura y cualquier CVC.
5. **Antes de publicar:** cambia a las claves reales (`sk_live_…`) y crea el mismo webhook en modo real.

## 3. Correos (Resend)

1. Crea una cuenta en resend.com y añade el dominio `autoescolesrolan.cat`. Te dará unos registros DNS (TXT/MX): ponlos donde esté contratado el dominio.
2. Cuando salga «Verified», crea una API key y ponla en `RESEND_API_KEY`.
3. `MAIL_FROM`: por ejemplo `Autoescoles Rolan <matricules@autoescolesrolan.cat>`.

Mientras no esté configurado, los pedidos se guardan igual. En el panel salen como «Revisar» y los correos se pueden reenviar desde allí.

## 4. Panel (`/gestio`)

1. Entra con `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
2. En **Dades i correus**, rellena:
   - la razón social, el domicilio fiscal y el número de autorización de la DGT (salen en el aviso legal, la privacidad, las condiciones y el contrato);
   - en «Correus que reben còpia», tu correo.
3. En **Centres**, revisa el correo de cada secretaría: allí llegan las matrículas.
4. En **Usuaris**, crea un acceso para cada secretaria, con su centro.
5. En **Promocions**, crea la de Black Friday:
   - porcentaje de descuento;
   - fechas de inicio y fin;
   - texto de la franja de arriba, en catalán y en castellano.

   Sin código se aplica sola. Con código, solo a quien lo escriba.

## 5. Cambiar el dominio (el día del lanzamiento)

1. En Render → la web → Settings → Custom Domains, añade `www.autoescolesrolan.cat` y `autoescolesrolan.cat`. Render dirá qué registros DNS hay que poner.
2. Donde esté contratado el dominio, cambia los registros que ahora apuntan a GitHub Pages por los de Render.
3. En GitHub, en el repositorio `web` → Settings → Pages, quita el dominio personalizado.
4. Cambia `PUBLIC_URL` a `https://www.autoescolesrolan.cat` y la URL del webhook de Stripe.
5. Haz una compra real pequeña y devuélvela desde Stripe para comprobar que todo funciona.

## Antes de publicar: revisar con la gestoría

- **Aviso legal, privacidad, cookies y condiciones de contratación:** son plantillas.
- **Desistimiento:** vender online da 14 días de desistimiento. El contrato en papel dice «No es durà a terme cap devolució», y eso no vale para las ventas a distancia. La web pide al alumno que marque si quiere empezar antes de los 14 días (art. 108 del TRLGDCU) y lo deja escrito en el contrato.
- **Facturas:** el recibo no es una factura. La secretaría tiene que hacer la factura en Holded de cada pago.

## Para verla en el ordenador (sin publicar nada)

Haz doble clic en **«Veure la web en local.bat»**. La primera vez tarda un par de minutos porque instala lo necesario; después se abre sola en el navegador:

- Web: http://127.0.0.1:8010/
- Panel: http://127.0.0.1:8010/gestio · usuario `admin@local.cat` · contraseña `rolanlocal123`

Funciona en modo de demostración:
- El pago es simulado: en lugar de Stripe sale una página de pago de prueba y no se cobra nada.
- Los correos no se envían, pero se pueden ver en el panel, dentro de cada pedido («Veure el correu…»).
- Los datos se guardan en el archivo `rolan_web_local.db` de la carpeta. Si lo borras, empiezas de cero.

Para pararla, cierra la ventana «Servidor Rolan Web». Necesitas tener Python instalado (el mismo que usas para la app). En el ordenador instala `requirements-local.txt` (sin Postgres); Render usa `requirements.txt`.

Para desarrolladores:

```
pip install -r requirements.txt
uvicorn app.main:app --reload
python -m pytest -q
```
