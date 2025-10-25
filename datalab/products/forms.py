from django import forms
from django.forms import inlineformset_factory,FileInput

from .models import Product, ProductImage

from multiupload.fields import MultiFileField

class UploadForm(forms.Form):
    files = MultiFileField(min_num=1, max_num=100, max_file_size=10485760)
    sheet_name = forms.CharField(required=False)

class DateFilterForm(forms.Form):
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    category = forms.CharField(required=False)


ProductImageFormSet = inlineformset_factory(
    parent_model=Product,
    model=ProductImage,
    fields=['image', 'alt'],
    extra=4,
    can_delete=True,
    max_num=100,
    validate_max=True
)
