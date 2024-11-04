from rest_framework import serializers
from weather_app.models import City, WeatherRequest

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'

class WeatherRequestSerializer(serializers.ModelSerializer):
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())  # Или используйте CitySerializer()

    class Meta:
        model = WeatherRequest
        fields = '__all__'
