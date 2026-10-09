from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def save(self, *a, **kw):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*a, **kw)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    gst_percent = models.DecimalField(max_digits=4, decimal_places=2, default=18)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *a, **kw):
        if not self.slug:
            base = slugify(f"{self.brand} {self.name}")[:200]
            slug, n = base, 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        super().save(*a, **kw)

    @property
    def default_variant(self):
        return (self.variants.filter(stock__gt=0).order_by("price").first()
                or self.variants.order_by("price").first())

    def __str__(self):
        return self.name


class Variant(models.Model):
    """Size / pack / grade of a product, e.g. '1 inch - Pack of 100'."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    label = models.CharField(max_length=120)
    sku = models.CharField(max_length=60, unique=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.label}"

    @property
    def discount_percent(self):
        if self.mrp and self.mrp > self.price:
            return int((self.mrp - self.price) * 100 / self.mrp)
        return 0

    @property
    def in_stock(self):
        return self.stock > 0

    def unit_price_for(self, qty):
        """Bulk slab pricing: best matching slab wins, else normal price."""
        slab = self.bulk_prices.filter(min_qty__lte=qty).order_by("-min_qty").first()
        return slab.price if slab else self.price


class BulkPrice(models.Model):
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name="bulk_prices")
    min_qty = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("variant", "min_qty")
        ordering = ["min_qty"]


class Order(models.Model):
    STATUS = [
        ("PENDING", "Payment pending"), ("PAID", "Paid"), ("PACKED", "Packed"),
        ("SHIPPED", "Shipped"), ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"), ("FAILED", "Payment failed"),
    ]
    METHOD = [("ONLINE", "Online (Razorpay)"), ("COD", "Cash on Delivery")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    address = models.TextField()
    city = models.CharField(max_length=80)
    pincode = models.CharField(max_length=6)
    gstin = models.CharField("GSTIN (optional)", max_length=15, blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(max_length=10, choices=METHOD, default="ONLINE")
    status = models.CharField(max_length=10, choices=STATUS, default="PENDING")
    tracking_note = models.CharField(max_length=200, blank=True, help_text="Courier / tracking no.")

    razorpay_order_id = models.CharField(max_length=60, blank=True, db_index=True)
    razorpay_payment_id = models.CharField(max_length=60, blank=True)
    stock_deducted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} - {self.name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(Variant, on_delete=models.PROTECT)
    product_name = models.CharField(max_length=300)   # snapshot
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    gst_percent = models.DecimalField(max_digits=4, decimal_places=2, default=18)

    @property
    def line_total(self):
        return self.unit_price * self.quantity
