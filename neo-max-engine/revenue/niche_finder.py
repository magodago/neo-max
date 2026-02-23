"""
niche_finder - Sistema comercial inteligente de micro-problemas.
Categorías comerciales, problemas específicos y monetizables.
Prioridad por nivel_monetizacion y complejidad. Sin IA; lógica estructurada.
"""

import random
from typing import TypedDict


class MicroProblema(TypedDict):
    problema: str
    categoria: str
    nivel_monetizacion: int
    complejidad: int


CATEGORIAS = [
    "Finanzas personales",
    "Negocios online",
    "Marketing digital",
    "Freelancers",
    "E-commerce",
    "Inversión",
    "Productividad profesional",
    "SaaS",
]

# Problemas comerciales: específicos, monetizables. nivel_monetizacion y complejidad 1-5.
PROBLEMAS_COMERCIALES: list[MicroProblema] = [
    # Finanzas personales
    {"problema": "Calculadora de rentabilidad para Airbnb en España", "categoria": "Finanzas personales", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Simulador cuota autónomo España 2026", "categoria": "Finanzas personales", "nivel_monetizacion": 5, "complejidad": 4},
    {"problema": "Calculadora de préstamo personal con TAE y cuota mensual", "categoria": "Finanzas personales", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Estimador de ahorro fiscal por deducción vivienda habitual", "categoria": "Finanzas personales", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Calculadora de fondo de emergencia (meses de gastos)", "categoria": "Finanzas personales", "nivel_monetizacion": 3, "complejidad": 2},
    # Negocios online
    {"problema": "Estimador de beneficio neto para Amazon FBA", "categoria": "Negocios online", "nivel_monetizacion": 5, "complejidad": 4},
    {"problema": "Calculadora de margen para dropshipping (producto + envío)", "categoria": "Negocios online", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Simulador de ingresos por suscripción mensual recurrente", "categoria": "Negocios online", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Estimador de costes por tráfico (CPC/CPM) para landing", "categoria": "Negocios online", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Calculadora de break-even para producto digital", "categoria": "Negocios online", "nivel_monetizacion": 4, "complejidad": 3},
    # Marketing digital
    {"problema": "Calculadora de ROI de campaña (inversión vs ingresos)", "categoria": "Marketing digital", "nivel_monetizacion": 5, "complejidad": 3},
    {"problema": "Conversor de tasa de conversión a ingresos estimados", "categoria": "Marketing digital", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Estimador de coste por lead (CPL) según canal", "categoria": "Marketing digital", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Calculadora de LTV (lifetime value) por cliente", "categoria": "Marketing digital", "nivel_monetizacion": 5, "complejidad": 4},
    {"problema": "Simulador de embudo: visitas → leads → ventas", "categoria": "Marketing digital", "nivel_monetizacion": 4, "complejidad": 3},
    # Freelancers
    {"problema": "Calculadora de tarifa hora para freelancer (costes + margen)", "categoria": "Freelancers", "nivel_monetizacion": 5, "complejidad": 3},
    {"problema": "Estimador de facturación mensual por días trabajados", "categoria": "Freelancers", "nivel_monetizacion": 4, "complejidad": 2},
    {"problema": "Simulador retención IRPF autónomo España por tramos", "categoria": "Freelancers", "nivel_monetizacion": 5, "complejidad": 4},
    {"problema": "Calculadora de precio proyecto fijo desde tarifa hora", "categoria": "Freelancers", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Comparador coste autónomo vs factura en sociedad", "categoria": "Freelancers", "nivel_monetizacion": 4, "complejidad": 4},
    # E-commerce
    {"problema": "Calculadora de margen bruto por producto (precio, coste, envío)", "categoria": "E-commerce", "nivel_monetizacion": 5, "complejidad": 3},
    {"problema": "Estimador de beneficio por pedido con comisiones pasarela", "categoria": "E-commerce", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Simulador de descuento máximo sin perder margen", "categoria": "E-commerce", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Calculadora de coste unitario con embalaje y logística", "categoria": "E-commerce", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Estimador de carrito medio para meta de ingresos", "categoria": "E-commerce", "nivel_monetizacion": 3, "complejidad": 2},
    # Inversión
    {"problema": "Calculadora de interés compuesto para ahorro o inversión", "categoria": "Inversión", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Simulador de rentabilidad anualizada (CAGR) desde histórico", "categoria": "Inversión", "nivel_monetizacion": 4, "complejidad": 4},
    {"problema": "Calculadora de dividendo neto tras retención fiscal", "categoria": "Inversión", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Estimador de capital final con aportaciones periódicas", "categoria": "Inversión", "nivel_monetizacion": 5, "complejidad": 4},
    {"problema": "Conversor rentabilidad nominal a real (inflación)", "categoria": "Inversión", "nivel_monetizacion": 4, "complejidad": 3},
    # Productividad profesional
    {"problema": "Calculadora de coste por hora de reunión (salarios)", "categoria": "Productividad profesional", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Estimador de tiempo ahorrado con automatización (horas/año)", "categoria": "Productividad profesional", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Simulador de capacidad de facturación por recurso", "categoria": "Productividad profesional", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Calculadora de ROI de formación (coste vs productividad)", "categoria": "Productividad profesional", "nivel_monetizacion": 4, "complejidad": 3},
    {"problema": "Conversor jornada a facturación diaria/semanal", "categoria": "Productividad profesional", "nivel_monetizacion": 3, "complejidad": 2},
    # SaaS
    {"problema": "Calculadora de MRR desde precios y planes", "categoria": "SaaS", "nivel_monetizacion": 5, "complejidad": 3},
    {"problema": "Estimador de churn para meta de ingresos recurrentes", "categoria": "SaaS", "nivel_monetizacion": 5, "complejidad": 4},
    {"problema": "Simulador de precios por valor (value-based pricing)", "categoria": "SaaS", "nivel_monetizacion": 5, "complejidad": 4},
    {"problema": "Calculadora de CAC objetivo según LTV y ratio", "categoria": "SaaS", "nivel_monetizacion": 5, "complejidad": 4},
    {"problema": "Conversor usuarios gratuitos a conversión necesaria para meta", "categoria": "SaaS", "nivel_monetizacion": 4, "complejidad": 3},
]


def generate_commercial_micro_problem() -> MicroProblema:
    """
    Devuelve un micro-problema comercial aleatorio con categoría,
    nivel_monetizacion (1-5) y complejidad (1-5).
    """
    return random.choice(PROBLEMAS_COMERCIALES).copy()


def get_micro_problem() -> str:
    """
    Compatibilidad: devuelve solo el texto del problema.
    Usar generate_commercial_micro_problem() para datos completos.
    """
    return generate_commercial_micro_problem()["problema"]


if __name__ == "__main__":
    p = generate_commercial_micro_problem()
    print(p["problema"])
    print("Categoría:", p["categoria"], "| Monetización:", p["nivel_monetizacion"], "| Complejidad:", p["complejidad"])
