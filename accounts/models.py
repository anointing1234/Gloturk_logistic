import random
import string
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import datetime, timedelta
from PIL import Image
import os
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.html import format_html
from decimal import Decimal
from django.contrib.auth import get_user_model
import uuid
from django.conf import settings
import json
import uuid
from django.contrib.auth.models import User 
import locale


class AccountManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("User must have an email address")
        
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email.split('@')[0])  # Default username from email if not provided
        first_name = extra_fields.pop('first_name', '')
        last_name = extra_fields.pop('last_name', '')
        phone_number = extra_fields.pop('phone_number', '')

        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email=email, password=password, **extra_fields)




class Account(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(verbose_name="Email", max_length=100, unique=True)
    username = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    date_joined = models.DateTimeField(verbose_name="Date Joined", auto_now_add=True)
    last_login = models.DateTimeField(verbose_name="Last Login", auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = AccountManager()

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True

class Courier(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='couriers', null=True, blank=True)  # User association

    # Receiver's Details
    receiver_name = models.CharField(max_length=255)
    receiver_contact_number = models.CharField(max_length=15)
    receiver_email = models.EmailField()
    receiver_address = models.TextField()

    # Sender's Details
    sender_name = models.CharField(max_length=255)
    sender_contact_number = models.CharField(max_length=15)
    sender_email = models.EmailField()
    sender_address = models.TextField()

    # Item(s) Description
    item_description = models.TextField()
    number_of_items = models.PositiveIntegerField(default=1)
    parcel_colour = models.CharField(max_length=50)
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Enter the package weight in kilograms")
    category = models.CharField(max_length=50, choices=[('Domestic', 'Domestic'), ('International', 'International')], default='Domestic', help_text="Select the delivery category")

    # Parcel & Consignment Transits
    destination = models.CharField(max_length=255)
    date_sent = models.DateField()
    estimated_delivery_date = models.DateField()

    # Parcel & Consignment Movement Information and Status
    status = models.CharField(
        max_length=50,
        choices=[
            ('In Transit', 'In Transit'),
            ('Delivered', 'Delivered'),
            ('Pending', 'Pending'),
            ('Returned', 'Returned'),
            ('Failed Delivery', 'Failed Delivery'),
        ],
        default='Pending'
    )
    current_location = models.CharField(
        max_length=100,
        default="Processing Center",  # Default location
        null=True,
        blank=True,
        help_text="Enter the current country or city of the package"
)

    tracking_number = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"Tracking No: {self.tracking_number} - Status: {self.status}"


class Transaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    courier = models.ForeignKey(Courier, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=50,
        choices=[
            ('Pending', 'Pending'),
            ('Completed', 'Completed'),
            ('Failed', 'Failed'),
            ('Refunded', 'Refunded')
        ],
        default='Pending'
    )
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction {self.transaction_id} - Status: {self.status}"


class AdminBankDetails(models.Model):
    bank_name = models.CharField(max_length=100)
    account_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    swift_code = models.CharField(max_length=50, blank=True, null=True)  # For international transfers
    branch_address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_name}"



class PasswordResetCode(models.Model):
    email = models.EmailField(unique=True)
    reset_code = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email   



class DeliveryFee(models.Model):
    DESTINATION_CHOICES = [
        ('Domestic', 'Domestic'),
        ('International', 'International'),
    ]
    destination_category = models.CharField(
        max_length=100,
        choices=DESTINATION_CHOICES,
        help_text="Select the destination category (e.g., Domestic or International)"
    )
    weight_min = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Minimum weight (kg) for this rate"
    )
    weight_max = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Maximum weight (kg) for this rate"
    )
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Base fee for shipments in this weight range"
    )
    price_per_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Additional fee per kilogram above the minimum weight"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_fee(self, weight):
        """
        Calculate the delivery fee for a given weight.
        If the weight is below the minimum, returns the base price.
        Otherwise, it returns the base price plus the additional charge 
        for the weight above the minimum.
        """
        if weight < self.weight_min:
            return self.base_price
        additional_weight = weight - self.weight_min
        return self.base_price + (additional_weight * self.price_per_kg)

    def is_applicable(self, weight):
        """
        Returns True if the given weight falls within the range of this fee rule.
        """
        return self.weight_min <= weight <= self.weight_max

    def __str__(self):
        return f"{self.destination_category}: {self.weight_min}kg - {self.weight_max}kg"
