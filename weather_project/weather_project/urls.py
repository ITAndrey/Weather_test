from django.urls import path, include
from rest_framework.routers import DefaultRouter
from weather_app.views import WeatherView, CityViewSet, WeatherRequestViewSet
from weather_app.views import get_weather, HistoryView, create_request, update_request, delete_request

router = DefaultRouter()
router.register(r'cities', CityViewSet)  # Это создаст маршруты для city-list и city-detail
router.register(r'requests', WeatherRequestViewSet)  # Это создаст маршруты для weatherrequest-list и weatherrequest-detail

urlpatterns = [
    path("weather/", WeatherView.as_view(), name="weather"),
    path('', get_weather, name='get_weather'),
    path('history/', HistoryView.as_view(), name='history_view'),
    path('create/', create_request, name='create_request'),
    path('update/<int:pk>/', update_request, name='update_request'),
    path('delete/<int:pk>/', delete_request, name='delete_request'), 
    path('', include(router.urls)),  # Добавляем маршруты роутера
]
