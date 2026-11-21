# Tienda Flask con AWS (DynamoDB, S3, SQS) y Docker

Aplicación de tienda en Flask con panel de administrador. Los productos y pedidos se guardan en DynamoDB, las imágenes en S3 y cada pedido se envía a una cola SQS. Para desarrollo local se usa LocalStack, que emula los servicios de AWS en la máquina.

## Funcionalidades

- **Catálogo** de productos con imagen.
- **Carrito** en sesión, con agregar y quitar productos.
- **Compra** que guarda el pedido en DynamoDB y lo envía a SQS.
- **Panel de administrador** para crear y eliminar productos y revisar pedidos.
- **Autenticación de administrador** con contraseña en hash (Werkzeug).
- **Script de simulación** que realiza pedidos por HTTP como un cliente real.

## Arquitectura

```text
Navegador ──> Flask (app) ──> DynamoDB  (products, orders)
                   │
                   ├──> S3   (imágenes de productos)
                   └──> SQS  (cola orders-queue)


# Requisitos

- Docker y Docker Compose
- AWS CLI v2
- Python 3.12+ (solo para el script de simulación o la app fuera de Docker)
- Token de LocalStack (cuenta gratuita en [[https://app.localstack.cloud][app.localstack.cloud]])

# Configuración

## Variables de entorno

Crea un archivo =.env= en la raíz del proyecto:

#+begin_src env
# Token de LocalStack (solo para el contenedor del emulador)
LOCALSTACK_AUTH_TOKEN=tu-token

# Aplicación
FLASK_SECRET_KEY=una-clave-larga-y-aleatoria
ADMIN_USER=admin
ADMIN_PASSWORD_HASH='scrypt:...'

# AWS (LocalStack)
AWS_REGION=us-east-1
S3_BUCKET=tienda-imagenes
PRODUCTS_TABLE=products
ORDERS_TABLE=orders
ORDERS_QUEUE=orders-queue
#+end_src

Genera el hash de la contraseña del administrador:

#+begin_src bash
python3 -c "from werkzeug.security import generate_password_hash as g; print(g('TU_CONTRASEÑA'))"
#+end_src

#+begin_quote
Pega el resultado completo entre comillas simples, porque contiene caracteres =$=.
#+end_quote

#+begin_quote
=.env= contiene secretos. Añádelo a =.gitignore=.
#+end_quote

## Perfil de AWS CLI para LocalStack

#+begin_src bash
aws configure set aws_access_key_id     test                  --profile localstack
aws configure set aws_secret_access_key test                  --profile localstack
aws configure set region                us-east-1             --profile localstack
aws configure set output                json                  --profile localstack
export AWS_PROFILE=localstack
#+end_src

=AWS_PROFILE= solo se usa en tu máquina. No lo pongas en =.env=, porque el contenedor no tiene ese perfil.

# Ejecución

## Con Docker (recomendado)

#+begin_src bash
docker compose up --build
#+end_src

Esto levanta LocalStack y la aplicación. Al arrancar, =setup_aws.py= crea las tablas =products= y =orders=, el bucket =tienda-imagenes= y la cola =orders-queue=.

Abre [[http://localhost:8000][http://localhost:8000]].

# Uso

1. *Administrador:* entra a [[http://localhost:8000/admin/login][/admin/login]], crea productos con imagen y revisa los pedidos en el panel.
2. *Cliente:* en el catálogo, agrega productos al carrito, revisa =/cart= y pulsa *Comprar*.
3. *Simulación:* con al menos un producto creado, ejecuta:

#+begin_src bash
pip install requests
python scripts/simulate_orders.py --count 100
#+end_src

# Verificación en AWS

#+begin_src bash
# Tablas
aws dynamodb list-tables
aws dynamodb scan --table-name orders --select COUNT

# Imágenes en S3
aws s3 ls s3://tienda-imagenes/products/ --recursive

# Cola SQS
aws sqs get-queue-attributes \
  --queue-url "$(aws sqs get-queue-url --queue-name orders-queue --query QueueUrl --output text)" \
  --attribute-names ApproximateNumberOfMessages
#+end_src

# Estados de un pedido

| Estado    | Significado                                  |
|-----------+----------------------------------------------|
| =PENDING= | Pedido guardado, pero el envío a SQS falló   |
| =QUEUED=  | Pedido guardado y enviado a SQS              |

# Solución de problemas

| Síntoma                                              | Causa probable                                                                                              |
|------------------------------------------------------+-------------------------------------------------------------------------------------------------------------|
| =ProfileNotFound: localstack= en los logs de =app=   | =AWS_PROFILE= está en =.env=. Quítalo y recrea con =docker compose up -d --force-recreate app=.            |
| =InvalidClientTokenId=                               | Faltan credenciales. Revisa =AWS_ACCESS_KEY_ID=test= en =docker-compose.yml=.                              |
| El login siempre falla                               | El hash no está entre comillas simples, o se generó con otra contraseña.                                    |
| Pedidos en =PENDING=                                 | La cola =orders-queue= no existe o =SQS_QUEUE_URL= es incorrecta.                                           |
| Las imágenes no se muestran                          | La clave de la imagen no coincide con el objeto en S3.                                                      |
| El contenedor de LocalStack no arranca               | Falta =LOCALSTACK_AUTH_TOKEN= o es inválido.                                                                |

# Seguridad

Este proyecto es para desarrollo y demostración. Antes de producción:

- Usa HTTPS y cambia =FLASK_SECRET_KEY=.
- Añade protección CSRF (por ejemplo, Flask-WTF) y límite de intentos de login.
- Guarda las credenciales en un gestor de secretos, no en =.env=.
- Usa AWS real con roles IAM en lugar de claves =test=.


# Limitaciones

- =scan()= de DynamoDB sirve para demostración, pero no escala. Usa paginación o índices en un catálogo grande.
- El panel muestra solo los últimos 20 pedidos.
- El carrito vive en la sesión del navegador.
