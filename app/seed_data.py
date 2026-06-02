"""Sample assortment used by the in-memory repository."""

from decimal import Decimal

from app.models import Product

SEED_PRODUCTS: list[Product] = [
    Product(
        id="laptop-tp-x1",
        name="ThinkPad X1 Carbon Gen 12",
        brand="Lenovo",
        category="Laptops",
        price=Decimal("1899.00"),
        stock=12,
        description="14-inch business ultrabook.",
        image_key="products/laptop-tp-x1/main.webp",
        specs={"cpu": "Intel Core Ultra 7", "ram": "32GB", "storage": "1TB SSD", "display": "14\" 2.8K OLED"},
    ),
    Product(
        id="gpu-rtx-4070",
        name="GeForce RTX 4070 Ti SUPER",
        brand="NVIDIA",
        category="Graphics Cards",
        price=Decimal("799.00"),
        stock=7,
        description="High-end 1440p / entry 4K gaming GPU.",
        image_key="products/gpu-rtx-4070/main.webp",
        specs={"vram": "16GB GDDR6X", "tdp": "285W", "ports": "3x DP, 1x HDMI"},
    ),
    Product(
        id="cpu-ryzen-7800x3d",
        name="Ryzen 7 7800X3D",
        brand="AMD",
        category="Processors",
        price=Decimal("349.00"),
        stock=20,
        description="8-core gaming CPU with 3D V-Cache.",
        image_key="products/cpu-ryzen-7800x3d/main.webp",
        specs={"cores": "8", "threads": "16", "socket": "AM5", "tdp": "120W"},
    ),
    Product(
        id="mon-odyssey-g7",
        name="Odyssey G7 32\"",
        brand="Samsung",
        category="Monitors",
        price=Decimal("649.00"),
        stock=5,
        description="32-inch 1440p 240Hz curved gaming monitor.",
        image_key="products/mon-odyssey-g7/main.webp",
        specs={"size": "32\"", "resolution": "2560x1440", "refresh": "240Hz", "panel": "VA"},
    ),
    Product(
        id="kbd-mx-keys",
        name="MX Keys S",
        brand="Logitech",
        category="Peripherals",
        price=Decimal("109.00"),
        stock=40,
        description="Wireless low-profile productivity keyboard.",
        image_key=None,
        specs={"layout": "Full-size", "connectivity": "Bluetooth / Logi Bolt", "backlight": "Yes"},
    ),
]
