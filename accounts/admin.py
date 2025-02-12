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
from django import forms
from django.urls import path
from django.shortcuts import render, redirect




User = get_user_model()  # Get the custom user model



class AccountCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = Account
        fields = ('email', 'first_name', 'last_name', 'phone_number')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        # Automatically create a username from the email
        user.username = self.cleaned_data['email'].split('@')[0]  # Use the part before the '@' as the username
        if commit:
            user.save()
        return user


class AccountAdmin(admin.ModelAdmin):
    form = AccountCreationForm  # Use the custom form
    list_display = ('email', 'username', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'username')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    ordering = ('-date_joined',)


class UpdateLocationForm(forms.Form):
    current_location = forms.CharField(max_length=255, required=True, label="Current Location")


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

    actions = ['mark_as_in_transit', 'mark_as_delivered', 'mark_as_failed_delivery','update_location_action']

    def save_model(self, request, obj, form, change):
        if change:  
            try:
                previous_status = Courier.objects.get(pk=obj.pk).status
            except Courier.DoesNotExist:
                previous_status = None

            print(f"Previous Status: {previous_status}, Current Status: {obj.status}")

            self.send_status_update_email(obj)

        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('update-location/', self.admin_site.admin_view(self.update_location_view), name='update-location'),
        ]
        return custom_urls + urls

    def update_location_action(self, request, queryset):
        selected = ','.join(str(obj.pk) for obj in queryset)
        return redirect(f"{request.path}update-location/?ids={selected}")

    update_location_action.short_description = "Update Current Location and Notify User"

    def update_location_view(self, request):
        ids = request.GET.get('ids', '').split(',')
        couriers = Courier.objects.filter(pk__in=ids)

        if request.method == 'POST':
            form = UpdateLocationForm(request.POST)
            if form.is_valid():
                current_location = form.cleaned_data['current_location']
                for courier in couriers:
                    # Update current location (add this to your model if needed)
                    # courier.current_location = current_location
                    courier.save()
                    self.send_location_update_email(courier, current_location)
                self.message_user(request, f"Location updated for {couriers.count()} courier(s) and notifications sent.")
                return redirect('..')
        else:
            form = UpdateLocationForm()

        context = {
            'form': form,
            'couriers': couriers,
            'title': "Update Current Location",
        }
        return render(request, 'admin/update_location.html', context)

    def send_location_update_email(self, courier, current_location):
        """Sends an email to notify the user of the updated current location."""
        email_subject = "Glotürk Logistics Kargo - Package Location Update"
        html_message = format_html(
            """
            <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #f9f9f9;">
                <h1 style="color: #000;">Glotürk Logistics Kargo</h1>
                <p style="font-size: 16px; color: #333;">Dear <strong>{}</strong>,</p>
                <p style="font-size: 16px; color: #333;">
                    Your package with tracking number <strong>{}</strong> is currently  at <strong style="color: #007bff;">{}</strong>.
                </p>
                <p style="font-size: 14px; color: #666;">If you have any questions, feel free to contact us at <a href="mailto:https://gloturklogistics.com/">https://gloturklogistics.com/</a>.</p>
                <p style="font-size: 14px; color: #666;">Best regards,<br>Glotürk Logistics Kargo Team</p>
            </div>
            """,
            courier.user.username,
            courier.tracking_number,
            current_location
        )

        send_mail(
            email_subject,
            "",
            settings.EMAIL_HOST_USER,
            [courier.user.email],
            fail_silently=False,
            html_message=html_message
        )

    def send_status_update_email(self, courier):
        """Sends a status update email to the user when the courier status changes."""
        email_subject = "Glotürk Logistics Kargo - Package Status Update"

        if courier.status == "In Transit":
            status_message = """
        We are pleased to inform you that your package is currently in transit. Our team is working diligently to ensure timely delivery.
        You can track your package’s progress using your tracking number. Should you have any questions, feel free to reach out to our support team.
        
        Thank you for choosing Glotürk Logistics. We appreciate your trust in our services.
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
                    If you have any questions, feel free to contact us at <a href="mailto:https://gloturklogistics.com/">https://gloturklogistics.com/</a>.
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