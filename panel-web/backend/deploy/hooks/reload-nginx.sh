#!/bin/sh
# Hook de despliegue de certbot: /etc/letsencrypt/renewal-hooks/deploy/
#
# Con `certonly` certbot no toca nginx. Sin este hook, el certificado nuevo queda en
# disco y nginx sigue sirviendo el viejo en memoria hasta que alguien recargue a mano
# — es decir, hasta que venza y el sitio deje de abrir.
# `reload` y no `restart`: no corta las conexiones en curso.
/usr/bin/systemctl reload nginx
