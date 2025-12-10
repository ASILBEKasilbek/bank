from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render
from django.urls import reverse
from rest_framework import viewsets

from .forms import LoginForm, ProfileForm, RegistrationForm, TopUpForm, TransferForm
from .models import Bank, Transaction
from .serializers import BankSerializer


class BankViewSet(viewsets.ModelViewSet):
    queryset = Bank.objects.all()
    serializer_class = BankSerializer


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Hisob muvaffaqiyatli yaratildi.")
            return redirect("dashboard")
    else:
        form = RegistrationForm()
    return render(request, "auth/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if not form.cleaned_data.get("remember_me"):
                request.session.set_expiry(0)
            messages.success(request, "Xush kelibsiz!")
            next_url = request.GET.get("next") or reverse("dashboard")
            return redirect(next_url)
    else:
        form = LoginForm()
    return render(request, "auth/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "Sessiya yopildi.")
    return redirect("login")


def dashboard_view(request):
    if not request.user.is_authenticated:
        sections = [
            {
                "title": "1. Login / Register",
                "description": "Ism, email va yuz aniqlash bilan bir zumda ro'yxattan o'ting.",
                "items": [
                    "Email orqali profil yaratish",
                    "Parolni ikki marta kiritish, tekshiruvlar",
                    "Ixtiyoriy yuz rasmini yuklash",
                ],
            },
            {
                "title": "2. Dashboard",
                "description": "Balans, oxirgi tranzaksiyalar va tezkor tugmalar bir joyda.",
                "items": [
                    "Balans va yangilanish vaqti",
                    "Oxirgi 5 tranzaksiya ro'yxati",
                    "Pul o'tkazish va kartani to'ldirish tugmalari",
                ],
            },
            {
                "title": "3. Profil",
                "description": "Profil rasmi, email, parolni to'liq boshqarish.",
                "items": [
                    "Rasm yuklash va yuz tasdiqlash", "Ism/email yangilash", "Parolni alohida forma orqali almashtirish"
                ],
            },
        ]
        return render(request, "home.html", {"sections": sections})

    profile = request.user.profile
    recent_transactions = request.user.transactions.all()[:5]
    context = {
        "profile": profile,
        "recent_transactions": recent_transactions,
    }
    return render(request, "dashboard.html", context)


@login_required
def transfer_view(request):
    if request.method == "POST":
        form = TransferForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Pul muvaffaqiyatli o'tkazildi.")
            return redirect("dashboard")
    else:
        form = TransferForm(request.user)
    return render(request, "transactions/transfer.html", {"form": form})


@login_required
def top_up_view(request):
    wants_fake = request.GET.get("fake") == "1" or request.POST.get("fake") == "1"
    is_fake = request.user.is_staff and wants_fake
    if request.method == "POST":
        form = TopUpForm(request.POST)
        if form.is_valid():
            form.save(request.user, is_fake=is_fake, performed_by=request.user)
            msg = "Fake to'lov qo'shildi." if is_fake else "Balans to'ldirildi."
            messages.success(request, msg)
            return redirect("dashboard")
    else:
        form = TopUpForm()
    return render(request, "transactions/top_up.html", {"form": form, "is_fake": is_fake})


@login_required
def profile_view(request):
    profile = request.user.profile
    form_type = request.POST.get("form_type") if request.method == "POST" else None
    profile_form = ProfileForm(
        request.user,
        request.POST if form_type == "profile" else None,
        request.FILES if form_type == "profile" else None,
        instance=profile,
    )
    password_form = PasswordChangeForm(user=request.user, data=request.POST if form_type == "password" else None)

    if request.method == "POST":
        if form_type == "profile" and profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Profil yangilandi.")
            return redirect("profile")
        if form_type == "password" and password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Parol muvaffaqiyatli o'zgartirildi.")
            return redirect("profile")

    context = {
        "profile_form": profile_form,
        "password_form": password_form,
        "transactions": request.user.transactions.all()[:5],
    }
    return render(request, "profile.html", context)


def docs_view(request):
    sections = [
        {
            "title": "1. Login / Register",
            "items": [
                "Ism, email va parol asosida ro'yxatdan o'tish",
                "Yuz aniqlash faylini yuklash va tasdiqlash jarayoni",
                "Login formida email+parol, 'remember me' sessiya boshqaruvi",
            ],
        },
        {
            "title": "2. Dashboard",
            "items": [
                "Balans ko'rinishi va oxirgi 5 tranzaksiya",
                "Pul o'tkazish va kartani to'ldirish tugmalari",
                "Profilga o'tish havolasi",
            ],
        },
        {
            "title": "3. Tranzaksiyalar",
            "items": [
                "Email orqali foydalanuvchilar orasida o'tkazma",
                "Balans yetarliligini tekshirish va ikki tomonlama yozuv",
                "Adminlar uchun fake to'lov rejimi",
            ],
        },
        {
            "title": "4. Profil",
            "items": [
                "Profil rasmi, ism/email yangilash",
                "Yuz tasdiqlanish statusi",
                "Parolni o'zgartirish uchun alohida forma",
            ],
        },
        {
            "title": "5. Admin panel",
            "items": [
                "Superuser barcha foydalanuvchi va tranzaksiyalarni ko'radi",
                "Balans o'zgartirish, fake to'lov qo'shish imkoni",
                "Jazzmin interfeysi bilan zamonaviy UI",
            ],
        },
    ]
    api_endpoints = [
        {"method": "GET", "path": "/api/banks/", "desc": "Banklar ro'yxati (DRF API)"},
    ]
    return render(request, "docs.html", {"sections": sections, "api_endpoints": api_endpoints})
