from django.db import models

class City(models.Model):  # Таблица с городами
    name = models.CharField(unique=True, max_length=100, blank=False, null=False)

    def __str__(self):
        return self.name

class WeatherRequest(models.Model):  # Хранит историю запросов погоды
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    request_type = models.CharField(
        max_length=50, choices=[("web", "Сайт"), ("telegram", "Telegram")]
    )
