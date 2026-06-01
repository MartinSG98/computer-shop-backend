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
        image_url=None,
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
        image_url=None,
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
        image_url=None,
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
        image_url=None,
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
        image_url=None,
        specs={"layout": "Full-size", "connectivity": "Bluetooth / Logi Bolt", "backlight": "Yes"},
    ),
]
