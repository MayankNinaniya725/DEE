# extractor/models.py
from django.db import models
from django.urls import reverse
from django.conf import settings
import os

class Vendor(models.Model):
    name = models.CharField(max_length=255, unique=True)
    config_file = models.FileField(upload_to="vendor_configs/")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class UploadedPDF(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="pdfs")
    file = models.FileField(upload_to="uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vendor.name} - {os.path.basename(self.file.name)}"

    def get_file_url(self):
        return settings.MEDIA_URL + str(self.file)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Uploaded PDF"
        verbose_name_plural = "Uploaded PDFs"

class ExtractedData(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    pdf = models.ForeignKey(UploadedPDF, on_delete=models.CASCADE, related_name="extracted_data")
    field_key = models.CharField(max_length=255)
    field_value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vendor.name} - {self.field_key}: {self.field_value}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Extracted Data"
        verbose_name_plural = "Extracted Data"

