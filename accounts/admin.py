from django.contrib import admin
from .models import Account,Courier,AdminBankDetails,Transaction,DeliveryFee
from django.utils.html import format_html
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
import logging
from django.templatetags.static import static
import base64
from django.core.files import File
from io import BytesIO
from PIL import Image
import os
from django.contrib.staticfiles.storage import staticfiles_storage
import json
from django.db.models import Count
from django.contrib.auth import get_user_model
from django.core.mail import send_mail



User = get_user_model()  # Get the custom user model





class AccountAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'username')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    ordering = ('-date_joined',)


class CourierAdmin(admin.ModelAdmin):
    list_display = (
        'tracking_number', 
        'user', 
        'receiver_name', 
        'sender_name', 
        'destination', 
        'date_sent', 
        'estimated_delivery_date', 
        'status'
    )
    list_filter = ('status', 'destination', 'date_sent', 'estimated_delivery_date')
    search_fields = ('tracking_number', 'receiver_name', 'sender_name', 'receiver_contact_number', 'sender_contact_number', 'user__username')
    
    readonly_fields = ('tracking_number',)

    fieldsets = (
        ('User Information', {
            'fields': ('user',),
        }),
        ('Receiver Information', {
            'fields': ('receiver_name', 'receiver_contact_number', 'receiver_email', 'receiver_address')
        }),
        ('Sender Information', {
            'fields': ('sender_name', 'sender_contact_number', 'sender_email', 'sender_address')
        }),
        ('Parcel Information', {
            'fields': ('item_description', 'number_of_items', 'parcel_colour', 'destination')
        }),
        ('Consignment Details', {
            'fields': ('date_sent', 'estimated_delivery_date', 'status', 'tracking_number')
        }),
    )

    actions = ['mark_as_in_transit', 'mark_as_delivered', 'mark_as_failed_delivery']

    def save_model(self, request, obj, form, change):
        if change:  
            try:
                previous_status = Courier.objects.get(pk=obj.pk).status
            except Courier.DoesNotExist:
                previous_status = None

            print(f"Previous Status: {previous_status}, Current Status: {obj.status}")

            self.send_status_update_email(obj)

        super().save_model(request, obj, form, change)

    def send_status_update_email(self, courier):
        """Sends a status update email to the user when the courier status changes."""
        email_subject = "Glotürk Logistics Kargo - Package Status Update"

        if courier.status == "In Transit":
            status_message = """
                We are pleased to inform you that the payment for your package has been confirmed. Your package is now scheduled for pickup, and our agents will contact you shortly via phone or email to coordinate the pickup process.
                Thank you for choosing Glotürk Logistics. We are committed to providing you with reliable service.
            """
        elif courier.status == "Delivered":
            status_message = "Your package has been successfully delivered. Thank you for using Glotürk Logistics."
        elif courier.status == "Failed Delivery":
            status_message = "Unfortunately, we were unable to deliver your package. Please contact our support team for assistance."

        html_message = format_html(
            """
            <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #f9f9f9;">
                <h1 style="color: #000;">Glotürk Logistics Kargo</h1>
                <p style="font-size: 16px; color: #333;">Dear <strong>{}</strong>,</p>
                <p style="font-size: 16px; color: #333;">
                    Your package with tracking number <strong>{}</strong> has been updated to <strong style="color: #007bff;">{}</strong>.
                </p>
                <p style="font-size: 16px; color: #333;">{}</p>
                <h2 style="color: #28a745;">Package Details</h2>
                <table style="margin: 0 auto; border-collapse: collapse; font-size: 14px; width: 80%;">
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd; background-color: #f1f1f1;"><strong>Receiver Name:</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd; background-color: #f1f1f1;"><strong>Destination:</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd; background-color: #f1f1f1;"><strong>Current Status:</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd; color: #007bff;"><strong>{}</strong></td>
                    </tr>
                </table>
                <p style="font-size: 14px; color: #666; margin-top: 20px;">
                    If you have any questions, feel free to contact us at <a href="mailto:info@gloturklogistics.com">info@gloturklogistics.com</a>.
                </p>
                <p style="font-size: 14px; color: #666;">Best regards,<br>Glotürk Logistics Kargo Team</p>
            </div>
            """,
            courier.user.username,
            courier.tracking_number,
            courier.status,
            status_message,
            courier.receiver_name,
            courier.destination,
            courier.status
        )

        send_mail(
            email_subject,
            "",  
            settings.EMAIL_HOST_USER,
            [courier.user.email],
            fail_silently=False,
            html_message=html_message
        )

    def mark_as_in_transit(self, request, queryset):
        queryset.update(status='In Transit')
        for courier in queryset:
            transactions = Transaction.objects.filter(courier=courier, status='Pending')
            updated_count = transactions.update(status='Completed')
            self.send_status_update_email(courier)
            if updated_count > 0:
                self.message_user(request, f"{updated_count} transaction(s) for {courier.tracking_number} marked as Completed.", level='info')
            else:
                self.message_user(request, f"No pending transactions found for {courier.tracking_number}.", level='warning')

        self.message_user(request, "Selected couriers have been marked as 'In Transit'.")
    mark_as_in_transit.short_description = "Mark selected as In Transit"

    def mark_as_delivered(self, request, queryset):
        queryset.update(status='Delivered')
        for courier in queryset:
            self.send_status_update_email(courier)
        self.message_user(request, "Selected couriers have been marked as 'Delivered'.")
    mark_as_delivered.short_description = "Mark selected as Delivered"

    def mark_as_failed_delivery(self, request, queryset):
        queryset.update(status='Failed Delivery')
        for courier in queryset:
            self.send_status_update_email(courier)
        self.message_user(request, "Selected couriers have been marked as 'Failed Delivery'.")
    mark_as_failed_delivery.short_description = "Mark selected as Failed Delivery"



# Admin for AdminBankDetails
@admin.register(AdminBankDetails)
class AdminBankDetailsAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_name', 'account_number', 'swift_code', 'created_at')
    search_fields = ('bank_name', 'account_name', 'account_number')
    ordering = ['-created_at']





@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'courier', 'amount', 'status', 'date')
    search_fields = ('transaction_id', 'user__username', 'courier__tracking_number', 'status')
    list_filter = ('status', 'date')
    ordering = ('-date',)
    autocomplete_fields = ('user', 'courier')

@admin.register(DeliveryFee)
class DeliveryFeeAdmin(admin.ModelAdmin):
    list_display = (
        'destination_category', 
        'weight_min', 
        'weight_max', 
        'base_price', 
        'price_per_kg', 
        'created_at'
    )
    list_filter = ('destination_category', 'created_at')
    search_fields = ('destination_category',)
    ordering = ('-created_at',)



admin.site.register(Courier, CourierAdmin)
admin.site.register(Account, AccountAdmin)