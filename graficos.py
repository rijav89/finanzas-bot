import io
import matplotlib
matplotlib.use('Agg')  # Evita abrir ventanas GUI
import matplotlib.pyplot as plt

def generar_grafico_categorias(datos, total, mes_actual):
    """
    Genera un gráfico circular (Donut chart) con los gastos del mes.
    Retorna un objeto io.BytesIO() con la imagen en formato PNG.
    """
    if not datos or total <= 0:
        return None

    categorias = []
    valores = []
    
    # Agrupar categorías muy pequeñas en "Otros" (opcional, pero útil si hay muchas)
    umbral = total * 0.05  # 5%
    otros_valor = 0
    para_graficar = []

    for cat, subtotal, _ in datos:
        if subtotal < umbral and len(datos) > 5:
            otros_valor += float(subtotal)
        else:
            para_graficar.append((cat, float(subtotal)))

    if otros_valor > 0:
        para_graficar.append(("Otros Menores", otros_valor))

    for cat, val in para_graficar:
        categorias.append(f"{cat}")
        valores.append(val)

    # Colores amigables (colores pastel/modernos)
    colores = plt.cm.Set3.colors + plt.cm.Pastel1.colors

    fig, ax = plt.subplots(figsize=(6, 5), subplot_kw=dict(aspect="equal"))
    
    wedges, texts, autotexts = ax.pie(
        valores,
        autopct='%1.1f%%',
        textprops=dict(color="black", weight="bold"),
        startangle=140,
        colors=colores[:len(valores)],
        wedgeprops=dict(width=0.4, edgecolor='w', linewidth=2)
    )
    
    # Añadir montos a la leyenda para más claridad
    leyenda_labels = [f"{c} (S/ {v:.2f})" for c, v in zip(categorias, valores)]

    ax.legend(
        wedges, leyenda_labels,
        title="Categorías",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1)
    )

    plt.setp(autotexts, size=9)
    ax.set_title(f"Gastos de {mes_actual}\nTotal: S/ {total:.2f}", weight="bold", pad=20)
    
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches="tight", dpi=150)
    plt.close()
    img_buffer.seek(0)
    
    return img_buffer

def generar_grafico_resumen(ingresos, gastos, mes_actual):
    """
    Genera un gráfico de barras horizontales comparando Ingresos vs Gastos.
    """
    if ingresos <= 0 and gastos <= 0:
        return None

    categorias = ['Ingresos', 'Gastos']
    valores = [ingresos, gastos]
    colores = ['#4CAF50', '#F44336']  # Verde y Rojo

    fig, ax = plt.subplots(figsize=(6, 3))
    
    barras = ax.barh(categorias, valores, color=colores, height=0.5)
    
    # Añadir montos al final de las barras
    for barra in barras:
        ancho = barra.get_width()
        ax.annotate(f'S/ {ancho:.2f}',
                    xy=(ancho, barra.get_y() + barra.get_height() / 2),
                    xytext=(5, 0),
                    textcoords="offset points",
                    ha='left', va='center', weight='bold')

    # Limpiar bordes innecesarios
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.get_xaxis().set_ticks([]) # Ocultar números de abajo
    
    saldo = ingresos - gastos
    estado_saldo = "(Positivo)" if saldo >= 0 else "(Negativo)"
    
    ax.set_title(f"Ingresos vs Gastos - {mes_actual}\nSaldo {estado_saldo}: S/ {saldo:.2f}", weight="bold", pad=20)
    
    max_val = max(ingresos, gastos)
    if max_val > 0:
        ax.set_xlim(0, max_val * 1.3)

    plt.tight_layout()
    
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches="tight", dpi=150)
    plt.close()
    img_buffer.seek(0)
    
    return img_buffer
