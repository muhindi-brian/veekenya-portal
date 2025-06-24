from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # Dashboard is now the index of core URLs
    path('children/', views.children_list, name='children'),
    path('sponsors/', views.sponsors_list, name='sponsors'),
    path('sponsorships/', views.sponsorships_list, name='sponsorships'),
    path('donations/', views.donations_list, name='donations'),
    path('reports/', views.reports, name='reports'),
    path('messages/', views.message_center, name='messages'),
    path('settings/', views.settings, name='settings'),
    
    # Quick action URLs
    path('children/add/', views.add_child, name='add_child'),
    path('sponsors/add/', views.add_sponsor, name='add_sponsor'),
    path('sponsorships/add/', views.add_sponsorship, name='add_sponsorship'),
    path('donations/add/', views.add_donation, name='add_donation'),
    path('reports/generate/', views.generate_report, name='generate_report'),
    
    # User Management URLs
    path('users/', views.user_management, name='user_management'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('users/test-email/', views.test_email, name='test_email'),
    path('users/diagnose-email/', views.diagnose_email, name='diagnose_email'),
    
    # User Self-Service URLs
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('profile/notifications/', views.update_notifications, name='update_notifications'),
    path('profile/export-data/', views.export_data, name='export_data'),
    path('profile/request-deletion/', views.request_deletion, name='request_deletion'),
    
    # Audit and Compliance URLs
    path('admin/audit-logs/', views.audit_logs, name='audit_logs'),
    path('admin/data-access-logs/', views.data_access_logs, name='data_access_logs'),
    path('admin/compliance/generate/', views.generate_compliance_report, name='generate_compliance_report'),
    path('admin/compliance/reports/', views.compliance_reports_list, name='compliance_reports_list'),
    path('admin/compliance/reports/<int:report_id>/', views.view_compliance_report, name='view_compliance_report'),
] 