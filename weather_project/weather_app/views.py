from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets
from django.core.cache import cache
from rest_framework import status
from .models import City, WeatherRequest
from .serializers import CitySerializer, WeatherRequestSerializer
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.utils import timezone  # Для добавления временной метки
from .forms import WeatherRequestForm  # Предполагается, что форма определена в forms.py


class WeatherView(APIView):
    API_KEY = "8d9b2728bd31be415ec496cb18419ca7"
    BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

    def get_current_weather(self, city_name):
        """Получение текущей погоды по названию города."""
        response = requests.get(
            self.BASE_URL,
            params={
                "q": city_name,
                "appid": self.API_KEY,
                "units": "metric",
                "lang": "ru",
            },
        )
        if response.status_code == 200:
            return response.json()  # Возвращаем данные о текущей погоде
        else:
            return None  # Если ошибка, возвращаем None

    def get(self, request):
        """Обработка GET-запроса для получения погоды."""
        city_name = request.query_params.get("city")
        if not city_name:
            return Response({"error": "City parameter is required"}, status=400)

        # Проверка кеша
        cache_key = f"weather_{city_name}"
        cached_data = cache.get(cache_key)  # Пытаемся получить данные из кеша
        if cached_data:
            return Response(cached_data)  # Если данные найдены в кеше, возвращаем их

        # Получение текущей погоды
        weather_data = self.get_current_weather(city_name)
        if weather_data:
            # Сохранение данных в кеш
            cache.set(
                cache_key,
                {
                    "temperature": weather_data["main"]["temp"],
                    "pressure": weather_data["main"]["pressure"],
                    "wind_speed": weather_data["wind"]["speed"],
                    "weather_text": weather_data["weather"][0]["description"],
                },
                timeout=1800,
            )  # Кеш на 30 минут

            # Сохранение запроса в базе данных
            city, created = City.objects.get_or_create(name=city_name)
            WeatherRequest.objects.create(
                city=city, request_type="web", timestamp=timezone.now()
            )
            print(f"Запрос сохранен в БД для города: {city_name}")  # Лог для проверки

            # Форматируем ответ
            formatted_data = {
                "temperature": weather_data["main"]["temp"],
                "pressure": weather_data["main"]["pressure"],
                "wind_speed": weather_data["wind"]["speed"],
                "weather_text": weather_data["weather"][0]["description"],
            }
            return Response(formatted_data)
        else:
            return Response(
                {"error": "City not found or API error"}, status=404
            )  # Возвращаем 404 при ошибке

    def post(self, request):
        """Обработка POST-запроса для получения погоды."""
        city_name = request.data.get("city")
        if not city_name:
            return Response({"error": "City parameter is required"}, status=400)

        # Логика аналогична обработке GET-запроса
        return self.get(request)


class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer


class WeatherRequestViewSet(viewsets.ModelViewSet):
    queryset = WeatherRequest.objects.all()
    serializer_class = WeatherRequestSerializer


def get_weather(request):
    weather_data = None
    error_message = None  # Переменная для хранения сообщения об ошибке

    if request.method == "POST":
        city_name = request.POST.get("city")
        if city_name:
            try:
                api = WeatherView()  # Создаем экземпляр класса WeatherView
                response = api.get_current_weather(city_name)  # Получаем погоду
                if response:
                    # Сохранение запроса в базу данных
                    city, created = City.objects.get_or_create(name=city_name)
                    WeatherRequest.objects.create(
                        city=city, request_type="web", timestamp=timezone.now()
                    )

                    pressure_mm = response["main"]["pressure"] * 0.750061683
                    weather_data = {
                        "city_name": city_name,
                        "temperature": int(response["main"]["temp"]),
                        "pressure": int(pressure_mm),  # Давление в мм рт. ст.
                        "wind_speed": int(response["wind"]["speed"]),
                        "weather_text": response["weather"][0]["description"],
                    }
                    print(
                        f"Запрос сохранен в БД для города: {city_name}"
                    )  # Лог для проверки
                else:
                    error_message = "Город не найден или произошла ошибка при запросе."
            except Exception as e:
                error_message = str(e)

    # Рендеринг шаблона с данными о погоде или сообщением об ошибке
    return render(
        request,
        "weather_app/weather_form.html",
        {
            "weather_data": weather_data,
            "error_message": error_message,  # Передаем сообщение об ошибке в контекст
        },
    )


class HistoryView(APIView):
    # (Существующий код, включая логику пагинации и фильтрации)
    
    def get(self, request):
        # Получение параметра количества элементов на странице
        items_per_page = request.GET.get("items_per_page", 10)
        if items_per_page not in ["5", "10", "15"]:
            items_per_page = 10  # Значение по умолчанию

        # Получение параметров сортировки и фильтрации
        sort = request.GET.get("sort", "-timestamp")  # Сортировка по умолчанию по времени
        request_type = request.GET.get("type")  # Фильтр по типу запроса

        # Фильтрация по типу запроса
        queryset = WeatherRequest.objects.select_related("city").all()
        if request_type in ["web", "telegram"]:  # Проверка на допустимые значения
            queryset = queryset.filter(request_type=request_type)

        # Сортировка
        if sort == "city":
            queryset = queryset.order_by("city__name")  # Сортировка по имени города
        else:
            queryset = queryset.order_by("-timestamp")  # Сортировка по времени запроса

        # Пагинация
        paginator = Paginator(queryset, int(items_per_page))
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        return render(
            request,
            "weather_app/history.html",
            {
                "requests": page_obj,
                "items_per_page": items_per_page,
                "current_page": page_obj.number,
                "total_pages": paginator.num_pages,
                "current_sort": sort,  # Текущая сортировка
                "current_type": request_type,  # Текущий тип запроса
            },
        )


def create_request(request):
    if request.method == "POST":
        form = WeatherRequestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("history_view")
    else:
        form = WeatherRequestForm()
    return render(request, "weather_app/create_request.html", {"form": form})


def update_request(request, pk):
    weather_request = get_object_or_404(WeatherRequest, pk=pk)
    if request.method == "POST":
        form = WeatherRequestForm(request.POST, instance=weather_request)
        if form.is_valid():
            form.save()
            return redirect("history_view")
    else:
        form = WeatherRequestForm(instance=weather_request)
    return render(request, "weather_app/update_request.html", {"form": form})


def delete_request(request, pk):
    weather_request = get_object_or_404(WeatherRequest, pk=pk)
    if request.method == "POST":
        weather_request.delete()
        return redirect("history_view")
    return render(
        request, "weather_app/delete_request.html", {"weather_request": weather_request}
    )
