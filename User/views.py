from datetime import date
import random
import re
import string
import time
from django.core.paginator import Paginator
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate, login as authlogin, logout as authlogout, update_session_auth_hash
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.core.mail import send_mail
import razorpay
from coupon_app.models import Coupons, Coupon_user
from product_app.models import Product
from variant_app.models import Variant
from category_app.models import Paint, Art
from django.shortcuts import get_object_or_404
from User.models import Address, Cart
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .models import Order, Order_details, Review, Wishlist, Return
from django.http import JsonResponse
from django.db import transaction
from django.conf import settings
from .models import Cart, Address, Order, Order_details, Wallet, Wallet_Transaction, OrderAddress, UserInformations
from decimal import Decimal
from reportlab.lib.pagesizes import A4  # type: ignore
from reportlab.lib import colors  # type: ignore
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle  # type: ignore
from django.http import HttpResponse
from .models import Order, Order_details  # Import your models
from django.core.mail import send_mail


# ========================= USER SIGNUP ===================== #

@never_cache
def signup(request):
    if request.method == 'POST':
        username = request.POST['username'].strip()
        email = request.POST['email'].strip()
        password1 = request.POST['password1'].strip()
        password2 = request.POST['password2'].strip()

        if User.objects.filter(username=username).exists():
            messages.info(request, 'Username already taken')
            return redirect('signup')

        if User.objects.filter(email=email).exists():
            messages.info(request, 'Email is already registered')
            return redirect('signup')

        try:
            validate_email(email)
        except ValidationError:
            messages.info(request, 'Invalid email address')
            return redirect('signup')

        if password1 != password2:
            messages.info(request, 'Password does not match !')
            return redirect('signup')
        else:
            # Store user info in session instead of creating the user
            request.session['signup_username'] = username
            request.session['signup_email'] = email
            request.session['signup_password'] = password1

            generated_otp = create_otp()
            send_otp_email(email, generated_otp)
            store_otp_in_session(request, generated_otp)
            request.session['email'] = email
            return redirect('otp')

    return render(request, 'user/signup.html')


# =========================== USER OTP SECTION ========================= #

def create_otp(length=4):
    digits = string.digits
    generated_otp = ''.join(random.choice(digits) for _ in range(length))
    return generated_otp


def send_otp_email(user_email, generated_otp):
    subject = 'Your OTP Code'
    message = f'Your OTP code is {generated_otp}. It is valid for 1 minute.'
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email])
    except Exception as e:
        print(f"Failed to send OTP email: {e}")


def store_otp_in_session(request, generated_otp):
    expiry_time = time.time() + 60  # OTP valid for 1 minute
    request.session['generated_otp'] = generated_otp
    request.session['otp_expiry'] = expiry_time


def is_otp_valid(request, input_otp):
    stored_otp = request.session.get('generated_otp')
    expiry_time = request.session.get('otp_expiry')

    if not stored_otp or not expiry_time:
        return False
    if time.time() < expiry_time and stored_otp == input_otp:
        return True
    return False


def otp(request):
    if request.method == 'POST':
        input_otp = request.POST.get('input_otp')
        if is_otp_valid(request, input_otp):
            # Retrieve user info from session
            username = request.session.get('signup_username')
            email = request.session.get('signup_email')
            password = request.session.get('signup_password')

            # Create the user after OTP validation
            user = User.objects.create_user(username=username, email=email, password=password)

            # Clear session data
            del request.session['signup_username']
            del request.session['signup_email']
            del request.session['signup_password']
            del request.session['generated_otp']
            del request.session['otp_expiry']

            return redirect('login')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            return redirect('otp')

    otp_expiry = request.session.get('otp_expiry', 0)
    remaining_time = int(otp_expiry - time.time())
    remaining_time = max(remaining_time, 0)

    return render(request, 'user/otp.html', {
        'remaining_time': remaining_time
    })


# ========================= USER LOGIN ============================= #

@never_cache
def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user:
            authlogin(request, user)
            return redirect('home')
        else:
            messages.info(request, 'INVALID USERNAME OR PASSWORD')
            return redirect('login')
    return render(request, 'user/login.html')


def resend_otp(request):
    email = request.session.get('email')

    if not email:
        messages.error(request, 'Email not found in session. Please start the signup process again.')
        return redirect('signup')

    otp = create_otp()
    send_otp_email(email, otp)
    store_otp_in_session(request, otp)
    messages.success(request, 'A new OTP has been sent to your email.')
    return redirect('otp')


# ======================= USER LOGOUT ========================= #

def user_logout(request):
    logout(request)
    return redirect('home')


# ======================= RESET PASSWORD ========================= #

def email_verify(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if User.objects.filter(email=email).exists():
            otp = create_otp()
            send_otp_email(email, otp)
            store_otp_in_session(request, otp)
            request.session['email'] = email
            return redirect('password_otp')
        else:
            messages.error(request, 'Email address not found.')
            return redirect('email_varify')
    return render(request, 'user/emailvarify.html')


def password_otp(request):
    if request.method == 'POST':
        input_otp = request.POST.get('otp')
        if not input_otp:
            messages.error(request, 'Please enter the OTP.')
            return redirect('password_otp.html')
        if is_otp_valid(request, input_otp):
            messages.success(request, 'OTP verified successfully!')
            return redirect('new_password')
        else:
            messages.error(request, 'Invalid or expired OTP. Please try again.')
            redirect('password_otp')

    otp_expiration = request.session.get('otp_expiration', 0)
    remaining_time = int(otp_expiration - time.time())
    remaining_time = max(remaining_time, 0)

    return render(request, 'user/password_otp.html', {'remaining_time': remaining_time})


def resend_otp_password(request):
    email = request.session.get('email')
    if not email:
        messages.error(request, 'Email not found in session. Please start the signup process again.')
        return redirect('email_varify')
    otp = create_otp()
    send_otp_email(email, otp)
    store_otp_in_session(request, otp)
    messages.success(request, 'A new OTP has been sent to your email.')
    return redirect('password_otp')


def new_password(request):
    email = request.session.get('email')
    if request.method == 'POST':
        newpassword = request.POST.get('newpassword')
        confirm_password = request.POST.get('confirmpassword')
        if len(newpassword) < 8:
            messages.error(request, 'New password must be at least 8 characters long.')
        elif newpassword != confirm_password:
            messages.error(request, 'The new password and confirm password do not match.')
        else:
            try:
                user = User.objects.get(email=email)
                user.set_password(newpassword)
                user.save()
                messages.success(request, 'Password changed successfully. Please log in with your new password.')
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, 'No user found with the provided email address.')

    return render(request, 'user/newpassword.html')


# ========================= HOME SECTION =========================== #

def home(request):
    arrivals = Product.objects.filter(
        Q(product_status=True) & Q(variants__isnull=False)
    ).distinct().order_by('-id')[:3]

    try:
        user = request.user
        if user.is_authenticated:
            customer = user.username
        else:
            customer = None
    except Exception as e:
        customer = None

    populars = Product.objects.filter(product_status=True)[:4]
    context = {
        'arrivals': arrivals,
        'populars': populars,
        'customer': customer
    }
    return render(request, 'user/home.html', context)


# ========================= SHOP SECTION ========================= #

def shop(request):
    try:
        user = request.user
        if user.is_authenticated:
            customer = user.username
        else:
            customer = None
    except Exception as e:
        customer = None
    search_query = request.GET.get('q', '').strip()
    selected_categories = request.POST.getlist('categories') if request.method == 'POST' else []
    selected_size = request.POST.getlist('size') if request.method == 'POST' else []
    price_order = request.POST.get('price_order') if request.method == 'POST' else None
    products = Product.objects.filter(
        Q(product_status=True) &
        Q(variants__isnull=False) &
        Q(art_category__art_type_status=True)
    ).distinct()
    if selected_categories:
        products = products.filter(art_category__id__in=selected_categories)

    if selected_size:
        products = products.filter(variants__id__in=selected_size)

    if price_order:
        if price_order == 'asc':
            products = products.order_by('variants__price')
        elif price_order == 'desc':
            products = products.order_by('-variants__price')

    if search_query:
        products = products.filter(product_name__icontains=search_query)

    paginator = Paginator(products, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    no_products_found = not products.exists()
    unique_frame_sizes = Variant.objects.order_by('frame_size').distinct()
    paints = Paint.objects.filter(paint_type_status=True)
    arts = Art.objects.filter(art_type_status=True)

    context = {
        'products': page_obj.object_list,
        'paints': paints,
        'arts': arts,
        'variants': unique_frame_sizes,
        'selected_categories': selected_categories,
        'selected_size': selected_size,
        'no_products_found': no_products_found,
        'search_query': search_query,
        'page_obj': page_obj,
        'customer': customer
    }

    return render(request, 'user/shop.html', context)


# ========================== SINGLE PRODUCT SECTION ========================== #

def single(request, product_id, variant_id):
    try:
        user = request.user
        if user.is_authenticated:
            customer = user.username
        else:
            customer = None
    except Exception as e:
        customer = None
    product = get_object_or_404(Product, id=product_id)
    variant = get_object_or_404(Variant, id=variant_id)
    sizes = Variant.objects.filter(product=product)
    related_product = Product.objects.filter(art_category=product.art_category).exclude(id=product.id)[:3]
    in_cart = None
    in_wishlist = None
    reviews = Review.objects.filter(variant=variant)[:2]

    if product.product_status == False:
        messages.error(request, "Item currently unavailable")
        return redirect('shop')

    if product.art_category.art_type_status == False:
        messages.error(request, "Item currently unavailable")
        return redirect('shop')

    if request.user.is_authenticated:
        in_cart = Cart.objects.filter(user=request.user, variant=variant).exists()
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, variant=variant).exists()

    offer_price = product.art_category.art_type_offer or 0
    variant_amount = variant.price
    offer_amount = None
    if offer_price > 0:
        offer_amount = variant_amount * (Decimal(1) - (Decimal(offer_price) / Decimal(100)))

    else:
        offer_amount = 0

    offer_display = f"{offer_price}% OFF" if offer_price > 0 else "0% OFF"

    return render(request, 'user/single.html', {
        'product': product,
        'variant': variant,
        'sizes': sizes,
        'in_cart': in_cart,
        'in_wishlist': in_wishlist,
        'reviews': reviews,
        'related_product': related_product,
        'variant_amount': variant_amount,
        'offer_amount': offer_amount,
        'offer_display': offer_display,
        'customer': customer
    })


def add_wishlist_single(request, product_id, variant_id):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to add items to your wishlist.")
        return redirect('login')

    product = get_object_or_404(Product, id=product_id)

    if product.product_status == False:
        messages.error(request, "Item currently unavailable")
        return redirect('shop')

    if product.art_category.art_type_status == False:
        messages.error(request, "Item currently unavailable")
        return redirect('shop')

    variant = get_object_or_404(Variant, id=variant_id)
    Wishlist.objects.create(product=product, user=request.user, variant=variant)
    messages.success(request, "Item has been added to your wishlist.")

    return redirect('single', product_id=product.id, variant_id=variant.id)


# ====================== DEMO VIEW FUNCTIONS =================== #

def jasir(request):
    return render(request, 'user/jasir.html')


def error(request):
    return render(request, 'user/error.html')


def change(request):
    return render(request, 'user/password_verify.html')


# ======================= ABOUT US =========================== #

def about_us(request):
    return render(request, 'user/about_us.html')


def contact_us(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        subject = f"Contact Form Submission by {name}"
        body = f"""
        Name: {name}
        Email: {email}

        Message:
        {message}
        """
        try:
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [settings.CONTACT_EMAIL],
                fail_silently=False,
            )
            messages.info(request, "Your message has been sent successfully!")
            return redirect('contact_us')
        except Exception as e:
            print(f"Error sending email: {e}")

    return render(request, 'user/contact_us.html')


# ======================= USER PROFILE SECTION ===================== #

def profile(request):
    if not request.user.is_authenticated:
        messages.info(request, "PLEASE LOGIN.")
        return redirect('login')

    if request.method == 'POST':
        fullname = request.POST.get('fullname')
        mobile = request.POST.get('mobile')
        pincode = request.POST.get('pincode')
        address = request.POST.get('address')
        city = request.POST.get('city')
        district = request.POST.get('district')
        state = request.POST.get('state')

        errors = []

        if not fullname or len(fullname) < 3 or not fullname.replace(" ", "").isalpha():
            errors.append("Fullname must be at least 3 characters long.")

        if not fullname.replace(" ", "").isalpha():
            errors.append("Fullname must contain only alphabets")

        pattern = r"^[6-9]\d{9}$"

        if not re.match(pattern, mobile):
            errors.append("Please Enter Valid Phone Number")

        if not pincode.isdigit() or len(pincode) != 6:
            errors.append("Pincode must be a 6-digit number.")

        if not address or len(address) < 5:
            errors.append("Address must be at least 5 characters long.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('profile')

        Address.objects.create(
            fullname=fullname,
            mobile=mobile,
            pincode=pincode,
            address=address,
            city=city,
            district=district,
            state=state,
            user_id=request.user
        )
        return redirect('profile')

    informations = Address.objects.filter(user_id_id=request.user)

    try:
        user_info = UserInformations.objects.get(user_id=request.user)
    except UserInformations.DoesNotExist:
        user_info = None

    if request.user.is_authenticated:
        username = request.user.username
        email = request.user.email
        password = request.user.password
    coupons = Coupons.objects.all()
    used_coupon_ids = Coupon_user.objects.filter(user=request.user).values_list('coupon_used_id', flat=True)
    for coupon in coupons:
        coupon.is_used = coupon.id in used_coupon_ids
        coupon.is_expired = coupon.expiry_date < date.today()
    no_coupon_found = not coupons.exists()
    wallet, created = Wallet.objects.get_or_create(user=request.user, defaults={'wallet_amount': 0})
    wallet_transaction = Wallet_Transaction.objects.filter(user=request.user).order_by('-id')
    no_wallet_found = not wallet_transaction.exists()

    context = {
        'informations': informations,
        'user_info': user_info,
        'username': username,
        'email': email,
        'coupons': coupons,
        'wallet': wallet,
        'wallet_transaction': wallet_transaction,
        'no_coupon_found': no_coupon_found,
        'no_wallet_found': no_wallet_found
    }

    return render(request, 'user/profile.html', context)


def edit_address(request):
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        fullname = request.POST.get('fullname').strip()
        mobile = request.POST.get('mobile').strip()
        pincode = request.POST.get('pincode').strip()
        address = request.POST.get('address').strip()
        city = request.POST.get('city').strip().replace(" ", "")
        district = request.POST.get('district').strip().replace(" ", "")
        state = request.POST.get('state').strip().replace(" ", "")

        errors = []

        if not fullname or len(fullname) < 3 or not fullname.replace(" ", "").isalpha():
            errors.append("Fullname must be at least 3 characters long.")

        if not fullname.replace(" ", "").isalpha():
            errors.append("Fullname must contain only alphabets")

        pattern = r"^[6-9]\d{9}$"

        if not re.match(pattern, mobile):
            errors.append("Please Enter Valid Phone Number")

        if not pincode.isdigit() or len(pincode) != 6:
            errors.append("Pincode must be a 6-digit number.")

        if not address or len(address) < 5:
            errors.append("Address must be at least 5 characters long.")

        if not city or not re.match(r"^[a-zA-Z\s]+$", city):
            errors.append("City must contain only alphabets and spaces.")

        if not district or not re.match(r"^[a-zA-Z\s]+$", district):
            errors.append("District must contain only alphabets and spaces.")

        if not state or not re.match(r"^[a-zA-Z\s]+$", state):
            errors.append("State must contain only alphabets and spaces.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('profile')

        if address_id:
            address_instance = get_object_or_404(Address, id=address_id)
            address_instance.fullname = fullname
            address_instance.mobile = mobile
            address_instance.pincode = pincode
            address_instance.address = address
            address_instance.city = city
            address_instance.district = district
            address_instance.state = state
            address_instance.save()
        else:
            Address.objects.create(
                fullname=fullname, mobile=mobile, pincode=pincode,
                address=address, city=city, district=district, state=state, user_id=request.user
            )
        return redirect('profile')


def remove_address_profile(request, address_id):
    address = Address.objects.filter(id=address_id)
    address.delete()
    return redirect('profile')


def personal_info(request):
    user = request.user
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        mobile = request.POST.get('mobile')
        gender = request.POST.get('gender')

        user_info, created = UserInformations.objects.update_or_create(
            user=user,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'mobile': mobile,
                'gender': gender,

            }
        )

    return redirect('profile')


# ======================= CHANGE PASSWORD SECTION =================== #

def password_verify(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        if check_password(old_password, request.user.password):
            return redirect('password_change')
        else:
            messages.error(request, '')
            return redirect('password_verify')

    return render(request, 'user/password_verify.html')


def password_change(request):
    if request.method == "POST":
        newpassword = request.POST.get('newpassword')
        confirm_password = request.POST.get('confirm_password')

        if newpassword == confirm_password:
            user = request.user
            user.set_password(newpassword)
            user.save()
            update_session_auth_hash(request, request.user)
            return redirect('profile')

    return render(request, 'user/password_change.html')


# ========================== CART SECTION ====================== #


def cart(request):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to view Cart.")
        return redirect('login')

    all_cart_items = Cart.objects.filter(user=request.user).order_by('-id')
    items_to_delete = all_cart_items.filter(product__product_status=False)
    if items_to_delete.exists():
        items_to_delete.delete()

    cart_items = Cart.objects.filter(user=request.user, product__product_status=True).order_by('-id')
    is_empty = not cart_items.exists()

    cart_items_with_offer_price = []

    for item in cart_items:
        product = item.product
        art_category = product.art_category

        if art_category.art_type_offer:
            offer_price = item.variant.price - (item.variant.price * art_category.art_type_offer / 100)
        else:
            offer_price = item.variant.price
        cart_items_with_offer_price.append({
            'item': item,
            'offer_price': offer_price
        })
    return render(request, 'user/cart.html', {
        'cart_items_with_offer_price': cart_items_with_offer_price,
        'is_empty': is_empty
    })


def add_cart(request, product_id, variant_id):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to add items to your cart.")
        return redirect('login')

    product_id = get_object_or_404(Product, id=product_id)
    variant_id = get_object_or_404(Variant, id=variant_id)

    if product_id.product_status == False:
        messages.error(request, "Item currently unavailable")
        return redirect('shop')

    if product_id.art_category.art_type_status == False:
        messages.error(request, "Item currently unavailable")
        return redirect('shop')

    cart_item_exists = Cart.objects.filter(variant=variant_id, user=request.user).exists()
    if cart_item_exists:
        messages.warning(request, "This item is already in your cart.")
        return redirect('single', product_id=product_id.id, variant_id=variant_id.id)
    Cart.objects.create(product=product_id, user=request.user, variant=variant_id)
    return redirect('cart')


def remove_cart_item(request, variant_id):
    cart_items = Cart.objects.get(variant=variant_id, user=request.user)
    cart_items.delete()
    return redirect('cart')


# ========================== CHECK OUT SECTION ====================== #

def checkout_og(request):
    if request.method == 'POST':
        total_price = request.POST.get('total_price')
        quantities = {
            key.split('_')[1]: int(value)
            for key, value in request.POST.items()
            if key.startswith('quantity_')
        }

        for variant_id, quantity in quantities.items():
            variant = get_object_or_404(Variant, id=variant_id)

            if variant.product.product_status == False:
                messages.error(request, f"{variant.product.product_name} is currently unavailable !")
                return redirect('cart')

            if quantity < 1:
                messages.error(request, "Quantity cannot be less than 1.")
                return redirect('cart')

            if quantity > 10:
                messages.error(request, "Purchase quantity cannot exceed 10.")
                return redirect('cart')

            if quantity > variant.stock:
                messages.error(request, f"{variant.product.product_name} is Out of stock !")
                return redirect('cart')

            cart_item = get_object_or_404(Cart, user=request.user, variant_id=variant_id, product__product_status=True)

            cart_item.quantity = quantity
            cart_item.save()
        request.session[f'quantity_{variant_id}'] = quantity

        request.session['total_price'] = total_price

        return redirect('checkout')

    return redirect('cart')


def checkout(request):
    em = Cart.objects.filter(user=request.user)
    if not em:
        return redirect('home')

    if not request.user.is_authenticated:
        messages.info(request, "PLEASE LOGIN.")
        return redirect('login')

    stock_error = validate_stock(request.user)
    if stock_error:
        messages.error(request, stock_error)
        return redirect('cart')

    status_error = validate_status(request.user)
    if status_error:
        messages.error(request, status_error)
        return redirect('cart')

    if request.method == 'POST':
        fullname = request.POST.get('fullname')
        mobile = request.POST.get('mobile')
        pincode = request.POST.get('pincode')
        address = request.POST.get('address')
        city = request.POST.get('city')
        district = request.POST.get('district')
        state = request.POST.get('state')

        errors = []

        stock_error = validate_stock(request.user)
        if stock_error:
            messages.error(request, stock_error)
            return redirect('cart')

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('checkout')

        Address.objects.create(
            fullname=fullname,
            mobile=mobile,
            pincode=pincode,
            address=address,
            city=city,
            district=district,
            state=state,
            user_id=request.user
        )
        return redirect('checkout')

    all_address = Address.objects.filter(user_id_id=request.user)
    total_price = request.session.get('total_price', 0)

    cart_items = Cart.objects.filter(user=request.user, product__product_status=True)
    used_coupon_ids = Coupon_user.objects.filter(user=request.user).values_list('coupon_used_id', flat=True)
    coupons = Coupons.objects.exclude(id__in=used_coupon_ids).filter(expiry_date__gte=date.today())

    try:
        wallet = Wallet.objects.get(user=request.user)
        wallet_balance = wallet.wallet_amount if wallet.wallet_amount is not None and wallet.wallet_amount > 0 else 0
    except Wallet.DoesNotExist:
        wallet_balance = 0

    context = {
        'all_address': all_address,
        'total_price': total_price,
        'cart_items': cart_items,
        'wallet_balance': wallet_balance,
        'coupons': coupons
    }

    return render(request, 'user/checkout.html', context)


def validate_stock(user):
    cart_items = Cart.objects.filter(user=user)
    for item in cart_items:
        variant = get_object_or_404(Variant, id=item.variant_id)
        product = variant.product

        if item.quantity > variant.stock:
            return f"{product.product_name} is out of stock!"

        if not product.art_category.art_type_status:
            return f"{product.product_name} is currently unavailable!"

        if not variant.variant_status:
            return f"The selected frame size of {product.product_name} is currently unavailable!"

    return None


def validate_status(user):
    cart_items = Cart.objects.filter(user=user)
    for item in cart_items:
        variant = get_object_or_404(Variant, id=item.variant_id)
        product = variant.product
        if not product.product_status:
            return f"{product.product_name} is currently unavailable!"

    return None


def edit_address_checkout(request):
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        fullname = request.POST.get('fullname').strip()
        mobile = request.POST.get('mobile').strip()
        pincode = request.POST.get('pincode').strip()
        address = request.POST.get('address').strip()
        city = request.POST.get('city').strip().replace(" ", "")
        district = request.POST.get('district').strip().replace(" ", "")
        state = request.POST.get('state').strip().replace(" ", "")

        errors = []

        if not fullname or len(fullname) < 3 or not fullname.replace(" ", "").isalpha():
            errors.append("Fullname must be at least 3 characters long.")

        if not fullname.replace(" ", "").isalpha():
            errors.append("Fullname must contain only alphabets")

        pattern = r"^[6-9]\d{9}$"

        if not re.match(pattern, mobile):
            errors.append("Please Enter Valid Phone Number")

        if not pincode.isdigit() or len(pincode) != 6:
            errors.append("Pincode must be a 6-digit number.")

        if not address or len(address) < 5:
            errors.append("Address must be at least 5 characters long.")

        if not city or not re.match(r"^[a-zA-Z\s]+$", city):
            errors.append("City must contain only alphabets and spaces.")

        if not district or not re.match(r"^[a-zA-Z\s]+$", district):
            errors.append("District must contain only alphabets and spaces.")

        if not state or not re.match(r"^[a-zA-Z\s]+$", state):
            errors.append("State must contain only alphabets and spaces.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('checkout')

        if address_id:
            address_instance = get_object_or_404(Address, id=address_id)
            address_instance.fullname = fullname
            address_instance.mobile = mobile
            address_instance.pincode = pincode
            address_instance.address = address
            address_instance.city = city
            address_instance.district = district
            address_instance.state = state
            address_instance.save()
        else:
            Address.objects.create(
                fullname=fullname, mobile=mobile, pincode=pincode,
                address=address, city=city, district=district, state=state, user_id=request.user
            )
        return redirect('checkout')


def remove_address(request, address_id):
    address = Address.objects.filter(id=address_id)
    address.delete()
    return redirect('checkout')


# ===================== PLACE ORDER SECTION ================== #

def place_order(request):
    cart_items = Cart.objects.filter(user=request.user)
    if not cart_items:
        return redirect('home')

    # for i in cart_items:
    #     if i.product.art_category.art_type_offer > 0:
    #         print(i.product.art_category.art_type_offer)

    if request.method == 'POST':

        payment_method = request.POST.get('payment_method')
        selected_address_id = request.POST.get('selected_address')
        total_price = int(request.session.get('total_price', 0)) * 100
        coupon_discount_price = request.POST.get('final_price', None)
        ##getting selected coupon code
        selected_coupon_code = request.POST.get('selected_coupon_code', None)
        coupon = None
        coupon_percentage = None
        if selected_coupon_code:

            try:
                coupon = Coupons.objects.get(coupon_code=selected_coupon_code)
                coupon_percentage = coupon.percentage
                Coupon_user.objects.create(
                    user=request.user,
                    coupon_used=coupon
                )
            except Coupons.DoesNotExist:
                messages.error(request, "The selected coupon is invalid or has been deleted.")
                return redirect('checkout')

        if coupon_discount_price:
            final_amount = int(float(coupon_discount_price) * 100)  # Convert to paise
        else:
            final_amount = total_price

        if not selected_address_id:
            messages.error(request, "Please select a valid address.")
            return redirect('checkout')

        try:
            selected_address = Address.objects.get(id=selected_address_id)
        except Address.DoesNotExist:
            messages.error(request, "The selected address is invalid or does not belong to you.")
            return redirect('checkout')

        stock_error = validate_stock(request.user)
        if stock_error:
            messages.error(request, stock_error)
            return redirect('cart')

        status_error = validate_status(request.user)
        if status_error:
            messages.error(request, status_error)
            return redirect('shop')

        if payment_method == 'COD':
            order = Order.objects.create(
                user=request.user,
                total_amount=final_amount / 100,
                payment_method=payment_method,
                coupon=coupon,
                coupon_name=selected_coupon_code,
                coupon_percentage=coupon_percentage
            )

            OrderAddress.objects.create(
                order=order,
                fullname=selected_address.fullname,
                mobile=selected_address.mobile,
                pincode=selected_address.pincode,
                address=selected_address.address,
                district=selected_address.district,
                city=selected_address.city,
                state=selected_address.state
            )

            for item in cart_items:
                offer_percentage = item.product.art_category.art_type_offer or 0
                offer_amount = item.variant.price * offer_percentage / 100
                final_offer_price = item.variant.price - offer_amount
                coupon_item_final_amount = final_offer_price

                if coupon_percentage:

                    coupon_item_amount = final_offer_price * coupon_percentage / 100
                    coupon_item_final_amount = final_offer_price - coupon_item_amount

                Order_details.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    variant=item.variant,
                    offer=offer_percentage,
                    item_coupon_amount=coupon_item_final_amount
                )
                item.variant.stock -= item.quantity
                item.variant.save()

            cart_items.delete()

            return redirect('order_placed')

        elif payment_method == 'Razorpay':
            order = Order.objects.create(
                user=request.user,
                total_amount=final_amount / 100,
                payment_method=payment_method,
                coupon=coupon,
                coupon_name=selected_coupon_code,
                coupon_percentage=coupon_percentage,
                payment_status='Failure'
            )

            OrderAddress.objects.create(
                order=order,
                fullname=selected_address.fullname,
                mobile=selected_address.mobile,
                pincode=selected_address.pincode,
                address=selected_address.address,
                district=selected_address.district,
                city=selected_address.city,
                state=selected_address.state
            )

            # Save order details
            for item in cart_items:
                offer_percentage = item.product.art_category.art_type_offer or 0
                Order_details.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    variant=item.variant,
                    offer=offer_percentage
                )

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))

            razorpay_order = client.order.create({
                'amount': final_amount,
                'currency': 'INR',
                'payment_capture': '1'
            })

            return render(request, 'user/payment.html', {
                'order_id': razorpay_order['id'],
                'amount': final_amount / 100,
                'razorpay_key': settings.RAZORPAY_KEY_ID,
                'user': request.user,
                'original_order_id': order.id
            })

        elif payment_method == 'Wallets':
            order = Order.objects.create(
                user=request.user,
                total_amount=final_amount / 100,
                payment_method=payment_method,
                coupon=coupon,
                coupon_name=selected_coupon_code,
                coupon_percentage=coupon_percentage,
                payment_status='Success'
            )

            OrderAddress.objects.create(
                order=order,
                fullname=selected_address.fullname,
                mobile=selected_address.mobile,
                pincode=selected_address.pincode,
                address=selected_address.address,
                district=selected_address.district,
                city=selected_address.city,
                state=selected_address.state
            )

            for item in cart_items:
                offer_percentage = item.product.art_category.art_type_offer or 0
                Order_details.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    variant=item.variant,
                    offer=offer_percentage
                )

                item.variant.stock -= item.quantity
                item.variant.save()

            wallet, created = Wallet.objects.get_or_create(user=request.user)
            wallet.wallet_amount -= order.total_amount  # Increment the wallet amount
            wallet.save()

            trasanction = Wallet_Transaction.objects.create(
                user=request.user,
                transaction_amount=order.total_amount,
                type='Debit',
                transaction_mode=order.payment_method
            )

            cart_items.delete()
            return redirect('order_placed')


# ======================== PAYMENT SECTION ====================== #

def payment_success(request):
    cart_items = Cart.objects.filter(user=request.user)
    for item in cart_items:
        item.variant.stock -= item.quantity
        item.variant.save()

    cart_items.delete()
    original_order_id = request.GET.get('order_id')
    order = get_object_or_404(Order, id=original_order_id)
    order.payment_status = 'Success'
    order.save()
    return redirect('order_placed')


def retry_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    payment_amount = order.total_amount
    payment_amount_float = float(payment_amount)
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))
    razorpay_order = client.order.create({
        'amount': int(payment_amount_float * 100),
        'currency': 'INR',
        'payment_capture': '1'
    })

    return render(request, 'user/retry_payment.html', {
        'order_id': razorpay_order['id'],
        'amount': payment_amount_float,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'user': request.user,
        'original_order_id': order.id
    })


def retry_payment_success(request):
    cart_items = Cart.objects.filter(user=request.user)

    for item in cart_items:
        item.variant.stock -= item.quantity
        item.variant.save()

    cart_items.delete()

    original_order_id = request.GET.get('order_id')
    order = get_object_or_404(Order, id=original_order_id)
    order.payment_status = 'Success'
    order.save()
    return redirect('orders')


# ==================== ORDERS SECTION ================== #

def orders(request):
    if not request.user.is_authenticated:
        messages.info(request, "PLEASE LOGIN.")
        return redirect('login')

    orders = Order.objects.filter(user=request.user).order_by('-id')
    no_user_orders_found = not orders.exists()

    if request.GET.get('cancelled') == 'true':
        messages.warning(request, "Your order placed, But payment not completed !")

    paginator = Paginator(orders, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'no_user_orders_found': no_user_orders_found
    }

    return render(request, 'user/orders.html', context)


@login_required
def order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.user != request.user:
        messages.error(request, "You are not authorized to view this order.")
        return redirect('login')

    if not request.user.is_authenticated:
        messages.info(request, "PLEASE LOGIN.")
        return redirect('login')

    orders = get_object_or_404(Order, id=order_id)
    return_button = None
    hide = None
    order_address = get_object_or_404(OrderAddress, order=order_id)
    order_items = Order_details.objects.filter(order=orders)
    if orders.coupon:
        coupon_code = orders.coupon.coupon_code

    for item in order_items:
        return_request = Return.objects.filter(order_item=item, status='accepted').exists()

    if orders.status in ['Delivered', 'Returned']:
        return_button = 'Deliver_Return'

    order_items = Order_details.objects.filter(order=orders).order_by('-id')
    items_with_price = []
    normal_total_price = 0
    item_offer = None

    for item in order_items:
        if item.offer:
            item_offer = item.variant.price * (Decimal(1) - (Decimal(item.offer) / Decimal(100)))
        original_price = item.variant.price * item.quantity
        discount_price = original_price

        if item.product.art_category.art_type_offer:
            discount_price -= (original_price * item.product.art_category.art_type_offer / 100)

        items_with_price.append({
            'item': item,
            'original_price': original_price,
            'discount_price': discount_price,
        })

        normal_total_price += original_price
    if order.payment_status == 'Failure':
        messages.error(request, "Please complete your payment")

    context = {
        'order_items': order_items,
        'return_button': return_button,
        'orders': orders,
        'order_address': order_address,
        'normal_total_price': normal_total_price,
        'item_offer': item_offer,
        'return_request': return_request,
        'items_with_price': items_with_price
        # 'hide': hide
    }
    return render(request, 'user/order_details.html', context)


# ============================= RETURN SECTION ========================= #

def item_return(request, order_id, item_id):
    if request.method == 'POST':
        reason = request.POST.get('reason')
        request_value = request.POST.get('request')
        item = get_object_or_404(Order_details, id=item_id)

        existing_return = Return.objects.filter(order_item=item, status='request').exists()
        if existing_return:
            messages.warning(request, 'You have already submitted a return request for this item.')
            return redirect('order_details', order_id=order_id)  #

        if reason == 'damaged':
            text = 'Damaged Product'
        elif reason == 'wrong_item':
            text = 'Wrong Item Sent'
        elif reason == 'not_satisfied':
            text = 'Not Satisfied with Product'
        else:
            text = 'Other'

        Return.objects.create(
            reason=text,
            status=request_value,
            order_item=item
        )

        messages.success(request, 'Your return request has been successfully sent')

        return redirect('order_details', order_id)


def order_placed(request):
    return render(request, 'user/order_placed.html')


# ======================== RATINGS AND REVIEWS ===================== #

def submit_review(request, product_id, order_id, variant_id):
    if request.method == 'POST':
        rating = request.POST.get('rating')
        review_text = request.POST.get('reviewtext')
        product = get_object_or_404(Product, id=product_id)
        variant = get_object_or_404(Variant, id=variant_id)
        Review.objects.create(
            review=review_text,
            rating=rating,
            product=product,
            variant=variant,
            user=request.user
        )
        messages.success(request, 'Thank you for your review!')
        return redirect('order_details', order_id)


# ==================== WISHLIST SECTION ================ #

def add_wishlist(request, product_id, variant_id):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to add items to your wishlist.")
        return redirect('login')

    product = get_object_or_404(Product, id=product_id)
    variant = get_object_or_404(Variant, id=variant_id)

    if not product.product_status:
        messages.warning(request, "This product is currently unavailable.")
        return redirect('shop')

    if not product.art_category.art_type_status:
        messages.warning(request, "This category of product is currently unavailable.")
        return redirect('shop')

    wishlist_item_exists = Wishlist.objects.filter(user=request.user, variant=variant).exists()
    if wishlist_item_exists:
        messages.warning(request, "This item is already in your wishlist.")
        return redirect('shop')

    Wishlist.objects.create(product=product, user=request.user, variant=variant)
    return redirect('wishlist')


def wishlist(request):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to view your wishlist.")
        return redirect('login')

    wishlist_items = Wishlist.objects.filter(user=request.user)
    is_empty = not wishlist_items.exists()
    wishlist_items_with_offer_price = []
    for item in wishlist_items:
        product = item.product
        art_category = product.art_category

        if art_category.art_type_offer:
            offer_price = item.variant.price - (item.variant.price * art_category.art_type_offer / 100)
        else:
            offer_price = item.variant.price

        wishlist_items_with_offer_price.append({
            'item': item,
            'offer_price': offer_price
        })
    paginator = Paginator(wishlist_items_with_offer_price, 3)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'user/wishlist.html', {
        'page_obj': page_obj,
        'is_empty': is_empty
    })


def remove_wishlist_item(request, variant_id):
    wishlist_items = Wishlist.objects.get(variant=variant_id, user=request.user)
    wishlist_items.delete()
    return redirect('wishlist')


def add_cart_wishlist(request, product_id, variant_id):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to add items to your cart.")
        return redirect('login')

    # Get the product and variant
    product = get_object_or_404(Product, id=product_id)
    variant = get_object_or_404(Variant, id=variant_id)

    if not product.product_status:
        messages.warning(request, "This product is currently unavailable.")
        return redirect('wishlist')

    if not product.art_category.art_type_status:
        messages.warning(request, "This category of product is currently unavailable.")
        return redirect('wishlist')

    cart_item_exists = Cart.objects.filter(variant=variant, user=request.user).exists()
    if cart_item_exists:
        messages.warning(request, "This item is already in your cart.")
        return redirect('wishlist')

    # Add item to the cart
    Cart.objects.create(product=product, user=request.user, variant=variant)
    messages.success(request, "Item added to Cart.")

    # Delete the item from the wishlist
    try:
        wishlist_item = Wishlist.objects.get(variant=variant, user=request.user)
        wishlist_item.delete()
    except Wishlist.DoesNotExist:
        messages.warning(request, "The item was not found in your wishlist.")

    return redirect('wishlist')


# =========================== ORDER CANCEL SECTION ======================= #

def order_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.status == 'Cancelled':
        messages.warning(request, "Order is already cancelled.")
        return redirect('order_details', order_id=order_id)

    order.status = 'Cancelled'

    order_details = Order_details.objects.filter(order=order)

    for detail in order_details:
        variant = detail.variant
        variant.stock += detail.quantity
        variant.save()
        detail.item_status = 'Cancelled'
        detail.save()
    order.save()

    if order.payment_method in ['Razorpay', 'Wallets']:
        wallet, created = Wallet.objects.get_or_create(user=request.user, defaults={'wallet_amount': 0})
        wallet.wallet_amount += order.total_amount
        wallet.save()

        trasanction = Wallet_Transaction.objects.create(
            user=request.user,
            transaction_amount=order.total_amount,
            type='Credit',
            transaction_mode='Order cancel'
        )

    order.save()
    return redirect('order_details', order_id=order_id)


def item_cancel(request, order_id, item_id):
    order = get_object_or_404(Order, id=order_id)
    item = get_object_or_404(Order_details, id=item_id)
    item.item_status = 'Cancelled'

    if order.payment_method in ['Razorpay', 'Wallets']:

        item_amount = item.variant.price
        amount_to_refund = item.variant.price * item.quantity
        art_offer = item.offer

        if art_offer:
            discount_from_offer = (Decimal(art_offer) / Decimal(100)) * amount_to_refund
            amount_to_refund -= discount_from_offer

        coupon_used = item.order.coupon
        if coupon_used:
            discount_from_coupon = (coupon_used.percentage / 100) * amount_to_refund
            amount_to_refund -= discount_from_coupon

        requested_user = item.order.user.username
        wallet, created = Wallet.objects.get_or_create(user=item.order.user)
        wallet.wallet_amount += amount_to_refund
        wallet.save()

        order.total_amount -= amount_to_refund
        order.save()

        trasanction = Wallet_Transaction.objects.create(
            user=item.order.user,
            transaction_amount=amount_to_refund,
            type='Credit',
            transaction_mode='Item cancel'
        )

        variant = item.variant
        variant.stock += item.quantity
        variant.save()

    elif order.payment_method == 'COD':
        variant = item.variant
        variant.stock += item.quantity
        variant.save()

    item.save()

    all_items_cancelled = not Order_details.objects.filter(
        order=order,
    ).exclude(item_status='Cancelled').exists()

    if all_items_cancelled:
        order.status = 'Cancelled'
        order.save()

    return redirect('order_details', order_id=order_id)


# ==================== DOWNLOAD INVOICE SECTION ================= #

def download_invoice(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        order_items = Order_details.objects.filter(order=order)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order_id}.pdf"'
        pdf = SimpleDocTemplate(
            response,
            pagesize=A4,
            title="Order invoice",
            encoding='UTF-8'
        )

        elements = []

        styles = getSampleStyleSheet()
        header_style = ParagraphStyle(
            name='CenteredHeader',
            fontSize=20,
            alignment=1,
            spaceAfter=12
        )

        header = Paragraph("ARTKART ORDER INVOICE", header_style)
        elements.append(header)

        elements.append(Paragraph("<br/>", styles['Normal']))

        table_data = [
            ["Product Name", "Quantity", "Normal Price", "Offer Price"],  # Table header
        ]

        normal_total_price = 0
        offer_total_price = 0
        final_payable_price = 0

        for item in order_items:
            product_name = item.product.product_name
            quantity = item.quantity
            normal_price = item.variant.price * quantity
            offer_price = normal_price

            art_offer_percentage = item.product.art_category.art_type_offer if item.product.art_category and item.product.art_category.art_type_offer else 0

            if art_offer_percentage:
                offer_price = normal_price - (normal_price * art_offer_percentage / 100)

            normal_total_price += normal_price
            offer_total_price += offer_price

            table_data.append([product_name, quantity, f"{normal_price:.2f}", f"{offer_price:.2f}"])

        if order.coupon_name:
            coupon_discount = (Decimal(offer_total_price) * Decimal(order.coupon_percentage)) / 100

            final_payable_price = offer_total_price - coupon_discount
        else:
            final_payable_price = offer_total_price

        column_widths = [150, 100, 100, 100]

        table = Table(table_data, colWidths=column_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWHEIGHT', (0, 0), (-1, -1), 40),
        ]))

        elements.append(table)

        elements.append(Paragraph(f"<br/>Normal Total Amount: rs {normal_total_price:.2f}", styles['Normal']))
        elements.append(Paragraph(f"Offer Total Amount: rs {offer_total_price:.2f}", styles['Normal']))

        if order.coupon_name:
            coupon_code = order.coupon_name
            elements.append(Paragraph(f"<br/>Coupon Used: {coupon_code}", styles['Normal']))
            elements.append(Paragraph(f"Coupon Percentage: {order.coupon_percentage}%", styles['Normal']))
        else:
            elements.append(Paragraph("<br/>Coupon Used: No coupon used", styles['Normal']))

        elements.append(Paragraph(f"<br/>Final Payable Amount: rs{final_payable_price:.2f}", styles['Normal']))

        order_address = get_object_or_404(OrderAddress, order=order_id)
        custom_style = ParagraphStyle(
            'CustomStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor='black',
            spaceAfter=12,
            alignment=1,
        )
        elements.append(Paragraph("<br/>BILLING ADDRESS", custom_style))
        elements.append(Paragraph(f"Name: {order_address.fullname}", styles['Normal']))
        elements.append(Paragraph(f"Address: {order_address.address}", styles['Normal']))
        elements.append(Paragraph(f"Phone Number: {order_address.mobile}", styles['Normal']))
        elements.append(Paragraph(f"City: {order_address.city}", styles['Normal']))
        elements.append(Paragraph(f"District: {order_address.district}", styles['Normal']))
        elements.append(Paragraph(f"Pincode: {order_address.pincode}", styles['Normal']))
        elements.append(Paragraph(f"State: {order_address.state}", styles['Normal']))

        pdf.build(elements)
        return response

    except Order.DoesNotExist:
        return HttpResponse("Order not found.", status=404)