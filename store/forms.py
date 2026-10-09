import re
from django import forms
from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["name", "phone", "email", "address", "city", "pincode", "gstin", "payment_method"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3}),
                   "payment_method": forms.RadioSelect}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for n, f in self.fields.items():
            if n != "payment_method":
                f.widget.attrs["class"] = "form-control"
        self.fields["gstin"].required = False
        self.fields["email"].required = False

    def clean_phone(self):
        p = re.sub(r"\D", "", self.cleaned_data["phone"])[-10:]
        if len(p) != 10:
            raise forms.ValidationError("Enter a valid 10 digit mobile number")
        return p

    def clean_pincode(self):
        p = self.cleaned_data["pincode"].strip()
        if not re.fullmatch(r"\d{6}", p):
            raise forms.ValidationError("Enter a valid 6 digit pincode")
        return p

    def clean_gstin(self):
        g = self.cleaned_data.get("gstin", "").strip().upper()
        if g and not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]", g):
            raise forms.ValidationError("Invalid GSTIN format")
        return g
