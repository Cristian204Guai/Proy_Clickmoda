from django.core.management.base import BaseCommand
from apps.catalog.models import Category, Product, ProductImage, ProductVariant


class Command(BaseCommand):
    help = "Carga categorías y productos del prototipo de ClickModa"

    def handle(self, *args, **options):
        categorias_data = [
            ("Camisas", "camisas", 1),
            ("Vestidos", "vestidos", 2),
            ("Jeans", "jeans", 3),
            ("Chaquetas", "chaquetas", 4),
        ]
        cat_map = {}
        for nombre, slug, orden in categorias_data:
            cat, _ = Category.objects.update_or_create(
                slug=slug, defaults={"nombre": nombre, "orden": orden}
            )
            cat_map[slug] = cat

        productos_data = [
            {
                "nombre": "Camisa lino manga larga",
                "descripcion": "Camisa fresca en lino colombiano, corte regular ideal para clima cálido o templado.",
                "categoria": "camisas",
                "precio_base": 89900,
                "bg": "#CBD5E1",
                "colores": [("Azul", "#1D4ED8"), ("Blanco", "#FFFFFF")],
                "tallas": ["S", "M", "L", "XL"],
            },
            {
                "nombre": "Vestido floral midi",
                "descripcion": "Vestido corte midi con caída fluida y estampado de temporada.",
                "categoria": "vestidos",
                "precio_base": 129900,
                "bg": "#FDE68A",
                "colores": [("Ámbar", "#F59E0B"), ("Blanco", "#FFFFFF")],
                "tallas": ["XS", "S", "M", "L"],
            },
            {
                "nombre": "Jean slim fit",
                "descripcion": "Denim elástico de alta resistencia con lavado clásico hecho en Colombia.",
                "categoria": "jeans",
                "precio_base": 119900,
                "bg": "#BFDBFE",
                "colores": [("Azul", "#1D4ED8"), ("Negro", "#111827")],
                "tallas": ["S", "M", "L", "XL"],
            },
            {
                "nombre": "Chaqueta bomber",
                "descripcion": "Chaqueta liviana impermeable con cierre metálico y bolsillos laterales.",
                "categoria": "chaquetas",
                "precio_base": 159900,
                "bg": "#E5E7EB",
                "colores": [("Negro", "#111827"), ("Azul", "#1D4ED8")],
                "tallas": ["S", "M", "L", "XL"],
            },
            {
                "nombre": "Blusa satinada",
                "descripcion": "Blusa elegante de tacto suave, perfecta para oficina o eventos casuales.",
                "categoria": "camisas",
                "precio_base": 74900,
                "bg": "#FCD34D",
                "colores": [("Ámbar", "#F59E0B"), ("Blanco", "#FFFFFF")],
                "tallas": ["XS", "S", "M", "L", "XL"],
            },
            {
                "nombre": "Pantalón cargo",
                "descripcion": "Pantalón en dril suave con bolsillos utilitarios y ajuste cómodo.",
                "categoria": "jeans",
                "precio_base": 99900,
                "bg": "#93C5FD",
                "colores": [("Azul", "#1D4ED8"), ("Negro", "#111827")],
                "tallas": ["S", "M", "L", "XL"],
            },
            {
                "nombre": "Camiseta básica",
                "descripcion": "Camiseta 100% algodón peruano peinado, cuello redondo reforzado.",
                "categoria": "camisas",
                "precio_base": 39900,
                "bg": "#D1D5DB",
                "colores": [("Blanco", "#FFFFFF"), ("Negro", "#111827"), ("Azul", "#1D4ED8")],
                "tallas": ["XS", "S", "M", "L", "XL"],
            },
            {
                "nombre": "Falda plisada",
                "descripcion": "Falda midi plisada de tiro alto con cintura elástica cómoda.",
                "categoria": "vestidos",
                "precio_base": 84900,
                "bg": "#FDE68A",
                "colores": [("Ámbar", "#F59E0B"), ("Negro", "#111827")],
                "tallas": ["XS", "S", "M", "L"],
            },
            {
                "nombre": "Chaqueta denim clásica",
                "descripcion": "Chaqueta en mezclilla gruesa para combinar en cualquier ocasión.",
                "categoria": "chaquetas",
                "precio_base": 149900,
                "bg": "#BFDBFE",
                "colores": [("Azul", "#1D4ED8")],
                "tallas": ["S", "M", "L"],
            },
            {
                "nombre": "Camisa oxford oversize",
                "descripcion": "Corte relajado en tejido oxford transpirable.",
                "categoria": "camisas",
                "precio_base": 94900,
                "bg": "#E5E7EB",
                "colores": [("Blanco", "#FFFFFF"), ("Azul", "#1D4ED8")],
                "tallas": ["XS", "S", "M", "L"],
            },
        ]

        for idx, item in enumerate(productos_data, start=1):
            prod, _ = Product.objects.update_or_create(
                nombre=item["nombre"],
                defaults={
                    "descripcion": item["descripcion"],
                    "categoria": cat_map[item["categoria"]],
                    "precio_base": item["precio_base"],
                    "porcentaje_iva": 19,
                    "activo": True,
                },
            )
            ProductImage.objects.update_or_create(
                producto=prod,
                orden=0,
                defaults={"url": item["bg"]},
            )
            for color_nombre, color_hex in item["colores"]:
                for talla in item["tallas"]:
                    sku = f"CM-{idx:02d}-{color_nombre[:2].upper()}-{talla}"
                    ProductVariant.objects.update_or_create(
                        sku=sku,
                        defaults={
                            "producto": prod,
                            "talla": talla,
                            "color": color_nombre,
                            "color_hex": color_hex,
                            "stock": 10,
                        },
                    )

        self.stdout.write(self.style.SUCCESS("Catálogo poblado correctamente (10 prendas)."))