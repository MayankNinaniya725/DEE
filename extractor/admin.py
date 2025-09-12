from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ExtractedData, Vendor, UploadedPDF
from .models.user import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_admin', 'is_active', 'date_joined')
    list_filter = ('role', 'is_admin', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_admin', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'is_admin'),
        }),
    )

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'config_file_link', 'total_pdfs', 'total_extractions']
    search_fields = ['name']
    list_per_page = 20
    
    def config_file_link(self, obj):
        if obj.config_file:
            return format_html('<a href="{}" target="_blank" class="button"><i class="fas fa-file"></i> View Config</a>', 
                             obj.config_file.url)
        return "-"
    config_file_link.short_description = "Config File"
    
    def total_pdfs(self, obj):
        count = obj.pdfs.count()
        url = reverse('admin:extractor_uploadedpdf_changelist') + f'?vendor__id__exact={obj.id}'
        return format_html('<a href="{}">{} PDFs</a>', url, count)
    total_pdfs.short_description = "Total PDFs"
    
    def total_extractions(self, obj):
        count = ExtractedData.objects.filter(vendor=obj).count()
        url = reverse('admin:extractor_extracteddata_changelist') + f'?vendor__id__exact={obj.id}'
        return format_html('<a href="{}">{} Extractions</a>', url, count)
    total_extractions.short_description = "Total Extractions"

    class Media:
        css = {
            'all': ['admin/css/vendor.css']
        }

@admin.register(UploadedPDF)
class UploadedPDFAdmin(admin.ModelAdmin):
    list_display = ['id', 'vendor', 'file_link', 'uploaded_at', 'extracted_count', 'file_size_display']
    list_filter = ['vendor', 'uploaded_at']
    search_fields = ['file', 'vendor__name']
    list_per_page = 20
    date_hierarchy = 'uploaded_at'
    readonly_fields = ['file_size', 'file_hash', 'uploaded_at']
    
    fieldsets = (
        ('PDF Information', {
            'fields': ('vendor', 'file', 'status', 'status_badge')
        }),
        ('File Details', {
            'fields': ('file_size', 'file_hash', 'uploaded_at')
        }),
    )

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">{}</a>', 
                             obj.file.url, obj.file.name.split('/')[-1])
        return "-"
    file_link.short_description = "PDF File"

    def extracted_count(self, obj):
        count = obj.extracted_data.count()
        return format_html('<span style="color: green;">{} fields</span>', count) if count else '0'
    extracted_count.short_description = "Extracted Fields"
    
    def file_size_display(self, obj):
        """Display file size in human-readable format"""
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size/1024:.1f} KB"
        else:
            return f"{obj.file_size/(1024*1024):.1f} MB"
    file_size_display.short_description = "File Size"
    
    def mark_as_pending(self, request, queryset):
        queryset.update(status='PENDING')
    mark_as_pending.short_description = "Mark selected PDFs as pending"
    
    def mark_as_processing(self, request, queryset):
        queryset.update(status='PROCESSING')
    mark_as_processing.short_description = "Mark selected PDFs as processing"
    
    def mark_as_completed(self, request, queryset):
        queryset.update(status='COMPLETED')
    mark_as_completed.short_description = "Mark selected PDFs as completed"
    
    def mark_as_error(self, request, queryset):
        queryset.update(status='ERROR')
    mark_as_error.short_description = "Mark selected PDFs as error"

    def status_badge(self, obj):
        status_colors = {
            'PENDING': 'warning',
            'PROCESSING': 'info',
            'COMPLETED': 'success',
            'ERROR': 'danger'
        }
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            status_colors.get(obj.status, 'secondary'),
            obj.status
        )
    status_badge.short_description = "Status"
    
    class Media:
        css = {
            'all': [
                'admin/css/admin.css',
                'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css',
            ]
        }
        js = [
            'admin/js/admin.js',
            'https://code.jquery.com/jquery-3.5.1.min.js',
            'https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js',
        ]

@admin.register(ExtractedData)
class ExtractedDataAdmin(admin.ModelAdmin):
    list_display = ['id', 'vendor', 'pdf_link', 'field_key', 'field_value', 'created_at']
    list_filter = ['vendor', 'field_key', 'created_at']
    search_fields = ['field_key', 'field_value', 'vendor__name']
    list_per_page = 50
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']

    def pdf_link(self, obj):
        if obj.pdf and obj.pdf.file:
            return format_html('<a href="{}" target="_blank">{}</a>', 
                             obj.pdf.file.url, obj.pdf.file.name.split('/')[-1])
        return "-"
    pdf_link.short_description = "Source PDF"

    fieldsets = (
        ('Source Information', {
            'fields': ('vendor', 'pdf')
        }),
        ('Extracted Data', {
            'fields': ('field_key', 'field_value')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
