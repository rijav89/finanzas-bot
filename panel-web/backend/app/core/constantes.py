"""Valores que tienen que coincidir entre varias capas.

Si estas listas se escriben a mano en cada query, tarde o temprano una queda vieja
y un total empieza a mentir sin que nada falle.
"""

#: Categorías que mueven el saldo pero no son ingreso ni gasto.
#: - Transferencia: la plata cambia de cuenta, sigue siendo tuya.
#: - Prestamo: la plata cambia de manos, pero no de dueño — devolverla no es un
#:   gasto (ya registraste el gasto al comprar con ella) ni recibirla es un ingreso.
CATEGORIAS_SIN_TOTALES = ("Transferencia", "Prestamo")

#: Fragmento SQL listo para interpolar en las queries analíticas.
SQL_EXCLUIR_SIN_TOTALES = "categoria NOT IN ('Transferencia', 'Prestamo')"
