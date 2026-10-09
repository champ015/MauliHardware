from django.urls import path
from . import views

urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("product/<slug:slug>/", views.product_detail, name="product"),
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/", views.cart_add, name="cart_add"),
    path("cart/update/", views.cart_update, name="cart_update"),
    path("checkout/", views.checkout, name="checkout"),
    path("payment/verify/", views.payment_verify, name="payment_verify"),
    path("payment/webhook/", views.razorpay_webhook, name="razorpay_webhook"),
    path("order/<int:pk>/", views.order_detail, name="order"),
    path("track/", views.track_order, name="track"),
]
