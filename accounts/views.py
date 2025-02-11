from django.shortcuts import render
import requests
import logging
import json
import os
import time
from django.conf import settings
from django.conf.urls.static import static
from django.core.mail import EmailMultiAlternatives
import pytz
from datetime import datetime, timedelta
from pytz import timezone as pytz_timezone
from urllib.parse import urljoin
from requests.exceptions import RequestException
from django.contrib.auth import logout
from django.contrib.auth import get_user_model
from bs4 import BeautifulSoup
import random
from decimal import Decimal
from .models import AdminBankDetails,Courier,Transaction,PasswordResetCode,DeliveryFee
from accounts.forms import RegisterForm,LoginForm,CourierForm,SendresetcodeForm,PasswordResetForm
from django.contrib.auth import logout as auth_logout,login as auth_login,authenticate
# from accounts.models import
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib import messages
from django.shortcuts import redirect
import uuid
from django.utils.timezone import now 
from django.contrib.auth.decorators import login_required
import logging
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.core.mail import EmailMessage
from django.utils.html import format_html
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.http import FileResponse
import io
from reportlab.graphics.barcode import code128 

logger = logging.getLogger(__name__)


def register(request):
    if request.method == 'POST':
        register_form = RegisterForm(request.POST)

        if register_form.is_valid():
            user = register_form.save(commit=False)
            
            # Generate a unique username (e.g., first 5 characters of the email + random 4-digit number)
            base_username = user.email.split('@')[0][:5]
            unique_username = f"{base_username}{str(uuid.uuid4().int)[:4]}"
            user.username = unique_username
            
            user.save()  # Save the user with the generated username
            
            return JsonResponse({'success': True, 'message': 'Registration successful!', 'redirect_url': '/login_view'})
        else:
            # Collect all form errors
            error_messages = []
            if register_form.errors:
                for field, errors in register_form.errors.items():
                    for error in errors:
                        error_messages.append(f"{field.capitalize()}: {error}")
            error_message = "\n".join(error_messages)

            return JsonResponse({'success': False, 'message': error_message})

    return JsonResponse({'success': False, 'message': 'Invalid request.'})




def login_Account(request):
    if request.method == 'POST':
        login_form = LoginForm(request.POST)
        if login_form.is_valid():
            user = login_form.get_user()
            auth_login(request, user)
            return JsonResponse({
                'success': True,
                'message': 'Login successful!',
                'redirect_url': '/'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid email  or password.'
            })
    else:
        form = LoginForm()
    return render(request,'forms/login.html',{'form':form})



def logout_view(request):
    auth_logout(request)
    form = LoginForm()
    return render(
    request,'forms/login.html',{'form':form})





def courier_form(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':  # Check for AJAX request
        form = CourierForm(request.POST)
        if form.is_valid():
            # Calculate delivery price using weight and category from the form
            weight = form.cleaned_data['weight']
            category = form.cleaned_data['category']
            delivery_price = calculate_delivery_price(Decimal(weight), category)
            delivery_price = float(delivery_price) 
            # Retrieve bank details
            bank_details = AdminBankDetails.objects.first()  # Example: Get the first entry in BankDetails table
            if bank_details:
                response_data = {
                    'delivery_price': delivery_price,
                    'bank_details': {
                        'bank_name': bank_details.bank_name,
                        'account_name': bank_details.account_name,
                        'account_number': bank_details.account_number,
                        'swift_code': bank_details.swift_code,
                        'branch_address': bank_details.branch_address,
                    }
                }
                print(bank_details.bank_name, bank_details.account_name, bank_details.account_number, bank_details.swift_code, bank_details.branch_address,delivery_price)
                return JsonResponse(response_data)
            else:
                return JsonResponse({'error': 'Bank details not found'}, status=500)
        else:
            return JsonResponse({'error': 'Invalid form data'}, status=400)

    # For non-AJAX GET requests, render the template
    form = CourierForm()
    return render(request, 'parkage_delivery.html', {'form': form})




def calculate_delivery_price(weight, category):
    """
    Calculate delivery fee based on the package's weight and the selected delivery category.
    If a matching fee rule is found in the DeliveryFee model, use it to calculate the fee.
    Otherwise, return 0.00 or a default fee.
    """
    try:
        fee_rule = DeliveryFee.objects.get(
            destination_category__iexact=category,
            weight_min__lte=weight,
            weight_max__gte=weight
        )
    except DeliveryFee.DoesNotExist:
        return 0.00  # Or set a default fee
    return fee_rule.calculate_fee(weight)


def generate_receipt(courier, user):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setTitle("Air Waybill Receipt")

    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(300, 800, "AIR WAYBILL RECEIPT")

    p.setFont("Helvetica", 10)
    p.drawString(50, 780, "Glotürk Logistics Kargo")
    p.drawString(50, 765, "Website: www.gloturklogistics.com")
    p.drawString(400, 780, f"Tracking #: {courier.tracking_number}")
    p.drawString(400, 765, f"Bill Date: {courier.date_sent.strftime('%d-%b-%Y')}")

    # Generate Barcode for Tracking Number
    barcode = code128.Code128(courier.tracking_number, barHeight=20, barWidth=0.8)
    barcode.drawOn(p, 400, 740)  # Adjust the position of the barcode (x=400, y=740)

    # Table for Ship From and Ship To
    data = [
        ['SHIP FROM', 'SHIP TO'],
        [
            f'Consignor: {courier.sender_name}\nAddress: {courier.sender_address}\nEmail: {courier.sender_email}', 
            f'Consignee: {courier.receiver_name}\nAddress: {courier.receiver_address}\nEmail: {courier.receiver_email}\nPhone: {courier.receiver_contact_number}'
        ]
    ]

    table = Table(data, colWidths=[250, 250])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    table.wrapOn(p, 50, 620)
    table.drawOn(p, 50, 670)

    # Package and Delivery Details
    package_data = [
        ['PACKAGE DETAILS', ''],
        ['Weight', f'{courier.weight} kg'],
        ['Category', courier.category],
        ['Delivery Status', courier.status],
        ['Item discription',courier.item_description]
    ]

    package_table = Table(package_data, colWidths=[150, 350])
    package_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    package_table.wrapOn(p, 50, 500)
    package_table.drawOn(p, 50, 550)

    # Footer Section with Disclaimer and Signatures
    p.setFont("Helvetica-Oblique", 8)
    p.drawString(50, 100, "If you have any questions, contact us at info@gloturklogistics.com.")
    p.drawString(50, 85, "Note: This document serves as a receipt for your shipment.")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer



def insert_courier(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        form = CourierForm(request.POST)
        delivery_price = request.POST.get('delivery_price')

        if form.is_valid() and delivery_price:
            try:
                delivery_price = float(delivery_price)
            except ValueError:
                return JsonResponse({'error': 'Invalid delivery price'}, status=400)

            courier = form.save(commit=False)
            courier.user = request.user
            courier.tracking_number = str(uuid.uuid4()).replace('-', '').upper()[:10]
            courier.status = 'Pending'
            courier.save()

            Transaction.objects.create(
                user=request.user,
                courier=courier,
                transaction_id=str(uuid.uuid4()).replace('-', '').upper()[:12],
                amount=delivery_price,
                status='Pending',
                date=now()
            )

            # Generate the PDF receipt
            pdf_buffer = generate_receipt(courier, request.user)

            # Prepare and send the email with the attached PDF
            subject = "Payment Processing - Glotürk Logistics Kargo"
            html_message = format_html(
                """
                <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px;">
                    <h1 style="color: #000000;">Glotürk Logistics Kargo</h1>
                    <p style="font-size: 16px; color: #333;">Dear <strong>{}</strong>,</p>
                    <p style="font-size: 16px; color: #333;">
                        Thank you for choosing Glotürk Logistics for your delivery service.<br>
                        We have received your payment and your delivery details are being processed.
                    </p>
                    <h2 style="color: #28a745;">Delivery Details</h2>
                    <table style="margin: 0 auto; border-collapse: collapse; font-size: 14px;">
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Tracking Number:</strong></td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Delivery Status:</strong></td>
                            <td style="padding: 8px; border: 1px solid #ddd;">Pending</td>
                        </tr>
                    </table>
                    <p style="font-size: 14px; color: #666; margin-top: 20px;">
                        If you have any questions, feel free to contact us at <a href="mailto:info@megametalmachinery.com">info@megametalmachinery.com</a>.
                    </p>
                    <p style="font-size: 14px; color: #666;">Best regards,<br>Glotürk Logistics Kargo Team</p>
                </div>
                """,
                request.user.first_name,
                courier.tracking_number,
            )

            email = EmailMessage(
                subject,
                html_message,
                settings.EMAIL_HOST_USER,
                [request.user.email]
            )
            email.content_subtype = "html"  # Specify HTML content
            email.attach(f"Delivery_Receipt_{courier.tracking_number}.pdf", pdf_buffer.getvalue(), "application/pdf")

            try:
                email.send()
            except Exception as e:
                return JsonResponse({'error': f'Failed to send email: {str(e)}'}, status=500)

            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': 'Invalid form data or missing delivery price'}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)






def track_package(request):
    tracking_status = None
    tracking_error = None

    if request.method == 'POST':
        tracking_number = request.POST.get('tracking_number', '').strip()  # Remove whitespace
        if tracking_number:
            try:
                # Find the courier by tracking number without checking user
                courier = Courier.objects.get(tracking_number=tracking_number)
                
                # Pass the courier object to the template
                tracking_status = courier  
            except Courier.DoesNotExist:
                tracking_error = "No package found with the provided tracking number."
        else:
            tracking_error = "Please enter a valid tracking number."

    return render(request, 'track_item.html', {
        'tracking_status': tracking_status,
        'tracking_error': tracking_error
    })




def transaction_history(request):
    """View to display a list of all transactions for the logged-in user."""
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')  # Get user's transactions
    return render(request, 'history.html', {'transactions': transactions})    







def send_reset_code_view(request):
    if request.method == 'POST':
        form = SendresetcodeForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            # Check if the email is registered
            User = get_user_model()  # Get the custom user model
            if not User.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'message': 'This email address is not registered.'})

            # Generate a reset code
            reset_code = get_random_string(length=7)  # Generate a random string as the reset code
            
            # Store the reset code in the database
            PasswordResetCode.objects.update_or_create(
                email=email,
                defaults={'reset_code': reset_code}
            )
            
            # Send the email
            send_mail(
                'Password Reset Code',
                f'Your password reset code is: {reset_code}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            return JsonResponse({'success': True, 'message': 'A password reset code has been sent to your email.'})
        else:
            return JsonResponse({'success': False, 'message': form.errors['email'][0]})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})





def reset_password_view(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)  # Use a different variable name
        if form.is_valid():
            email = form.cleaned_data['email']
            reset_code = form.cleaned_data['reset_code']
            new_password = form.cleaned_data['new_password']

            # Check if the reset code is valid for the given email
            try:
                reset_entry = PasswordResetCode.objects.get(email=email, reset_code=reset_code)
            except PasswordResetCode.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Invalid reset code or email.'})

            # Update the user's password
            User = get_user_model()
            try:
                user = User.objects.get(email=email)
                user.set_password(new_password)  # Set the new password
                user.save()

                # Optionally, delete the reset code after use
                reset_entry.delete()

                messages.success(request, "Your password has been reset successfully.")
                return JsonResponse({'success': True, 'message': 'Your password has been reset successfully.'})
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'User  not found.'})

    else:
        form = PasswordResetForm()  # This is now correctly instantiated

    return render(request,'forms/reset_pass.html', {'form': form})







def contact_send(request):
    logger.info(f"Request method: {request.method}")

    if request.method == 'POST':
        # Get data sent from the form (JSON format)
        data = json.loads(request.body)
        fullname = data.get('fullname')
        email = data.get('email')
        phone_number = data.get('phone_number')
        service_type = data.get('service_type')
        subject = data.get('subject')
      
        logger.info(f"Received contact message from {fullname} ({email}) with subject: {subject}")

        # Check if required fields are provided
        if not fullname or not email or not subject :
            logger.warning("Missing required fields in the contact form.")
            return JsonResponse({
                'success': False,
                'error_message': 'All fields are required.',
            })

        # Prepare the email content with HTML formatting
        email_subject = f"New Contact Message: {subject}"
        email_message = format_html(
            """
            <html>
                <body>
                    <h2>New Contact Message</h2>
                    <p><strong>Name:</strong> {fullname}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Phone Number:</strong> {phone_number}</p>
                    <p><strong>Service Type:</strong> {service_type}</p>
                    <p><strong>Message:</strong></p>
                    <p>{subject}</p>
                </body>
            </html>
            """,
            fullname=fullname,
            email=email,
            phone_number=phone_number,
            service_type=service_type,
            subject=subject
        )
        recipient_email = 'info@gloturklogistics.com'  # Replace with your recipient email

        try:
            # Send email using Django's send_mail function
            send_mail(
                email_subject,       # Email subject
                email_message,       # Email message (HTML)
                settings.DEFAULT_FROM_EMAIL,  # Sender email
                [recipient_email],      # Receiver email
                fail_silently=False,
                html_message=email_message  # Send HTML message
            )
            logger.info(f"Contact message sent successfully to {recipient_email}.")
            return JsonResponse({'success': True, 'message': 'Your message has been sent successfully!'})

        except Exception as e:
            logger.error(f"Failed to send contact message: {e}")
            return JsonResponse({'success': False, 'message': 'There was an error sending your message. Please try again later.'})

    # Return error response for invalid request method
    logger.error("Invalid request method.")
    return JsonResponse({'success': False, 'message': 'Invalid request method. Please use POST.'})




def contact_us_send(request):
    logger.info(f"Request method: {request.method}")

    if request.method == 'POST':
        # Get data sent from the form (JSON format)
        data = json.loads(request.body)
        name = data.get('name')
        email = data.get('email')
        subject = data.get('subject')
        message = data.get('message')
      
        logger.info(f"Received contact message from {name} ({email}) with message: {message}")

        # Check if required fields are provided
        if not name or not email or not message:
            logger.warning("Missing required fields in the contact form.")
            return JsonResponse({
                'success': False,
                'error_message': 'All fields are required.',
            })

        # Prepare the email content with HTML formatting
        email_subject = f"New Contact Message: {subject}"
        email_message = format_html(
            """
            <html>
                <body>
                    <h2>New Contact Message</h2>
                    <p><strong>Name:</strong> {name}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Service Type:</strong> {subject}</p>
                    <p><strong>Message:</strong></p>
                    <p>{message}</p>
                </body>
            </html>
            """,
            name=name,  # Corrected variable name
            email=email,
            subject=subject,
            message=message
        )
        recipient_email = 'info@gloturklogistics.com'  # Replace with your recipient email

        try:
            # Send email using Django's send_mail function
            send_mail(
                email_subject,       # Email subject
                '',                  # Email message (text version, if needed)
                settings.DEFAULT_FROM_EMAIL,  # Sender email
                [recipient_email],      # Receiver email
                fail_silently=False,
                html_message=email_message  # Send HTML message
            )
            logger.info(f"Contact message sent successfully to {recipient_email}.")
            return JsonResponse({'success': True, 'message': 'Your message has been sent successfully!'})

        except Exception as e:
            logger.error(f"Failed to send contact message: {e}")
            return JsonResponse({'success': False, 'message': 'There was an error sending your message. Please try again later.'})

    # Return error response for invalid request method
    logger.error("Invalid request method.")
    return JsonResponse({'success': False, 'message': 'Invalid request method. Please use POST.'})