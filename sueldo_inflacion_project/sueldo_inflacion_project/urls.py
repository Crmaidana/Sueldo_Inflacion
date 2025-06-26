# sueldo_inflacion_project/sueldo_inflacion_project/urls.py

from django.contrib import admin
from django.urls import path, include # Asegúrate de importar include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('comparador/', include('comparador.urls')), # <-- Añade esta línea
    path('', include('comparador.urls')), # Opcional: Para que la app sea la página principal
]