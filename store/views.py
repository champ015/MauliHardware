import json
import razorpay
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Min, Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .cart import Cart, delivery_charge
from .forms import CheckoutForm
from .models import Category, Order, OrderItem, Product, Variant


def _rzp():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


# ---------- Catalog ----------
def catalog(request):
    qs = (Product.objects.filter(is_active=True)
          .select_related("category").annotate(min_price=Min("variants__price")))
    q = request.GET.get("q", "").strip()
    cat = request.GET.get("category", "")
    sort = request.GET.get("sort", "")
    pmin, pmax = request.GET.get("min"), request.GET.get("max")

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(brand__icontains=q) |
                       Q(description__icontains=q) | Q(category__name__icontains=q))
    if cat:
        qs = qs.filter(category__slug=cat)
    if pmin and pmin.isdigit():
        qs = qs.filter(min_price__gte=pmin)
    if pmax and pmax.isdigit():
        qs = qs.filter(min_price__lte=pmax)
    qs = qs.order_by({"price_asc": "min_price", "price_desc": "-min_price",
                      "rating": "-rating"}.get(sort, "-created_at"))

    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "store/catalog.html", {
        "page": page, "q": q, "current_cat": cat, "sort": sort,
        "pmin": pmin or "", "pmax": pmax or "", "qs": params.urlencode(),
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    variants = list(product.variants.prefetch_related("bulk_prices"))
    return render(request, "store/product.html", {"product": product, "variants": variants})


# ---------- Cart ----------
@require_POST
def cart_add(request):
    v = get_object_or_404(Variant, pk=request.POST.get("variant"))
    try:
        qty = max(1, int(request.POST.get("qty", 1)))
    except ValueError:
        qty = 1
    if not v.in_stock:
        messages.error(request, "Out of stock.")
        return redirect("product", slug=v.product.slug)
    cart = Cart(request)
    cart.add(v.id, min(qty, v.stock))
    if request.POST.get("buy_now"):
        return redirect("checkout")
    messages.success(request, f"{v.product.name} added to cart.")
    return redirect("cart")


@require_POST
def cart_update(request):
    cart = Cart(request)
    vid = request.POST.get("variant")
    if request.POST.get("remove"):
        cart.remove(vid)
    else:
        try:
            cart.add(vid, int(request.POST.get("qty", 1)), replace=True)
        except ValueError:
            pass
    return redirect("cart")


def cart_view(request):
    cart = Cart(request)
    return render(request, "store/cart.html", {"lines": cart.lines(), "subtotal": cart.subtotal()})


# ---------- Checkout & payment ----------
@transaction.atomic
def _create_order(request, form, cart):
    lines = cart.lines()
    for l in lines:                       # re-check stock
        if l["variant"].stock < l["qty"]:
            raise ValueError(f"Only {l['variant'].stock} left of {l['variant']}")
    subtotal = cart.subtotal()
    ship = delivery_charge(form.cleaned_data["pincode"], subtotal)
    order = form.save(commit=False)
    order.user = request.user if request.user.is_authenticated else None
    order.subtotal, order.delivery_charge, order.total = subtotal, ship, subtotal + ship
    order.save()
    for l in lines:
        OrderItem.objects.create(
            order=order, variant=l["variant"], quantity=l["qty"], unit_price=l["unit_price"],
            product_name=f"{l['variant'].product.name} ({l['variant'].label})",
            gst_percent=l["variant"].product.gst_percent)
    return order


def _mark_paid_and_deduct(order, payment_id=""):
    """Idempotent: safe if called by both verify view and webhook."""
    with transaction.atomic():
        o = Order.objects.select_for_update().get(pk=order.pk)
        if o.stock_deducted:
            return o
        for item in o.items.select_related("variant"):
            v = Variant.objects.select_for_update().get(pk=item.variant_id)
            v.stock = max(0, v.stock - item.quantity)
            v.save(update_fields=["stock"])
        o.stock_deducted = True
        if o.payment_method == "ONLINE":
            o.status = "PAID"
            o.razorpay_payment_id = payment_id or o.razorpay_payment_id
        o.save()
        return o


def checkout(request):
    cart = Cart(request)
    if not cart.data:
        return redirect("cart")
    form = CheckoutForm(request.POST or None)
    subtotal = cart.subtotal()
    if request.method == "POST" and form.is_valid():
        try:
            order = _create_order(request, form, cart)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("cart")
        if order.payment_method == "COD":
            _mark_paid_and_deduct(order)
            cart.clear()
            return redirect("order", pk=order.pk)
        rz = _rzp().order.create({"amount": int(order.total * 100), "currency": "INR",
                                  "receipt": f"order_{order.pk}", "payment_capture": 1})
        order.razorpay_order_id = rz["id"]
        order.save(update_fields=["razorpay_order_id"])
        request.session["pending_order"] = order.pk
        return render(request, "store/pay.html", {
            "order": order, "key_id": settings.RAZORPAY_KEY_ID, "amount": int(order.total * 100)})
    return render(request, "store/checkout.html", {
        "form": form, "lines": cart.lines(), "subtotal": subtotal,
        "free_above": settings.FREE_DELIVERY_ABOVE})


@require_POST
def payment_verify(request):
    """Server side signature verification - never trust the browser."""
    p = request.POST
    try:
        order = Order.objects.get(razorpay_order_id=p.get("razorpay_order_id", ""))
        _rzp().utility.verify_payment_signature({
            "razorpay_order_id": p["razorpay_order_id"],
            "razorpay_payment_id": p["razorpay_payment_id"],
            "razorpay_signature": p["razorpay_signature"]})
    except Exception:
        Order.objects.filter(razorpay_order_id=p.get("razorpay_order_id", ""),
                             status="PENDING").update(status="FAILED")
        messages.error(request, "Payment verification failed. If money was deducted, it will be refunded.")
        return redirect("cart")
    _mark_paid_and_deduct(order, p["razorpay_payment_id"])
    Cart(request).clear()
    return redirect("order", pk=order.pk)


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """Backup confirmation if customer closes browser after paying."""
    sig = request.headers.get("X-Razorpay-Signature", "")
    body = request.body.decode()
    try:
        _rzp().utility.verify_webhook_signature(body, sig, settings.RAZORPAY_WEBHOOK_SECRET)
    except Exception:
        return HttpResponseBadRequest("bad signature")
    data = json.loads(body)
    if data.get("event") in ("payment.captured", "order.paid"):
        ent = data["payload"].get("payment", {}).get("entity", {})
        order = Order.objects.filter(razorpay_order_id=ent.get("order_id", "")).first()
        if order:
            _mark_paid_and_deduct(order, ent.get("id", ""))
    return HttpResponse("ok")


# ---------- Orders ----------
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    allowed = request.user.is_staff or request.session.get("pending_order") == pk \
        or request.session.get("track_ok") == pk
    if not allowed:
        return redirect("track")
    return render(request, "store/order.html", {"order": order})


def track_order(request):
    if request.method == "POST":
        o = Order.objects.filter(pk=request.POST.get("order_id") or 0,
                                 phone=request.POST.get("phone", "")[-10:]).first()
        if o:
            request.session["track_ok"] = o.pk
            return redirect("order", pk=o.pk)
        messages.error(request, "Order not found. Check order number and phone.")
    return render(request, "store/track.html")
