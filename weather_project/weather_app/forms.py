from django import forms
from .models import WeatherRequest

class WeatherRequestForm(forms.ModelForm):
    class Meta:
        model = WeatherRequest
        fields = ['city', 'request_type']