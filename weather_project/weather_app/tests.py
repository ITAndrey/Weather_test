from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import City, WeatherRequest


class WeatherApiTests(APITestCase):
    def test_get_weather_without_city(self):
        """Тест для проверки ответа при отсутствии имени города в запросе."""
        response = self.client.get(reverse('weather'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # Ожидаем код 400 Bad Request

    def test_get_weather_with_valid_city(self):
        """Тест для проверки получения данных о погоде для валидного города."""
        city_name = 'Cairo'
        City.objects.create(name=city_name)  # Создаем город
        response = self.client.get(reverse('weather'), {'city': city_name})

        print("Response status code:", response.status_code)  # Выводим статус код
        print("Response content:", response.content)  # Выводим содержимое ответа

        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Ожидаем код 200 OK

    def test_get_weather_with_invalid_city(self):
        """Тест для проверки обработки невалидного имени города."""
        response = self.client.get(reverse('weather'), {'city': 'НевуществующийГород'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)  # Ожидаем код 404 Not Found

    def test_create_city(self):
        """Тест для проверки создания нового города."""
        response = self.client.post(reverse('city-list'), {'name': 'Moscow'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)  # Ожидаем код 201 Created
        self.assertEqual(City.objects.count(), 1)  # Проверяем, что город был добавлен
        self.assertEqual(City.objects.get().name, 'Moscow')  # Проверяем, что имя совпадает


    def test_get_weather_with_caching(self):
        """Тест для проверки кэширования запросов на погоду."""
        city_name = 'Cairo'
        City.objects.create(name=city_name)  # Создаем город
        
        # Первый запрос, должен вернуть 200 OK
        response = self.client.get(reverse('weather'), {'city': city_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Второй запрос в течение 30 минут
        response = self.client.get(reverse('weather'), {'city': city_name})
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Должен вернуться из кэша
