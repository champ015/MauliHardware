"""Session based cart: {variant_id: qty}"""
from decimal import Decimal
from django.conf import settings
from .models import Variant


class Cart:
    KEY = "cart"

    def __init__(self, request):
        self.session = request.session
        self.data = self.session.setdefault(self.KEY, {})

    def _save(self):
        self.session.modified = True

    def add(self, variant_id, qty=1, replace=False):
        k = str(variant_id)
        new = qty if replace else self.data.get(k, 0) + qty
        if new <= 0:
            self.data.pop(k, None)
        else:
            self.data[k] = new
        self._save()

    def remove(self, variant_id):
        self.data.pop(str(variant_id), None)
        self._save()

    def clear(self):
        self.session[self.KEY] = {}
        self._save()

    def __len__(self):
        return sum(self.data.values())

    def lines(self):
        variants = Variant.objects.select_related("product").filter(id__in=self.data.keys())
        out = []
        for v in variants:
            qty = self.data[str(v.id)]
            if v.stock:
                qty = min(qty, v.stock)
            price = v.unit_price_for(qty)
            out.append({"variant": v, "qty": qty, "unit_price": price, "total": price * qty})
        return out

    def subtotal(self):
        return sum((l["total"] for l in self.lines()), Decimal("0"))


def delivery_charge(pincode, subtotal):
    if subtotal >= settings.FREE_DELIVERY_ABOVE:
        return Decimal("0")
    if pincode.startswith(settings.LOCAL_PINCODE_PREFIXES):
        return Decimal(settings.LOCAL_DELIVERY_CHARGE)
    return Decimal(settings.OUTSIDE_DELIVERY_CHARGE)
