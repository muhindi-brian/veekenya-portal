from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Sum, Q, Count
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.db.models.functions import TruncMonth, TruncYear
from django.urls import reverse
from django.utils.html import strip_tags

from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from .models import Child, Sponsor, Sponsorship, Donation, UserProfile, AuditLog, DataAccessLog, ComplianceReport
from .forms import UserManagementForm, UserEditForm

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import socket
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Create your views here.

def home(request):
    return render(request, 'core/home.html')

@login_required
def dashboard(request):
    # Get statistics
    context = {
        'total_children': Child.objects.count(),
        'active_sponsors': Sponsor.objects.count(),
        'total_donations': Donation.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
        'active_sponsorships': Sponsorship.objects.filter(end_date__isnull=True).count(),
        
        # Get recent activities (last 5)
        'recent_activities': [
            # This would be replaced with actual activity tracking
            {
                'icon': 'fa-child',
                'description': 'New child added: John Doe',
                'timestamp': timezone.now()
            },
            {
                'icon': 'fa-dollar-sign',
                'description': 'New donation received: $500',
                'timestamp': timezone.now()
            }
        ]
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def children_list(request):
    # Get all children with optional search filter
    search_query = request.GET.get('search', '')
    education_level = request.GET.get('education_level', '')
    
    children = Child.objects.all().order_by('-date_added')
    
    # Apply filters if provided
    if search_query:
        children = children.filter(
            Q(full_name__icontains=search_query) |
            Q(school__icontains=search_query) |
            Q(village__icontains=search_query)
        )
    
    if education_level:
        children = children.filter(education_level=education_level)
    
    # Pagination
    paginator = Paginator(children, 10)  # Show 10 children per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'children': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
        'paginator': paginator,
    }
    return render(request, 'core/children_list.html', context)

@login_required
def child_detail(request, child_id):
    child = get_object_or_404(Child, id=child_id)
    return render(request, 'core/child_detail.html', {'child': child})

@login_required
def sponsors_list(request):
    # Get all sponsors with optional search filter
    search_query = request.GET.get('search', '')
    country_filter = request.GET.get('country', '')
    
    sponsors = Sponsor.objects.all().order_by('-joined_date')
    
    # Apply filters if provided
    if search_query:
        sponsors = sponsors.filter(
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(country__icontains=search_query)
        )
    
    if country_filter:
        sponsors = sponsors.filter(country=country_filter)
    
    # Get unique countries for filter dropdown
    countries = Sponsor.objects.values_list('country', flat=True).distinct()
    
    # Pagination
    paginator = Paginator(sponsors, 10)  # Show 10 sponsors per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'sponsors': page_obj,
        'countries': countries,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
        'paginator': paginator,
    }
    return render(request, 'core/sponsors_list.html', context)

@login_required
def sponsorships_list(request):
    return render(request, 'core/sponsorships_list.html')

@login_required
def donations_list(request):
    # Get all donations with optional search filter
    search_query = request.GET.get('search', '')
    
    donations = Donation.objects.all().order_by('-date_received')
    
    # Apply filters if provided
    if search_query:
        donations = donations.filter(
            Q(sponsor__full_name__icontains=search_query) |
            Q(child__full_name__icontains=search_query) |
            Q(amount__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(donations, 10)  # Show 10 donations per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'donations': page_obj,
        'total_amount': Donation.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
        'paginator': paginator,
    }
    return render(request, 'core/donations_list.html', context)

@login_required
def reports(request):
    # Get date range from request or default to current month
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # Last 12 months by default
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
    
    # Get statistics
    context = {
        'total_children': Child.objects.count(),
        'active_sponsors': Sponsor.objects.count(),
        'active_sponsorships': Sponsorship.objects.filter(end_date__isnull=True).count(),
        'total_donations': Donation.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
        
        # Monthly donations
        'monthly_donations': Donation.objects.filter(
            date_received__range=[start_date, end_date]
        ).annotate(
            month=TruncMonth('date_received')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month'),
        
        # Yearly donations
        'yearly_donations': Donation.objects.filter(
            date_received__range=[start_date, end_date]
        ).annotate(
            year=TruncYear('date_received')
        ).values('year').annotate(
            total=Sum('amount')
        ).order_by('year'),
        
        # Top sponsors
        'top_sponsors': Sponsor.objects.annotate(
            total_donations=Sum('donations__amount')
        ).filter(
            total_donations__gt=0
        ).order_by('-total_donations')[:5],
        
        # Recent sponsorships
        'recent_sponsorships': Sponsorship.objects.filter(
            start_date__range=[start_date, end_date]
        ).order_by('-start_date')[:10],
        
        # Date range for the form
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    }
    
    return render(request, 'core/reports.html', context)

@login_required
def message_center(request):
    return render(request, 'core/messages.html')

@login_required
def settings(request):
    return render(request, 'core/settings.html')

# Quick action views
@login_required
def add_child(request):
    if request.method == 'POST':
        try:
            # Extract form data
            child = Child.objects.create(
                full_name=request.POST['full_name'],
                birth_date=request.POST['birth_date'],
                gender=request.POST['gender'],
                village=request.POST['village'],
                school=request.POST['school'],
                education_level=request.POST['education_level'],
                health_notes=request.POST['health_notes']
            )
            messages.success(request, f'Child record for {child.full_name} created successfully.')
            return redirect('children')
        except Exception as e:
            messages.error(request, 'Error creating child record. Please check your input.')
            return render(request, 'core/add_child.html', {'form_data': request.POST})
    
    return render(request, 'core/add_child.html')

@login_required
def edit_child(request, child_id):
    child = get_object_or_404(Child, id=child_id)
    if request.method == 'POST':
        # Handle form submission
        pass
    return render(request, 'core/edit_child.html', {'child': child})

@login_required
def delete_child(request, child_id):
    child = get_object_or_404(Child, id=child_id)
    if request.method == 'POST':
        child.delete()
        messages.success(request, 'Child record deleted successfully.')
        return redirect('children')
    return redirect('child_detail', child_id=child_id)

@login_required
def add_sponsor(request):
    if request.method == 'POST':
        try:
            # Extract form data
            sponsor = Sponsor.objects.create(
                full_name=request.POST['full_name'],
                email=request.POST['email'],
                phone=request.POST['phone'],
                country=request.POST['country']
            )
            messages.success(request, f'Sponsor {sponsor.full_name} created successfully.')
            return redirect('sponsors')
        except Exception as e:
            messages.error(request, 'Error creating sponsor. Please check your input.')
            return render(request, 'core/add_sponsor.html', {'form_data': request.POST})
    
    return render(request, 'core/add_sponsor.html')

@login_required
def add_donation(request):
    if request.method == 'POST':
        try:
            # Extract form data
            sponsor = get_object_or_404(Sponsor, id=request.POST['sponsor'])
            
            donation = Donation.objects.create(
                sponsor=sponsor,
                amount=request.POST['amount'],
                date_received=request.POST['date_received'],
                purpose=request.POST['purpose']
            )
            messages.success(request, f'Donation of ${donation.amount} from {sponsor.full_name} recorded successfully.')
            return redirect('donations')
        except Exception as e:
            messages.error(request, 'Error recording donation. Please check your input.')
            return render(request, 'core/add_donation.html', {'form_data': request.POST})
    
    # Get all sponsors for the form
    sponsors = Sponsor.objects.all()
    return render(request, 'core/add_donation.html', {
        'sponsors': sponsors
    })

@login_required
def add_sponsorship(request):
    if request.method == 'POST':
        try:
            # Extract form data
            child = get_object_or_404(Child, id=request.POST['child'])
            sponsor = get_object_or_404(Sponsor, id=request.POST['sponsor'])
            
            sponsorship = Sponsorship.objects.create(
                child=child,
                sponsor=sponsor,
                start_date=request.POST['start_date'],
                notes=request.POST.get('notes', '')
            )
            messages.success(request, f'Sponsorship created successfully between {sponsor.full_name} and {child.full_name}.')
            return redirect('sponsorships')
        except Exception as e:
            messages.error(request, 'Error creating sponsorship. Please check your input.')
            return render(request, 'core/add_sponsorship.html', {'form_data': request.POST})
    
    # Get all available children and sponsors for the form
    children = Child.objects.filter(sponsorships__isnull=True)
    sponsors = Sponsor.objects.all()
    return render(request, 'core/add_sponsorship.html', {
        'children': children,
        'sponsors': sponsors
    })

@login_required
def generate_report(request):
    # Create the HttpResponse object with PDF headers
    buffer = BytesIO()
    
    # Create the PDF object using ReportLab
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Add the title
    elements.append(Paragraph('VeeKenya Report', title_style))
    elements.append(Paragraph(f'Generated on {datetime.now().strftime("%B %d, %Y")}', subtitle_style))
    elements.append(Spacer(1, 12))
    
    # Add summary statistics
    elements.append(Paragraph('Summary Statistics', subtitle_style))
    elements.append(Spacer(1, 12))
    
    # Create statistics table
    stats_data = [
        ['Metric', 'Value'],
        ['Total Children', str(Child.objects.count())],
        ['Active Sponsors', str(Sponsor.objects.count())],
        ['Active Sponsorships', str(Sponsorship.objects.filter(end_date__isnull=True).count())],
        ['Total Donations', f'${Donation.objects.aggregate(Sum("amount"))["amount__sum"] or 0:,.2f}'],
    ]
    
    stats_table = Table(stats_data, colWidths=[4*inch, 2*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 20))
    
    # Add top sponsors section
    elements.append(Paragraph('Top Sponsors', subtitle_style))
    elements.append(Spacer(1, 12))
    
    # Get top sponsors data
    top_sponsors = Sponsor.objects.annotate(
        total_donations=Sum('donations__amount')
    ).filter(
        total_donations__gt=0
    ).order_by('-total_donations')[:5]
    
    sponsors_data = [['Sponsor Name', 'Email', 'Total Donations']]
    for sponsor in top_sponsors:
        sponsors_data.append([
            sponsor.full_name,
            sponsor.email,
            f'${sponsor.total_donations:,.2f}'
        ])
    
    sponsors_table = Table(sponsors_data, colWidths=[2.5*inch, 3*inch, 1.5*inch])
    sponsors_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
    ]))
    elements.append(sponsors_table)
    elements.append(Spacer(1, 20))
    
    # Add recent sponsorships section
    elements.append(Paragraph('Recent Sponsorships', subtitle_style))
    elements.append(Spacer(1, 12))
    
    # Get recent sponsorships data
    recent_sponsorships = Sponsorship.objects.all().order_by('-start_date')[:10]
    
    sponsorships_data = [['Start Date', 'Child', 'Sponsor', 'Status']]
    for sponsorship in recent_sponsorships:
        sponsorships_data.append([
            sponsorship.start_date.strftime('%Y-%m-%d'),
            sponsorship.child.full_name,
            sponsorship.sponsor.full_name,
            'Active' if not sponsorship.end_date else 'Ended'
        ])
    
    sponsorships_table = Table(sponsorships_data, colWidths=[1.5*inch, 2*inch, 2*inch, 1.5*inch])
    sponsorships_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(sponsorships_table)
    
    # Build the PDF document
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create the HTTP response with PDF content
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="veekenya_report.pdf"'
    response.write(pdf)
    
    return response

def is_superuser(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_superuser)
def user_management(request):
    # Get filters
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    users = User.objects.select_related('profile').exclude(id=request.user.id)
    
    # Apply filters
    if role_filter:
        users = users.filter(profile__role=role_filter)
    if status_filter:
        is_active = status_filter == 'active'
        users = users.filter(profile__is_active=is_active)
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Get user statistics
    all_users = User.objects.select_related('profile').exclude(id=request.user.id)
    total_users = all_users.count()
    active_users = all_users.filter(profile__is_active=True).count()
    inactive_users = total_users - active_users
    
    # Pagination
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'role_choices': UserProfile.ROLE_CHOICES,
        'current_role': role_filter,
        'current_status': status_filter,
        'search_query': search_query,
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
    }
    return render(request, 'core/admin/dashboard_users.html', context)

@user_passes_test(is_superuser)
def add_user(request):
    if request.method == 'POST':
        form = UserManagementForm(request.POST)
        if form.is_valid():
            try:
                # Create user
                user = form.save()
                
                # Get the generated password
                password = form.cleaned_data.get('password')
                
                # Prepare email context
                context = {
                    'user': user,
                    'password': password,
                    'login_url': request.build_absolute_uri(reverse('home')),
                }
                
                # Render email templates
                html_message = render_to_string('core/emails/welcome.html', context)
                plain_message = strip_tags(html_message)
                
                # Send email with better error handling
                try:
                    send_mail(
                        subject='Welcome to VeeKenya',
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        html_message=html_message,
                        fail_silently=False,  # Raise exceptions for debugging
                    )
                    messages.success(request, f'User {user.username} created successfully and welcome email sent.')
                    logger.info(f"User {user.username} created and welcome email sent to {user.email}")
                except Exception as e:
                    # Log the error but don't fail the user creation
                    error_msg = f"Failed to send welcome email to {user.email}: {str(e)}"
                    logger.error(error_msg)
                    messages.warning(request, f'User created but failed to send welcome email: {str(e)}')
                
                return redirect('user_management')
            except Exception as e:
                error_msg = f"Error creating user: {str(e)}"
                logger.error(error_msg)
                messages.error(request, error_msg)
    else:
        form = UserManagementForm()
    
    return render(request, 'core/admin/add_user.html', {'form': form})

@user_passes_test(is_superuser)
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {user.get_full_name()} updated successfully.')
            return redirect('user_management')
    else:
        form = UserEditForm(instance=user)
    
    return render(request, 'core/admin/edit_user.html', {
        'form': form,
        'user_obj': user
    })

@user_passes_test(is_superuser)
def toggle_user_status(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.profile.is_active = not user.profile.is_active
        user.profile.save()
        
        status = 'activated' if user.profile.is_active else 'deactivated'
        messages.success(request, f'User {user.get_full_name()} {status} successfully.')
    
    return redirect('user_management')

@user_passes_test(is_superuser)
def delete_user(request, user_id):
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Prevent deletion of superusers
            if user.is_superuser:
                messages.error(request, 'Cannot delete superuser accounts.')
                return redirect('user_management')
            
            # Store user info for email before deletion
            user_email = user.email
            user_first_name = user.first_name
            
            # Send deletion notification email
            try:
                context = {
                    'user': user,
                    'deletion_date': timezone.now()
                }
                
                # Create both HTML and plain text versions
                email_html = render_to_string('core/emails/account_deleted.html', context)
                email_plain = f"""
                Account Deletion Notice
                
                Dear {user_first_name},
                
                This email is to inform you that your VeeKenya account has been deleted from the system.
                
                Account Information:
                Username: {user.username}
                Email: {user_email}
                Deletion Date: {timezone.now().strftime('%B %d, %Y')}
                
                All your personal data has been removed from our system in accordance with our data protection policies.
                
                If you believe this action was taken in error, or if you have any questions, please contact our support team immediately.
                
                Best regards,
                The VeeKenya Team
                """
                
                # Send the email
                send_mail(
                    'Your VeeKenya Account Has Been Deleted',
                    email_plain,
                    settings.DEFAULT_FROM_EMAIL,
                    [user_email],
                    html_message=email_html,
                    fail_silently=False,
                )
                print(f"Deletion notification email sent to {user_email}")  # Debug log
            except Exception as e:
                error_message = f'Failed to send deletion notification email: {str(e)}'
                print(error_message)  # Debug log
                messages.warning(request, error_message)
            
            # Delete the user
            user.delete()
            messages.success(request, f'User {user_first_name} has been deleted successfully.')
            
        except Exception as e:
            error_message = f'Error deleting user: {str(e)}'
            print(error_message)  # Debug log
            messages.error(request, error_message)
    
    return redirect('user_management')

@login_required
def profile(request):
    """View for user's profile page"""
    return render(request, 'core/user/profile.html')

@login_required
def update_profile(request):
    """Handle profile information updates"""
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()
        
        profile = user.profile
        profile.phone_number = request.POST.get('phone_number', '')
        profile.address = request.POST.get('address', '')
        profile.bio = request.POST.get('bio', '')
        profile.save()
        
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')
    
    return redirect('profile')

@login_required
def change_password(request):
    """Handle password changes"""
    if request.method == 'POST':
        user = request.user
        current_password = request.POST.get('current_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password1 != new_password2:
            messages.error(request, 'New passwords do not match.')
        else:
            user.set_password(new_password1)
            user.save()
            messages.success(request, 'Password changed successfully. Please log in again.')
            return redirect('login')
    
    return redirect('profile')

@login_required
def update_notifications(request):
    """Handle notification preferences updates"""
    if request.method == 'POST':
        profile = request.user.profile
        profile.email_notifications = 'email_notifications' in request.POST
        profile.sms_notifications = 'sms_notifications' in request.POST
        profile.save()
        
        messages.success(request, 'Notification preferences updated successfully.')
    return redirect('profile')

@login_required
def export_data(request):
    """Export user's personal data"""
    if request.method == 'POST':
        user = request.user
        profile = user.profile
        
        # Prepare user data
        data = {
            'personal_info': {
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
            },
            'profile_info': {
                'role': profile.role,
                'phone_number': profile.phone_number,
                'address': profile.address,
                'bio': profile.bio,
                'created_at': profile.created_at.isoformat(),
                'modified_at': profile.modified_at.isoformat(),
            },
            'preferences': {
                'email_notifications': profile.email_notifications,
                'sms_notifications': profile.sms_notifications,
            }
        }
        
        # Create JSON response
        response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{user.username}_data_export.json"'
        return response
    
    return redirect('profile')

@login_required
def request_deletion(request):
    """Handle account deletion requests"""
    if request.method == 'POST':
        profile = request.user.profile
        profile.deletion_requested = timezone.now()
        profile.deletion_reason = request.POST.get('reason', '')
        profile.save()
        
        # Send notification to administrators
        admins = User.objects.filter(is_superuser=True)
        context = {
            'user': request.user,
            'reason': profile.deletion_reason,
            'requested_at': profile.deletion_requested,
        }
        
        html_message = render_to_string('core/email/deletion_request.html', context)
        
        for admin in admins:
            send_mail(
                'Account Deletion Request',
                '',
                settings.DEFAULT_FROM_EMAIL,
                [admin.email],
                html_message=html_message,
                fail_silently=True,
            )
        
        messages.info(request, 'Your account deletion request has been submitted. An administrator will review your request.')
    return redirect('profile')

@user_passes_test(lambda u: u.is_staff)
def audit_logs(request):
    """View for audit logs and user activity"""
    # Get filters from request
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    action_type = request.GET.get('action_type')
    user_id = request.GET.get('user_id')
    
    # Base queryset
    logs = AuditLog.objects.all()
    
    # Apply filters
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__lte=date_to)
    if action_type:
        logs = logs.filter(action_type=action_type)
    if user_id:
        logs = logs.filter(user_id=user_id)
    
    # Pagination
    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs = paginator.get_page(page)
    
    context = {
        'logs': logs,
        'action_types': dict(AuditLog.ACTION_TYPES),
        'users': User.objects.all(),
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'action_type': action_type,
            'user_id': user_id,
        }
    }
    return render(request, 'core/admin/audit_logs.html', context)

@user_passes_test(lambda u: u.is_staff)
def data_access_logs(request):
    """View for data access logs"""
    # Get filters from request
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    operation_type = request.GET.get('operation_type')
    data_model = request.GET.get('data_model')
    user_id = request.GET.get('user_id')
    
    # Base queryset
    logs = DataAccessLog.objects.all()
    
    # Apply filters
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__lte=date_to)
    if operation_type:
        logs = logs.filter(operation_type=operation_type)
    if data_model:
        logs = logs.filter(data_model=data_model)
    if user_id:
        logs = logs.filter(user_id=user_id)
    
    # Pagination
    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs = paginator.get_page(page)
    
    context = {
        'logs': logs,
        'operation_types': dict(DataAccessLog.OPERATION_TYPES),
        'data_models': DataAccessLog.objects.values_list('data_model', flat=True).distinct(),
        'users': User.objects.all(),
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'operation_type': operation_type,
            'data_model': data_model,
            'user_id': user_id,
        }
    }
    return render(request, 'core/admin/data_access_logs.html', context)

@user_passes_test(lambda u: u.is_staff)
def generate_compliance_report(request):
    """Generate a compliance report"""
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        period_start = request.POST.get('period_start')
        period_end = request.POST.get('period_end')
        
        # Convert string dates to datetime
        start_date = datetime.strptime(period_start, '%Y-%m-%d')
        end_date = datetime.strptime(period_end, '%Y-%m-%d')
        
        # Generate report data based on type
        report_data = {}
        if report_type == 'data_access':
            report_data = {
                'total_accesses': DataAccessLog.objects.filter(
                    timestamp__range=(start_date, end_date)
                ).count(),
                'access_by_type': list(DataAccessLog.objects.filter(
                    timestamp__range=(start_date, end_date)
                ).values('operation_type').annotate(count=Count('id'))),
                'access_by_model': list(DataAccessLog.objects.filter(
                    timestamp__range=(start_date, end_date)
                ).values('data_model').annotate(count=Count('id'))),
            }
        elif report_type == 'user_activity':
            report_data = {
                'total_activities': AuditLog.objects.filter(
                    timestamp__range=(start_date, end_date)
                ).count(),
                'activities_by_type': list(AuditLog.objects.filter(
                    timestamp__range=(start_date, end_date)
                ).values('action_type').annotate(count=Count('id'))),
                'activities_by_status': list(AuditLog.objects.filter(
                    timestamp__range=(start_date, end_date)
                ).values('status').annotate(count=Count('id'))),
            }
        
        # Create compliance report
        report = ComplianceReport.objects.create(
            report_type=report_type,
            generated_by=request.user,
            report_period_start=start_date,
            report_period_end=end_date,
            report_data=report_data,
            summary=f"Compliance report for period {period_start} to {period_end}"
        )
        
        messages.success(request, 'Compliance report generated successfully.')
        return redirect('view_compliance_report', report_id=report.id)
    
    context = {
        'report_types': dict(ComplianceReport.REPORT_TYPES)
    }
    return render(request, 'core/admin/generate_compliance_report.html', context)

@user_passes_test(lambda u: u.is_staff)
def view_compliance_report(request, report_id):
    """View a specific compliance report"""
    report = get_object_or_404(ComplianceReport, id=report_id)
    return render(request, 'core/admin/view_compliance_report.html', {'report': report})

@user_passes_test(lambda u: u.is_staff)
def compliance_reports_list(request):
    """List all compliance reports"""
    reports = ComplianceReport.objects.all().order_by('-generated_at')
    return render(request, 'core/admin/compliance_reports_list.html', {'reports': reports})

@user_passes_test(is_superuser)
def test_email(request):
    """Test email configuration with detailed error handling"""
    if request.method == 'POST':
        test_email = request.POST.get('test_email')
        if test_email:
            try:
                # Create message
                msg = MIMEMultipart('alternative')
                msg['Subject'] = 'VeeKenya Email Test'
                msg['From'] = settings.DEFAULT_FROM_EMAIL
                msg['To'] = test_email
                
                # Create both plain text and HTML versions
                text = f"""
                VeeKenya Email Test
                
                This is a test email sent at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
                If you're receiving this, the email system is working correctly.
                
                Test Details:
                - From: {settings.DEFAULT_FROM_EMAIL}
                - To: {test_email}
                - Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                
                html = f"""
                <html>
                    <body>
                        <h1>VeeKenya Email Test</h1>
                        <p>This is a test email sent at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p>If you're receiving this, the email system is working correctly.</p>
                        <hr>
                        <p><strong>Test Details:</strong></p>
                        <ul>
                            <li>From: {settings.DEFAULT_FROM_EMAIL}</li>
                            <li>To: {test_email}</li>
                            <li>Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                        </ul>
                    </body>
                </html>
                """
                
                msg.attach(MIMEText(text, 'plain'))
                msg.attach(MIMEText(html, 'html'))
                
                # Send email with detailed error handling
                try:
                    # First try direct SMTP
                    with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=settings.EMAIL_TIMEOUT) as smtp:
                        smtp.starttls()
                        smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                        smtp.send_message(msg)
                        messages.success(request, f'Test email sent successfully to {test_email}')
                        print(f"Test email sent successfully to {test_email}")  # Console log
                except Exception as e:
                    # If direct SMTP fails, try Django's send_mail
                    print(f"Direct SMTP failed, trying Django's send_mail: {str(e)}")  # Console log
                    send_mail(
                        subject='VeeKenya Email Test',
                        message=text,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[test_email],
                        html_message=html,
                        fail_silently=False,
                    )
                    messages.success(request, f'Test email sent successfully to {test_email} (via Django)')
                    print(f"Test email sent successfully to {test_email} via Django's send_mail")  # Console log
                
            except Exception as e:
                error_message = f'Failed to send test email: {str(e)}'
                messages.error(request, error_message)
                print(f"Error sending test email: {str(e)}")  # Console log
        else:
            messages.error(request, 'Please provide an email address')
    
    return render(request, 'core/admin/test_email.html')

@user_passes_test(is_superuser)
def diagnose_email(request):
    """Detailed email system diagnosis"""
    results = []
    
    # Test 1: Basic SMTP Connection
    try:
        smtp = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=settings.EMAIL_TIMEOUT)
        results.append(('Basic SMTP Connection', 'Success', f'Connected to {settings.EMAIL_HOST}:{settings.EMAIL_PORT}'))
    except Exception as e:
        results.append(('Basic SMTP Connection', 'Failed', f'Failed to connect: {str(e)}'))
        return render(request, 'core/admin/email_diagnosis.html', {'results': results})
    
    # Test 2: STARTTLS
    try:
        smtp.starttls()
        results.append(('STARTTLS', 'Success', 'Successfully initiated TLS connection'))
    except Exception as e:
        results.append(('STARTTLS', 'Failed', f'Failed to start TLS: {str(e)}'))
        smtp.quit()
        return render(request, 'core/admin/email_diagnosis.html', {'results': results})
    
    # Test 3: Authentication
    try:
        smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        results.append(('Authentication', 'Success', f'Successfully authenticated as {settings.EMAIL_HOST_USER}'))
    except Exception as e:
        results.append(('Authentication', 'Failed', f'Failed to authenticate: {str(e)}'))
        smtp.quit()
        return render(request, 'core/admin/email_diagnosis.html', {'results': results})
    
    # Test 4: Send Test Email
    try:
        test_email = request.user.email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'VeeKenya Email System Test'
        msg['From'] = settings.DEFAULT_FROM_EMAIL
        msg['To'] = test_email
        
        text = "This is a test email from VeeKenya system."
        html = f"""
        <html>
            <body>
                <h1>VeeKenya Email System Test</h1>
                <p>This is a test email sent at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>If you're receiving this, the email system is working correctly.</p>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        
        smtp.send_message(msg)
        results.append(('Send Test Email', 'Success', f'Test email sent to {test_email}'))
    except Exception as e:
        results.append(('Send Test Email', 'Failed', f'Failed to send test email: {str(e)}'))
    finally:
        try:
            smtp.quit()
        except:
            pass
    
    # Test 5: Check Settings
    settings_check = [
        ('EMAIL_BACKEND', settings.EMAIL_BACKEND),
        ('EMAIL_HOST', settings.EMAIL_HOST),
        ('EMAIL_PORT', settings.EMAIL_PORT),
        ('EMAIL_USE_TLS', settings.EMAIL_USE_TLS),
        ('EMAIL_HOST_USER', settings.EMAIL_HOST_USER),
        ('DEFAULT_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL),
        ('EMAIL_TIMEOUT', settings.EMAIL_TIMEOUT),
    ]
    
    for setting, value in settings_check:
        results.append(('Setting: ' + setting, 'Info', str(value)))
    
    # Test 6: DNS Resolution
    try:
        socket.gethostbyname(settings.EMAIL_HOST)
        results.append(('DNS Resolution', 'Success', f'Successfully resolved {settings.EMAIL_HOST}'))
    except Exception as e:
        results.append(('DNS Resolution', 'Failed', f'Failed to resolve {settings.EMAIL_HOST}: {str(e)}'))
    
    context = {
        'results': results,
        'user_email': request.user.email
    }
    
    return render(request, 'core/admin/email_diagnosis.html', context)
