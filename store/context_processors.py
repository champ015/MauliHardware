from .cart import Cart
from .models import Category


def cart_and_categories(request):
    return {"cart_count": len(Cart(request)), "nav_categories": Category.objects.all()}
