from decimal import Decimal

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.db import transaction

from .models import Transaction, UserProfile


User = get_user_model()


class TailwindFormMixin:
    input_class = (
        "w-full rounded-2xl border border-slate-700/80 bg-slate-900/60 px-4 py-3 text-slate-100 "
        "placeholder-slate-500 focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-500"
    )
    checkbox_class = "h-4 w-4 text-teal-500 border-slate-600 rounded focus:ring-teal-500"

    def _style_fields(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", self.checkbox_class)
                continue
            if isinstance(widget, (forms.FileInput, forms.ClearableFileInput)):
                widget.attrs.setdefault(
                    "class",
                    "w-full cursor-pointer rounded-2xl border border-dashed border-slate-600 bg-slate-900/30 px-4 py-3 text-slate-200",
                )
                continue
            widget.attrs.setdefault("class", self.input_class)
            widget.attrs.setdefault("placeholder", widget.attrs.get("placeholder") or field.label)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class RegistrationForm(TailwindFormMixin, forms.Form):
    full_name = forms.CharField(max_length=150, label="Ism")
    email = forms.EmailField(label="Email")
    password1 = forms.CharField(label="Parol", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Parol (tasdiq)", widget=forms.PasswordInput)
    face_reference = forms.ImageField(label="Yuz aniqlash", required=False)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Bu email bilan hisob mavjud.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Parollar mos kelmadi.")
        return cleaned_data

    def save(self):
        full_name = self.cleaned_data["full_name"].strip()
        first_name, _, last_name = full_name.partition(" ")
        email = self.cleaned_data["email"].lower()
        user = User.objects.create_user(
            username=email,
            email=email,
            password=self.cleaned_data["password1"],
            first_name=first_name,
            last_name=last_name,
        )
        profile = getattr(user, "profile", None)
        if profile is None:
            profile = UserProfile.objects.create(user=user)
        face_reference = self.cleaned_data.get("face_reference")
        if face_reference:
            profile.face_reference = face_reference
            profile.is_face_verified = True
            profile.save()
        return user


class LoginForm(TailwindFormMixin, forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Parol", widget=forms.PasswordInput)
    remember_me = forms.BooleanField(label="Eslab qolish", required=False)

    error_messages = {
        "invalid_login": "Email yoki parol noto'g'ri.",
        "inactive": "Profil faol emas.",
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")
        if email and password:
            user = authenticate(self.request, username=email, password=password)
            if user is None:
                raise forms.ValidationError(self.error_messages["invalid_login"])
            if not user.is_active:
                raise forms.ValidationError(self.error_messages["inactive"])
            self.user = user
        return cleaned_data

    def get_user(self):
        return self.user


class TransferForm(TailwindFormMixin, forms.Form):
    recipient_email = forms.EmailField(label="Qabul qiluvchi emaili")
    amount = forms.DecimalField(max_digits=12, decimal_places=2, label="Miqdor")
    note = forms.CharField(label="Izoh", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, sender, *args, **kwargs):
        self.sender = sender
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Miqdor musbat bo'lishi kerak.")
        return amount.quantize(Decimal("0.01"))

    def clean_recipient_email(self):
        email = self.cleaned_data["recipient_email"].lower()
        try:
            self.recipient = User.objects.get(email=email)
        except User.DoesNotExist:
            raise forms.ValidationError("Bunday email topilmadi.")
        if self.recipient == self.sender:
            raise forms.ValidationError("O'zingizga pul yo'llay olmaysiz.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get("amount")
        if amount is not None:
            balance = self.sender.profile.balance
            if amount > balance:
                raise forms.ValidationError("Balansda yetarli mablag' yo'q.")
        return cleaned_data

    def save(self):
        amount = self.cleaned_data["amount"]
        note = self.cleaned_data.get("note", "")
        with transaction.atomic():
            sender_profile = self.sender.profile
            recipient_profile = self.recipient.profile
            sender_profile.balance -= amount
            recipient_profile.balance += amount
            sender_profile.save(update_fields=["balance"])
            recipient_profile.save(update_fields=["balance"])
            Transaction.objects.create(
                user=self.sender,
                amount=amount,
                transaction_type=Transaction.TransactionType.TRANSFER_OUT,
                description=note,
                counterparty=self.recipient.get_full_name() or self.recipient.email,
                performed_by=self.sender,
            )
            Transaction.objects.create(
                user=self.recipient,
                amount=amount,
                transaction_type=Transaction.TransactionType.TRANSFER_IN,
                description=note,
                counterparty=self.sender.get_full_name() or self.sender.email,
                performed_by=self.sender,
            )
        return amount


class TopUpForm(TailwindFormMixin, forms.Form):
    amount = forms.DecimalField(max_digits=12, decimal_places=2, label="Miqdor")
    note = forms.CharField(label="Izoh", required=False)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Miqdor musbat bo'lishi kerak.")
        return amount.quantize(Decimal("0.01"))

    def save(self, user, is_fake=False, performed_by=None):
        amount = self.cleaned_data["amount"]
        note = self.cleaned_data.get("note", "")
        profile = user.profile
        profile.balance += amount
        profile.save(update_fields=["balance"])
        Transaction.objects.create(
            user=user,
            amount=amount,
            transaction_type=(
                Transaction.TransactionType.FAKE_PAYMENT if is_fake else Transaction.TransactionType.TOP_UP
            ),
            description=note,
            performed_by=performed_by,
        )
        return amount


class ProfileForm(TailwindFormMixin, forms.ModelForm):
    full_name = forms.CharField(max_length=150, label="Ism", required=True)
    email = forms.EmailField(label="Email", required=True)

    class Meta:
        model = UserProfile
        fields = ["profile_image", "face_reference", "is_face_verified"]
        widgets = {
            "is_face_verified": forms.CheckboxInput(attrs={"class": "hidden"}),
        }

    def __init__(self, user, *args, **kwargs):
        self.user = user
        kwargs.setdefault("initial", {})
        kwargs["initial"].setdefault("full_name", user.get_full_name() or user.username)
        kwargs["initial"].setdefault("email", user.email)
        super().__init__(*args, **kwargs)
        self.fields["is_face_verified"].disabled = True
        self.fields["is_face_verified"].help_text = "Tasdiqlangan yuz nusxasi bor-yo'qligi."

    def save(self, commit=True):
        full_name = self.cleaned_data["full_name"].strip()
        first_name, _, last_name = full_name.partition(" ")
        self.user.first_name = first_name
        self.user.last_name = last_name
        self.user.email = self.cleaned_data["email"].lower()
        self.user.username = self.user.email
        if commit:
            self.user.save()
        profile = super().save(commit=False)
        if commit:
            profile.save()
        return profile
