from django import forms
from .models import UploadedPDF, Vendor

class UploadPDFForm(forms.ModelForm):
    class Meta:
        model = UploadedPDF
        fields = ["vendor", "file"]
