from django.db import models
from django.contrib.auth.models import User
from product_app.models import Product
from variant_app.models import Variant
from coupon_app.models import Coupons


class Address(models.Model):
    fullname = models.CharField(max_length=50)
    mobile = models.CharField(max_length=15) 
    pincode = models.CharField(max_length=10) 
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=50)
    district = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.fullname}, {self.city}, {self.district}, {self.district}"




class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)



class Order(models.Model):
    STATUS_CHOICES = [
    ('Pending', 'Pending'),
    ('Returned', 'Returned'),
    ('Shipped', 'Shipped'),
    ('Delivered', 'Delivered'),
    ('Cancelled', 'Cancelled'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Success', 'Success'),
        ('Failure', 'Failure')
    ]
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=60)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    order_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    deliver_date = models.DateTimeField(null=True, blank= True)
    coupon = models.ForeignKey(Coupons, null=True, blank=True, on_delete=models.SET_NULL, related_name='orders')
    
    coupon_name = models.CharField(max_length=100, null=True, blank=True)
    coupon_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    

class Order_details(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    variant = models.ForeignKey(Variant, on_delete= models.CASCADE)
    offer = models.PositiveIntegerField(null=True, blank=True)
    item_coupon_amount = models.PositiveIntegerField(null=True, blank=True)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('return', 'Return'),
        ('cancelled', 'Cancelled'),
    ]
    
    item_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')


class OrderAddress(models.Model):
    fullname = models.CharField(max_length=50)
    mobile = models.CharField(max_length=15) 
    pincode = models.CharField(max_length=10) 
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=50)
    district = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='orders')


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)



class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_items')
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name='wishlist_items')


class Wallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallet')
    wallet_amount = models.IntegerField(default=0)


class Wallet_Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_amount = models.IntegerField()
    created_date = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=50)
    transaction_mode = models.CharField(max_length=50)


class Return(models.Model):
    order_item = models.ForeignKey(Order_details, on_delete=models.CASCADE, related_name='returns')
    status = models.CharField(max_length=100, default='pending')
    reason = models.CharField(max_length=200, default='Other')
    

class UserInformations(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15)
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ]
    gender = models.CharField(max_length=30, choices=GENDER_CHOICES)
   
    def __str__(self):
        return f"{self.first_name} {self.last_name}"

   