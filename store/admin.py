from django.contrib import admin
from .models import Category, Product, Variant, BulkPrice, Order, OrderItem


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 1


class BulkInline(admin.TabularInline):
    model = BulkPrice
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "category", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "brand")
    inlines = [VariantInline]


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ("product", "label", "sku", "mrp", "price", "stock")
    list_editable = ("mrp", "price", "stock")   # quick inventory + price edit
    search_fields = ("sku", "product__name")
    inlines = [BulkInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("variant", "product_name", "quantity", "unit_price", "gst_percent")
    can_delete = False


@admin.action(description="Mark selected as Shipped")
def mark_shipped(modeladmin, request, qs):
    qs.filter(status__in=["PAID", "PACKED"]).update(status="SHIPPED")


@admin.action(description="Mark selected as Delivered")
def mark_delivered(modeladmin, request, qs):
    qs.filter(status="SHIPPED").update(status="DELIVERED")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "total", "payment_method", "status", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    list_editable = ("status",)
    search_fields = ("name", "phone", "razorpay_order_id", "razorpay_payment_id")
    readonly_fields = ("razorpay_order_id", "razorpay_payment_id", "subtotal", "delivery_charge", "total")
    inlines = [OrderItemInline]
    actions = [mark_shipped, mark_delivered]
