from django.contrib import admin
from django.utils.html import format_html
from .models import ExtractedData, Vendor, UploadedPDF

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'config_file_link']
    search_fields = ['name']
    list_per_page = 20

    def config_file_link(self, obj):
        if obj.config_file:
            return format_html('<a href="{}" target="_blank">View Config</a>', obj.config_file.url)
        return "-"
    config_file_link.short_description = "Config File"

@admin.register(UploadedPDF)
class UploadedPDFAdmin(admin.ModelAdmin):
    list_display = ['id', 'vendor', 'file_link', 'uploaded_at', 'extracted_count']
    list_filter = ['vendor', 'uploaded_at']
    search_fields = ['file', 'vendor__name']
    list_per_page = 20
    date_hierarchy = 'uploaded_at'

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
