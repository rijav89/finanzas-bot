def categorizar(texto):

    texto = texto.lower()

    if texto in ["cine","netflix","juego","streaming"]:
        return "Entretenimiento"

    if texto in ["pollo","almuerzo","cena","desayuno","comida"]:
        return "Comida"

    if texto in ["uber","taxi","bus","pasaje"]:
        return "Transporte"

    if texto in ["farmacia","medicina"]:
        return "Salud"

    return "Otros"